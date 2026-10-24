import array
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio_engineering import analyse, compare, summarize, PROTOCOL
from evaluation_common import load_json
from studio_test_support import synthetic_timeline


class StudioEngineeringTests(unittest.TestCase):
    def analysis_fixture(self, rate=48000):
        frames, primary, delay = rate*28//5, rate*5, rate//10
        source = array.array("f", [.01]*primary+[0.]*(frames-primary))
        audio = [array.array("f", [0.]*frames) for _ in range(10)]
        audio[0] = source; audio[1] = array.array("f", [0.]*delay)+source[:frames-delay]
        for channel in range(2, 8): audio[channel] = array.array("f", (x*.5 for x in audio[1]))
        for channel, lead in ((8, audio[0]), (9, audio[1])):
            audio[channel] = array.array("f", (x+sum(audio[c][i] for c in (5, 6, 7))/3 for i, x in enumerate(lead)))
        metadata, timeline = synthetic_timeline(rate, frames)
        native = {"frames": frames, "rate": rate, "source_frames": primary, "zero_tail": frames-primary,
                  "engine": "signalsmith", "window": 2048, "hop": 512}
        capture = {"name": "cold", "complete": True, "processed": frames, "finish_peak": 0,
                   "voices": metadata["voices"], **{key: 0 for key in ("bad_events", "late_controls", "telemetry_dropped", "invalid_input", "missing_metadata", "fifo_overflow")}}
        controls = [{**r, "shift": r["applied_shift"]} for r in timeline if r["kind"] == "0"]
        callbacks = [{"begin": str(i), "frames": str(min(128, frames-i)), "ns": "1", "allocations": "0"} for i in range(0, frames, 128)]
        return source, audio, native, capture, controls, callbacks, load_json(PROTOCOL)

    def analyse_fixture(self, fixture):
        source, audio, native, capture, controls, callbacks, protocol = fixture
        def floats(path):
            if str(path).endswith("-source.f32"): return source, source.tobytes()
            channel = int(str(path).rsplit("-channel", 1)[1].split(".")[0])
            return audio[channel], audio[channel].tobytes()
        with patch("studio_engineering.read_float", side_effect=floats), \
             patch("studio_engineering.read_csv", side_effect=lambda path: controls if str(path).endswith("-controls.csv") else callbacks):
            return analyse(Path("synthetic/render-cold"), native, capture, protocol)

    def test_complete_frozen_workload_and_both_sums_pass_at_both_rates(self):
        for rate in (44100, 48000):
            with self.subTest(rate=rate):
                result = self.analyse_fixture(self.analysis_fixture(rate))
                self.assertEqual(result["status"], "measured")
                self.assertTrue(all(value == "pass" for value in result["gates"].values()))
                self.assertEqual(set(result["fixed_sum"]), {"sum-direct", "sum-aligned"})

    def test_self_consistent_short_duration_and_wrong_split_rejected_before_io(self):
        protocol = load_json(PROTOCOL)
        for fault in ("short", "split", "rate"):
            native = {"rate": 48000, "source_frames": 240000, "zero_tail": 28800, "frames": 268800}
            if fault == "short": native.update(source_frames=9000, zero_tail=1000, frames=10000)
            elif fault == "split": native.update(source_frames=239999, zero_tail=28801)
            else: native["rate"] = 32000
            capture = {"name": "cold", "complete": True, "processed": native["frames"]}
            with patch("studio_engineering.read_float") as read, self.subTest(fault=fault), self.assertRaises(ValueError):
                analyse(Path("synthetic/render-cold"), native, capture, protocol)
            read.assert_not_called()

    def test_zeroed_changed_gain_and_wrong_route_sums_fail(self):
        fixture = self.analysis_fixture()
        for channel in (8, 9):
            for fault in ("zero", "gain", "route"):
                changed = list(fixture); changed[1] = list(fixture[1])
                original = fixture[1][channel]
                changed[1][channel] = array.array("f", [0.]*len(original)) if fault == "zero" else \
                    array.array("f", (x*.8 for x in original)) if fault == "gain" else fixture[1][17-channel]
                with self.subTest(channel=channel, fault=fault):
                    result = self.analyse_fixture(changed)
                    self.assertEqual(result["gates"]["fixed_sum"], "fail")
                    self.assertEqual(result["gates"]["lead_null"], "pass")

    def test_truncated_file_nonzero_supplied_tail_and_missing_control_tail_fail(self):
        for fault in ("file", "tail", "control"):
            fixture = list(self.analysis_fixture())
            if fault == "file": fixture[1][4].pop()
            elif fault == "tail": fixture[0][-1] = .01
            else: fixture[4].pop()
            with self.subTest(fault=fault), self.assertRaises(ValueError): self.analyse_fixture(fixture)

    def capture(self):
        return {"complete": True, "voices": [{"input_hash": "same", "control_hash": "same"} for _ in range(3)]}

    def raw(self, prefix, length=100, offset=0):
        for channel in range(10):
            values = array.array("f", [(channel+1)*.001+offset]*length)
            Path(str(prefix)+f"-channel{channel}.f32").write_bytes(values.tobytes())

    def test_frozen_repeat_limits_and_all_channels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); a, b = root/"a", root/"b"
            self.raw(a); self.raw(b)
            self.assertEqual(compare(a, b, self.capture(), self.capture())["status"], "pass")
            data = array.array("f", [.1]*100); Path(str(b)+"-channel9.f32").write_bytes(data.tobytes())
            result = compare(a, b, self.capture(), self.capture())
            self.assertEqual(result["status"], "waveform_difference")
            self.assertFalse(result["channels"][9]["pass"])

    def test_mismatched_input_is_not_attributed_to_native_nondeterminism(self):
        with tempfile.TemporaryDirectory() as temporary:
            a, b = Path(temporary)/"a", Path(temporary)/"b"; self.raw(a); self.raw(b)
            changed = self.capture(); changed["voices"][1]["control_hash"] = "different"
            self.assertEqual(compare(a, b, self.capture(), changed)["status"], "input_control_mismatch")

    def test_missing_tail_and_incomplete_native_run_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            a, b = Path(temporary)/"a", Path(temporary)/"b"; self.raw(a); self.raw(b, 99)
            self.assertEqual(compare(a, b, self.capture(), self.capture())["status"], "waveform_difference")
            changed = self.capture(); changed["complete"] = False
            self.assertEqual(compare(a, b, self.capture(), changed)["status"], "incomplete_native_capture")

    def test_summary_retains_allocation_and_repeat_failures(self):
        case = {"case": "rubberband-48000-512-p0", "engine": "rubberband", "rate": 48000, "block": 512, "status": "rendered",
                "native": {"restart_rejected": True}, "captures": [{"name": "cold", "status": "measured", "gates": {"callback_allocation": "fail"},
                 "callback": {"allocation_calls": 9, "occupancy_p999": .1, "occupancy_max": .2, "overdue_callbacks": 0}}]}
        comparison = {"engine": "rubberband", "kind": "stopped_reconstruction", "a": case["case"]+"/cold", "b": case["case"]+"/reset",
                      "result": {"status": "waveform_difference"}}
        row = next(r for r in summarize([case], [comparison]) if r["engine"] == "rubberband")
        self.assertEqual(row["callback_allocations"], 9)
        self.assertEqual(len(row["failures"]), 2)
        self.assertTrue(all(p["bounded_screen"] == "fail_or_incomplete" for p in row["points"]))

    def test_failed_small_buffer_does_not_erase_passing_larger_point(self):
        cases = []
        for block in (128, 512):
            for repeat in (0, 1):
                captures = [{"name": name, "status": "measured", "gates": {"callback_budget_this_run": "fail" if block == 128 else "pass"},
                             "callback": {"allocation_calls": 0, "occupancy_p999": .7 if block == 128 else .2, "occupancy_max": .8, "overdue_callbacks": 0}}
                            for name in ("cold", "reset", "fresh")]
                cases.append({"case": f"signalsmith-48000-{block}-p{repeat}", "engine": "signalsmith", "rate": 48000, "block": block,
                              "status": "rendered", "captures": captures, "native": {"restart_rejected": True}})
        comparisons = [{"engine": "signalsmith", "kind": "independent_process", "a": f"signalsmith-48000-{block}-p0/cold",
                        "b": f"signalsmith-48000-{block}-p1/cold", "result": {"status": "pass"}} for block in (128, 512)]
        row = next(r for r in summarize(cases, comparisons) if r["engine"] == "signalsmith")
        points = {p["block"]: p["bounded_screen"] for p in row["points"] if p["rate"] == 48000}
        self.assertEqual(points, {128: "fail_or_incomplete", 512: "pass"})


if __name__ == "__main__": unittest.main()
