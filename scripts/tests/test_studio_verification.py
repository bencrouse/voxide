from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import studio_verification as verification


class StudioVerificationTests(unittest.TestCase):
    def setUp(self):
        self.protocol = verification.execution_protocol()
        self.calibration = self.protocol["calibration"]

    def observations(self, errors):
        return [{"eligible": True, "source_sample": i*480, "observed_hz": None if e is None else 220,
                 "error_cents": e} for i, e in enumerate(errors)]

    def test_frozen_bounded_set_and_negatives(self):
        cases = verification.calibration_cases(self.protocol)
        self.assertEqual(len(cases), 36)
        self.assertEqual(sum(c["kind"] == "positive" for c in cases), 28)
        self.assertEqual({c["midi"] for c in cases if c["kind"] == "positive"}, {28, 40, 45, 57, 69, 84, 96})

    def test_empty_gates_or_meter_bindings_cannot_waive_calibration(self):
        import copy
        original = verification.load_json
        for fault in ("gates", "meter"):
            changed = copy.deepcopy(self.protocol)
            if fault == "gates": changed["calibration"]["gates"] = {}
            else: changed["meter_sources_sha256"] = {}
            with patch.object(verification, "load_json", side_effect=lambda path: changed if path == verification.EXECUTION else original(path)), self.subTest(fault=fault), self.assertRaises(ValueError):
                verification.execution_protocol()

    def test_missing_pitch_is_wrong_not_removed(self):
        case = {"rate": 48000, "kind": "positive", "reference_voiced": True}
        result = verification.score(self.observations([0]*99+[None]), case, self.calibration)
        self.assertEqual(result["eligible_pitch_frames"], 100)
        self.assertEqual(result["missing_estimates"], 1)
        self.assertEqual(result["within_25c_fraction"], .99)

    def test_wrong_octaves_and_long_wrong_runs_fail(self):
        case = {"rate": 48000, "kind": "positive", "reference_voiced": True}
        for errors in ([1200]+[0]*999, [100]*6+[0]*994):
            self.assertFalse(verification.score(self.observations(errors), case, self.calibration)["calibration_pass"])

    def test_wrong_target_controls_must_detect_error_not_accept_it(self):
        case = {"rate": 48000, "kind": "one-semitone-wrong-target", "reference_voiced": True}
        self.assertTrue(verification.score(self.observations([-100]*100), case, self.calibration)["calibration_pass"])
        self.assertFalse(verification.score(self.observations([0]*100), case, self.calibration)["calibration_pass"])
        self.assertFalse(verification.score(self.observations([None]*100), case, self.calibration)["calibration_pass"])

    def test_unvoiced_never_earns_accuracy_and_false_detections_fail(self):
        case = {"rate": 48000, "kind": "silence", "reference_voiced": False}
        result = verification.score(self.observations([None]*10), case, self.calibration)
        self.assertTrue(result["calibration_pass"])
        self.assertIsNone(result["within_25c_fraction"])
        self.assertEqual(result["correct_pitch_frames"], 0)
        self.assertFalse(verification.score(self.observations([0]*10), case, self.calibration)["calibration_pass"])

    def test_no_eligible_reference_is_not_a_pass(self):
        with self.assertRaises(ValueError):
            verification.score([], {"rate": 48000, "kind": "positive", "reference_voiced": True}, self.calibration)

    def test_private_worker_input_is_rejected_before_hash_or_decode(self):
        with patch.object(verification, "sha256") as digest, self.assertRaises(ValueError):
            verification.measure_job({"source": "evaluation/pr-06a/never-open.f32"})
        digest.assert_not_called()

    def test_generation_is_finite_exact_duration_and_attenuation_only(self):
        case = {"rate": 44100, "midi": 28, "shape": "six-harmonic"}
        source, metadata = verification.generate(case, self.calibration)
        self.assertEqual(len(source), 158760)
        self.assertEqual(metadata["primary_frames"], 132300)
        self.assertTrue(all(x == 0 for x in source[132300:]))
        self.assertTrue(0 < metadata["source_gain"] <= 1)

    def test_consumed_calibration_stops_before_generation_or_workers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            claim = root/"build/studio-verification/claims"/(self.protocol["id"]+"-a1.json")
            claim.parent.mkdir(parents=True); claim.write_text("consumed")
            with patch.object(verification, "ROOT", root), patch.object(verification, "execution_protocol", return_value=self.protocol), \
                 patch.object(verification, "generate") as generate, patch.object(verification, "ProcessPoolExecutor") as workers, self.assertRaises(FileExistsError):
                verification.calibrate(1)
            generate.assert_not_called(); workers.assert_not_called()
            self.assertEqual(claim.read_text(), "consumed")

    def test_calibration_output_symlink_is_rejected_before_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); public = root/"public"; public.mkdir()
            (root/"build").mkdir(); (root/"build/studio-verification").symlink_to(public, target_is_directory=True)
            with patch.object(verification, "ROOT", root), patch.object(verification, "execution_protocol", return_value=self.protocol), \
                 patch.object(verification, "generate") as generate, self.assertRaisesRegex(ValueError, "Symlink"):
                verification.calibrate(1)
            generate.assert_not_called(); self.assertEqual(list(public.iterdir()), [])


if __name__ == "__main__": unittest.main()
