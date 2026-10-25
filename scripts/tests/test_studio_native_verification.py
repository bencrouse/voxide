import array
import copy
import struct
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import studio_native_verification as native
from studio_test_support import synthetic_timeline


class StudioNativeVerificationTests(unittest.TestCase):
    def fixture(self, rate=48000, mode="prescribed"):
        case = {"rate": rate, "midi": 57, "mode": mode, "shape": "sine", "voicing": "octaves", "intervals": [-12, 0, 12]}
        total, primary, delay = rate*18//5, rate*3, rate//10
        source = array.array("f", [.01]*primary+[0.]*(total-primary))
        outputs = {name: array.array("f", [0.]*total) for name in native.CHANNELS}
        outputs["lead-direct"] = source; outputs["lead-aligned"] = array.array("f", [0.]*delay)+source[:total-delay]
        for v in range(3): outputs["voice"+str(v+1)] = array.array("f", (x*.5 for x in outputs["lead-aligned"]))
        for name, lead in (("sum-direct", source), ("sum-aligned", outputs["lead-aligned"])):
            outputs[name] = array.array("f", (x+sum(outputs["voice"+str(v+1)][i] for v in range(3))/3 for i, x in enumerate(lead)))
        metadata, rows = synthetic_timeline(rate, total, oracle=mode == "prescribed")
        if mode == "prescribed":
            pitch = copy.copy(rows[0]); pitch["request_kind"] = "0"
            target = copy.copy(rows[0]); target["request_kind"] = "1"
            rows[:1] = [pitch, target]
        for row in rows:
            if row["kind"] == "0" and int(row["source"]) >= 0:
                v = int(row["voice"])
                row["request_kind"] = "1" if mode == "prescribed" else "3"
                row["target_midi"] = str(57+case["intervals"][v])
                row["applied_shift"] = row["requested_shift"] = str(case["intervals"][v])
        info = {"engine": "signalsmith", "sample_rate": rate, "window": 2048, "hop": 512,
                "mode": 0 if mode == "prescribed" else 2, "treatment": 0, "reserve_profile": 1,
                "shift_limit": 12, "inactive_uncertain": True, "source_frames": primary, "zero_tail": total-primary,
                "output_frames": total, "latency_samples": delay, "unrendered_finish_peak": 0, **metadata,
                **{key: 0 for key in ("missing_metadata", "fifo_overflow", "bad_events", "late_controls", "telemetry_dropped", "invalid_input")}}
        fed = (total-metadata["analysis_delay_samples"])//512*512
        words = array.array("I"); words.frombytes(source.tobytes()[:fed*4])
        for v in range(3):
            applied = [r for r in rows if r["kind"] == "0" and r["voice"] == str(v)]
            control = [struct.unpack("<Q", struct.pack("<d", value))[0] for r in applied for value in
                       (float(r["applied_shift"]), float(r["hz"]) if int(r["voiced"]) else 0.)]
            info["voices"][v].update(native_input_hash=native.fnv(words), control_hash=native.fnv(control))
        return case, info, outputs, source, rows

    def test_exact_72_matched_cases_and_inclusive_octaves(self):
        cases = native.steady_cases()
        self.assertEqual(len(cases), 72); self.assertEqual(len({c["id"] for c in cases}), 72)
        self.assertEqual({tuple(c["intervals"]) for c in cases if c["voicing"] == "octaves"}, {(-12, 0, 12)})
        self.assertEqual(native.intervals(40, "upper"), [3, 7, 12])
        self.assertEqual(native.intervals(84, "upper"), [4, 7, 12])
        self.assertEqual(native.intervals(40, "lower"), [-4, -7, -12])

    def test_prescribed_events_are_analytic_and_causal(self):
        case = {"midi": 57, "mode": "prescribed", "intervals": [-12, 0, 12]}
        self.assertEqual(native.event_text(case), "0 0 P 220 1 1 0 0\n0 0 T 45 57 69 7\n")

    def test_valid_scoped_timeline_and_hashes_at_both_rates_and_modes(self):
        for rate in (44100, 48000):
            for mode in ("prescribed", "tracked-scale"):
                with self.subTest(rate=rate, mode=mode): native.safety(*self.fixture(rate, mode))

    def test_missing_packets_and_unknown_request_fail_oracle_validation(self):
        for fault in ("packet", "request", "clock", "hash", "nonfinite", "sum"):
            fixture = self.fixture(); case, info, outputs, _, rows = fixture
            if fault == "packet": rows.pop(next(i for i, r in enumerate(rows) if r["kind"] == "1"))
            elif fault == "request": rows[0]["request_kind"] = "3"
            elif fault == "clock": next(r for r in rows if r["kind"] == "1")["wall"] = "0"
            elif fault == "hash": info["voices"][0]["control_hash"] = "0"
            elif fault == "nonfinite": outputs["native1"][100] = float("nan")
            else: outputs["sum-direct"][5000] = 0
            with self.subTest(fault=fault), self.assertRaises(ValueError): native.safety(*fixture)

    def test_private_calibration_reference_is_refused_before_report_read(self):
        with patch.object(native, "execution_protocol", return_value={"id": "test"}), \
             patch.object(native, "load_json", return_value={"run": "evaluation/pr-06a/do-not-open"}) as read, self.assertRaises(ValueError):
            native.prerequisite()
        self.assertEqual(read.call_count, 1)

    def test_failed_calibration_blocks_native_entry_before_any_execution(self):
        with patch.object(native, "prerequisite", side_effect=ValueError("A1 failed")), \
             patch.object(native.subprocess, "run") as run, self.assertRaisesRegex(ValueError, "A1 failed"):
            native.steady(Path("build/interaction-release"), 1)
        run.assert_not_called()

    def test_control_diagnostics_do_not_use_tracker_as_its_own_truth(self):
        case, _, _, _, rows = self.fixture()
        controls = [r for r in rows if r["kind"] == "0"]
        self.assertTrue(native.control_diagnostics(case, controls)["pass"])
        # A consistently sharp source/target pair still has correct relative
        # selector intervals, but must fail the independent analytic source truth.
        for row in controls:
            if int(row["voiced"]):
                row["hz"] = str(220*2**(1/12)); row["target_midi"] = str(float(row["target_midi"])+1)
        result = native.control_diagnostics(case, controls)
        self.assertFalse(result["pass"])
        self.assertEqual(result["voices"][0]["source_within_25c_fraction"], 0)
        self.assertLess(result["voices"][0]["selector_interval_max_error_semitones"], 1e-6)

    def test_inactive_uncertain_control_is_missing_source_not_a_wrong_ratio(self):
        case, _, _, _, rows = self.fixture(mode="tracked-scale")
        controls = [r for r in rows if r["kind"] == "0"]
        row = next(r for r in controls if r["voice"] == "0" and int(r["source"]) >= 4800)
        row.update(voiced="0", active="0", hz="0", requested_shift="0", applied_shift="0", target_midi="57")
        result = native.control_diagnostics(case, controls)
        self.assertTrue(result["pass"])
        self.assertLess(result["voices"][0]["source_within_25c_fraction"], 1)
        self.assertEqual(result["voices"][0]["applied_shift_max_error_semitones"], 0)

    def test_oversized_case_set_is_rejected_before_authorization_or_execution(self):
        cases = native.steady_cases(); cases.append(dict(cases[0], id="extra"))
        with patch.object(native, "steady_cases", return_value=cases), patch.object(native, "prerequisite") as auth, \
             patch.object(native.subprocess, "run") as run, self.assertRaisesRegex(ValueError, "before execution"):
            native.steady(Path("build/interaction-release"), 1)
        auth.assert_not_called(); run.assert_not_called()

    def test_consumed_native_stage_cannot_render_again(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); protocol = {"id": "test-stage"}
            claim = root/"build/studio-verification/claims/test-stage-a2.json"
            claim.parent.mkdir(parents=True); claim.write_text("consumed")
            with patch.object(native, "ROOT", root), patch.object(native, "prerequisite", return_value=(protocol, root/"build/calibration")), \
                 patch.object(native, "provenance") as attest, patch.object(native.subprocess, "run") as run, self.assertRaises(FileExistsError):
                native.steady(root/"build/isolated", 1)
            attest.assert_not_called(); run.assert_not_called()
            self.assertEqual(claim.read_text(), "consumed")


if __name__ == "__main__": unittest.main()
