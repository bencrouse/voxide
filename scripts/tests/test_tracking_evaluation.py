import sys
from pathlib import Path
import unittest
import tempfile
import json
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tracking_evaluation import (at_or_before, summarize, response, validate_frames,
                                 permitted_development, approved_private_audio, analytic_cases, aggregate)
from evaluation_common import write_wav, read_wav, read_wav_bytes, sha256


def estimate(available, hz=220, voiced=1):
    return {"begin": 0, "end": available, "available": available, "hz": hz, "voiced": voiced}


class CausalTrackingMetricsTests(unittest.TestCase):
    def test_availability_not_support_center(self):
        frames = [estimate(100)]
        self.assertIsNone(at_or_before(frames, 98, 5))
        self.assertEqual(at_or_before(frames, 99, 5)["available"], 100)
        self.assertIsNone(at_or_before(frames, 104, 5))

    def test_missing_uncertain_and_octave_denominators(self):
        reference = [{"sample": sample, "voiced": True, "stable": True, "f0_hz": 220, "uncertain": sample == 400}
                     for sample in (0, 100, 200, 300, 400)]
        result = summarize([estimate(100), estimate(200, 440), estimate(300, 220, 0)], reference, 48000)
        self.assertEqual(result["stable_voiced_reference_frames"], 4)
        self.assertEqual(result["stable_accuracy"], .25)
        self.assertEqual(result["missing_or_unvoiced_frames"], 2)
        self.assertEqual(result["octave_error_frames"], 1)
        self.assertEqual(result["uncertain_reference_frames_excluded"], 1)

    def test_dwell_completion_never_backdated(self):
        frames = [estimate(t) for t in range(10, 51, 5)]
        measured = response(frames, [(0, 60, "cold")], lambda _: 220, 1000)
        self.assertEqual(measured[0]["dwell_completed_ms"], 30)
        frames[2]["voiced"] = 0
        measured = response(frames, [(0, 60, "cold")], lambda _: 220, 1000)
        self.assertEqual(measured[0]["dwell_completed_ms"], 45)

    def test_missing_response_not_zero(self):
        measured = response([estimate(10, voiced=0)], [(0, 100, "cold")], lambda _: 220, 1000)
        self.assertIsNone(measured[0]["dwell_completed_ms"])
        self.assertTrue(measured[0]["missing_response"])

    def test_stale_tail_and_missing_middle_are_accuracy_failures(self):
        reference = [{"sample": sample, "voiced": True, "stable": True, "f0_hz": 220} for sample in (9, 14, 19, 24, 29)]
        result = summarize([estimate(10), estimate(20)], reference, 1000)
        self.assertEqual(result["stable_voiced_reference_frames"], 5)
        self.assertEqual(result["within_25c_frames"], 2)
        self.assertEqual(result["missing_or_unvoiced_frames"], 3)

    def test_dwell_restarts_after_missing_decisions(self):
        frames = [estimate(t) for t in (10, 35, 40, 45, 50, 55)]
        measured = response(frames, [(0, 60, "cold")], lambda _: 220, 1000)
        self.assertEqual(measured[0]["dwell_completed_ms"], 55)
        measured = response([estimate(10), estimate(100)], [(0, 110, "cold")], lambda _: 220, 1000)
        self.assertTrue(measured[0]["missing_response"])

    def test_decision_at_onset_cannot_start_event_dwell(self):
        frames = [estimate(t) for t in (50, 55, 60, 65, 70, 75)]
        measured = response(frames, [(50, 80, "continuous")], lambda _: 220, 1000)
        self.assertEqual(measured[0]["dwell_completed_ms"], 25)

    def test_probe_coverage_rejects_missing_middle_and_truncated_tail(self):
        timing = {"support_samples": 8, "hop_samples": 5, "first_available": 10}
        frames = [dict(estimate(t), begin=t - 8, confidence=1, rms=.1) for t in (10, 15, 20, 25, 30)]
        validate_frames(frames, 32, timing)
        validate_frames([], 9, timing)
        for malformed in (frames[:-1], frames[:2] + frames[3:], [], frames + [dict(frames[-1])]):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                validate_frames(malformed, 32, timing)

    def test_register_requirement_uses_post_transition_source_not_case_label(self):
        policy = {"timing_ms": {"recognition_boundary_hz": 150, "recognition_low_p95": 50, "recognition_high_p95": 30}}
        metrics = {"stable_voiced_reference_frames": 1, "within_25c_frames": 1, "octave_error_frames": 0, "false_voiced_frames": 0}
        row = {"variant": "yin", "midi_register": 48, "metrics": metrics, "responses": [
            {"kind": "cold", "source_hz_at_onset": 130.81, "dwell_completed_ms": 40, "missing_response": False},
            {"kind": "continuous", "source_hz_at_onset": 155.56, "dwell_completed_ms": 40, "missing_response": False}]}
        summary = next(group for group in aggregate([row], policy) if group["variant"] == "yin" and group["midi_register"] == 48)
        self.assertEqual(summary["timing"]["cold"]["required_recognition_p95_ms"], 50)
        self.assertTrue(summary["timing"]["cold"]["meets_target_on_this_probe_only"])
        self.assertEqual(summary["timing"]["continuous"]["required_recognition_p95_ms"], 30)
        self.assertFalse(summary["timing"]["continuous"]["meets_target_on_this_probe_only"])

    def test_generator_onsets_match_samples_and_edge_bends_are_not_clipped(self):
        for rate in (44100, 48000):
            for name, _, _, truth, events, midi in analytic_cases(rate):
                if "rhythmic-bend" not in name:
                    continue
                actual = [i for i, hz in enumerate(truth) if hz is not None and (i == 0 or truth[i - 1] is None)]
                self.assertEqual(actual, [event[0] for event in events])
                voiced = [hz for hz in truth if hz is not None]
                self.assertTrue(all(82.4068892282175 - 1e-9 <= hz <= 1046.5022612023945 + 1e-9 for hz in voiced))
                if midi in (40, 84):
                    boundary = 82.4068892282175 if midi == 40 else 1046.5022612023945
                    self.assertFalse(any(abs(hz - boundary) < 1e-10 for hz in voiced))


class PrivateInputBindingTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="voxide-tracking-binding-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.audio = self.root / "approved.wav"
        self.replacement = self.root / "replacement.wav"
        write_wav(self.audio, 48000, [.1] * 100)
        write_wav(self.replacement, 48000, [.2] * 100)
        self.manifest = self.root / "corpus.json"
        self.manifest.write_text(json.dumps({"sources": [{"id": "dev", "audio": {"path": "approved.wav", "sha256": sha256(self.audio)}}]}))

    def test_replacement_after_validation_is_not_approved(self):
        with patch("tracking_evaluation.select_sources", return_value=["dev"]):
            permitted = permitted_development(self.manifest)
        self.audio.write_bytes(self.replacement.read_bytes())
        with self.assertRaisesRegex(ValueError, "registered digest"):
            approved_private_audio(self.audio, permitted[self.audio])

    def test_decoder_receives_only_the_hashed_snapshot(self):
        expected_bytes = self.audio.read_bytes()
        expected_info, expected_samples = read_wav(self.audio)
        def decode(data):
            self.assertEqual(data, expected_bytes)
            # Even a swap-and-restore during decoding cannot substitute its PCM.
            self.audio.write_bytes(self.replacement.read_bytes())
            result = read_wav_bytes(data)
            self.audio.write_bytes(expected_bytes)
            return result
        with patch("tracking_evaluation.read_wav_bytes", side_effect=decode):
            info, samples = approved_private_audio(self.audio, sha256(self.audio))
        self.assertEqual(info, expected_info)
        self.assertEqual(samples, expected_samples)

    def test_manifest_change_during_validation_is_refused(self):
        def select(*args, **kwargs):
            self.manifest.write_text('{"sources":[]}')
            return ["dev"]
        with patch("tracking_evaluation.select_sources", side_effect=select), self.assertRaisesRegex(ValueError, "manifest changed"):
            permitted_development(self.manifest)


if __name__ == "__main__":
    unittest.main()
