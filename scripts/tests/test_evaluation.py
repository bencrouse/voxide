import copy
import importlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
common = importlib.import_module("evaluation_common")
fixtures = importlib.import_module("evaluation_fixtures")
metrics = importlib.import_module("evaluation_metrics")
corpus = importlib.import_module("evaluation_corpus")
evaluation = importlib.import_module("evaluation")


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="voxide-evaluation-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_contract_includes_two_octave_extremes_and_pending_human_policy(self):
        contract = evaluation.validate_contract()
        self.assertEqual(contract["support"]["shift_semitones_min"], -24)
        self.assertEqual(contract["support"]["shift_semitones_max"], 24)
        self.assertAlmostEqual(common.midi_hz(16), 20.601722307, places=7)
        self.assertAlmostEqual(common.midi_hz(108), 4186.00904481, places=7)
        self.assertEqual(contract["musical_policy_approval"], "pending")

    def test_fixture_bytes_match_frozen_catalog_without_modifying_expected_files(self):
        before = common.sha256(common.FIXTURES / "catalog.json")
        expected = fixtures.validate(common.FIXTURES)
        actual = fixtures.generate(self.root / "generated")
        self.assertEqual(actual, expected)
        for entry in expected["cases"]:
            for record in entry["files"].values():
                self.assertEqual(common.sha256(self.root / "generated" / record["path"]), record["sha256"])
        self.assertEqual(common.sha256(common.FIXTURES / "catalog.json"), before)
        with self.assertRaises(FileExistsError):
            fixtures.generate(self.root / "generated")

    def test_fixtures_reject_missing_and_corrupt_audio(self):
        # Use one generated suite for destructive negative controls; expected assets stay read-only.
        directory = self.root / "generated"
        data = fixtures.generate(directory)
        record = data["cases"][0]["files"]["audio"]
        path = directory / record["path"]
        original = path.read_bytes()
        path.write_bytes(original[:-1])
        with self.assertRaisesRegex(ValueError, "checksum"):
            fixtures.validate(directory)
        path.write_bytes(original)
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            fixtures.validate(directory)

    def test_wav_roundtrip_pcm24_and_invalid_signal(self):
        path = self.root / "audio.wav"
        common.write_wav(path, 48000, [-0.5, 0.0, 0.25])
        info, values = common.read_wav(path)
        self.assertEqual((info["frames"], info["bits"], info["channels"]), (3, 24, 1))
        self.assertLess(max(abs(a - b) for a, b in zip(values, [-0.5, 0, 0.25])), 1e-7)
        with self.assertRaises(FileExistsError): common.write_wav(path, 48000, [0.1])
        for samples in ([math.nan], [math.inf], [1.0], [-1.1], []):
            with self.assertRaises(ValueError): common.write_wav(self.root / "bad.wav", 48000, samples)

    def test_json_nonfinite_duplicate_keys_and_exclusive_writes(self):
        path = self.root / "data.json"
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":1e999}', '{"a":-1e999}',
                     '{"nested":[{"value":1e309}]}', '{"nested":{"value":-1e309}}'):
            path.write_text(text)
            with self.assertRaises(ValueError): common.load_json(path)
        with self.assertRaises(FileExistsError): common.write_json(path, {})
        path.write_text('{"a":1e308}')
        self.assertTrue(math.isfinite(common.load_json(path)["a"]))

    def test_paths_reject_traversal_absolute_and_symlinks(self):
        for name in ("../elsewhere", "/absolute", "nested/../../escape"):
            with self.assertRaises(ValueError): common.contained(self.root, name)
        (self.root / "link").symlink_to(self.root / "missing")
        with self.assertRaises(ValueError): common.contained(self.root, "link")

    def test_controls_partition_invariant_and_bounds(self):
        _, reference, controls = fixtures.synthesize("sine-mid", 48000)
        info = {"sample_rate": reference["sample_rate"], "frames": reference["frames"]}
        events = common.validate_controls(controls, info, reference["source_pcm_sha256"])
        for blocks in ([32], [64], [128], [257], [512], [1024], [32, 257, 64, 1024, 128, 512]):
            scheduled = common.partition_controls(events, reference["frames"], blocks)
            recovered = [dict((k, v) for k, v in event.items() if k not in ("block_start", "offset"))
                         for event in scheduled]
            self.assertEqual(recovered, events)
            self.assertTrue(all(event["sample"] == event["block_start"] + event["offset"] for event in scheduled))
        for field, value in (("note", -1), ("note", 128), ("sample", -1), ("sample", reference["frames"]),
                             ("channel", 0), ("channel", 17), ("velocity", 128), ("sample", True)):
            broken = copy.deepcopy(controls)
            broken["events"][0][field] = value
            with self.assertRaises(ValueError): common.validate_controls(broken, info, reference["source_pcm_sha256"])
        for blocks in ([], [0], [-1], [True]):
            with self.assertRaises(ValueError): common.partition_controls(events, reference["frames"], blocks)

    def test_pitch_and_formant_calibration_with_negative_controls(self):
        report = evaluation.calibrate()
        self.assertEqual(report["status"], "pass")
        self.assertEqual(len(report["measurements"]), 14)
        self.assertTrue(report["off_by_one_detected"])

    def test_independent_pitch_estimator_recovers_known_semitone_and_octave_faults(self):
        for semitones in (1, 12, 24, -24):
            hz = 220 * 2 ** (semitones / 12)
            samples = [0.1 * math.sin(2 * math.pi * hz * i / 48000) for i in range(12000)]
            measured = metrics.estimate_pitch(samples, 48000)
            self.assertAlmostEqual(metrics.cents(measured["f0_hz"], 220), semitones * 100, delta=2)
        self.assertIsNone(metrics.estimate_pitch([0.0] * 4096, 48000)["f0_hz"])
        self.assertIsNone(metrics.estimate_pitch(fixtures.noise(4096), 48000)["f0_hz"])

    def test_pitch_scores_missing_estimates_and_uncertainty_never_become_passes(self):
        _, reference, _ = fixtures.synthesize("sine-mid", 48000)
        expected = reference["grid"]
        observed = [{"sample": f["sample"], "f0_hz": f["f0_hz"]} for f in expected]
        score = metrics.score_pitch(expected, observed)
        self.assertEqual(score["accuracy"], 1)
        self.assertLess(score["accuracy_wilson95"][0], 1)
        observed[0]["f0_hz"] *= 2
        observed[1]["f0_hz"] = None
        expected[2]["uncertain"] = True
        score = metrics.score_pitch(expected, observed)
        self.assertEqual(score["octave_errors"], 1)
        self.assertEqual(score["missing_voiced_estimates"], 1)
        self.assertEqual(score["excluded_reference_frames"], 1)
        self.assertLess(score["accuracy"], 1)
        observed[0]["sample"] += 1
        with self.assertRaises(ValueError): metrics.score_pitch(expected, observed)
        for frame in expected: frame["uncertain"] = True
        observed[0]["sample"] -= 1
        self.assertEqual(metrics.score_pitch(expected, observed)["status"], "pending")

    def test_sparse_three_and_four_octave_faults_cannot_pass_the_octave_gate(self):
        reference = {"schema": "voxide.annotation.v2", "source_id": "octave-regression", "source_pcm_sha256": "0" * 64,
            "annotator_id": "analytic-oracle", "origin": "synthetic", "sample_rate": 48000,
            "frames": 480000, "landmarks": [],
            "grid": [{"sample": i * 480, "voiced": True, "f0_hz": 110.0,
                      "stable": True, "uncertain": False} for i in range(1000)]}
        reference_path = self.root / "octave-reference.json"
        common.write_json(reference_path, reference)
        observed = {"schema": "voxide.pitch-observations.v2", "source_id": reference["source_id"],
            "source_pcm_sha256": reference["source_pcm_sha256"],
            "reference_sha256": common.sha256(reference_path), "sample_rate": 48000, "frames": 480000,
            "producer": {"id": "test-only", "revision": "test"},
            "grid": [{"sample": f["sample"], "f0_hz": f["f0_hz"]} for f in reference["grid"]]}
        for i, octaves in enumerate((3, -3, 4, -4)):
            observed["grid"][i]["f0_hz"] *= 2 ** octaves
        path = self.root / "octave-observations.json"
        common.write_json(path, observed)
        score = evaluation.score_observations(reference_path, path)
        self.assertGreaterEqual(score["accuracy"], 0.99)
        self.assertEqual(score["octave_errors"], 4)
        self.assertEqual(score["threshold_status"], "fail")

    def test_cents_reports_extreme_finite_errors_without_ratio_underflow(self):
        self.assertTrue(math.isfinite(metrics.cents(5e-324, 440)))
        self.assertTrue(math.isfinite(metrics.cents(1e308, 5e-324)))
        self.assertAlmostEqual(metrics.cents(880, 110), 3600)
        self.assertFalse(common.finite(10 ** 4000))
        with self.assertRaises(ValueError): metrics.cents(10 ** 4000, 110)

    def test_null_detects_gain_missing_tail_and_one_sample_misalignment(self):
        source = [0.0, 0.5, -0.125, 0.0]
        self.assertEqual(metrics.compare_delayed(source, [0.0] * 3 + source, 3)["status"], "pass")
        self.assertEqual(metrics.compare_delayed(source, [0.0] * 3 + [x * 0.9 for x in source], 3)["status"], "fail")
        with self.assertRaises(ValueError): metrics.compare_delayed(source, [0.0] * 2 + source, 3)
        with self.assertRaises(ValueError): metrics.measure_unity_delay([0.0] * 64, [0.0] * 128, 32)

    def test_settling_counts_confirmation_time_and_restarts_on_gaps_or_bad_frames(self):
        frames = [{"sample": i * 480, "f0_hz": 220 if i >= 1 else 440} for i in range(8)]
        self.assertEqual(metrics.settling_sample(frames, 220, 0, 960, 480), 1440)
        self.assertIsNone(metrics.settling_sample(frames[:3], 220, 0, 960, 480))
        self.assertEqual(metrics.settling_sample(frames[:2] + frames[3:], 220, 0, 960, 480), 2400)
        report = metrics.score_response([{"id": "cold", "kind": "cold_onset", "sample": 0, "target_hz": 220}], frames, 48000)
        high = next(g for g in report["groups"] if g["kind"] == "cold_onset" and g["register"] == "high")
        self.assertEqual(high["p95_ms"], 30)
        self.assertEqual(high["status"], "pass")
        frames = [{"sample": i * 480, "f0_hz": None} for i in range(8)]
        report = metrics.score_response([{"id": "cold", "kind": "cold_onset", "sample": 0, "target_hz": 220}], frames, 48000)
        self.assertTrue(any(g["status"] == "fail" and g["missing_decisions"] == 1 for g in report["groups"]))

    def test_control_latency_rejects_early_reordered_missing_and_late_applications(self):
        expected = [{"id": "a", "sample": 7}, {"id": "b", "sample": 23}]
        applied = [{"id": "a", "sample": 135}, {"id": "b", "sample": 151}]
        self.assertEqual(metrics.score_control_response(expected, applied, 48000, 128)["status"], "pass")
        self.assertEqual(metrics.score_control_response(expected, applied, 48000, 64)["status"], "fail")
        with self.assertRaises(ValueError): metrics.score_control_response(expected, applied[:1], 48000, 128)
        with self.assertRaises(ValueError): metrics.score_control_response(expected, list(reversed(applied)), 48000, 128)
        applied[0]["sample"] = 6
        with self.assertRaises(ValueError): metrics.score_control_response(expected, applied, 48000, 128)

    def test_control_application_timestamps_preserve_chronology_and_ties(self):
        expected = [{"id": "a", "sample": 7}, {"id": "b", "sample": 23}]
        reordered = [{"id": "a", "sample": 135}, {"id": "b", "sample": 23}]
        with self.assertRaisesRegex(ValueError, "timestamps reordered"):
            metrics.score_control_response(expected, reordered, 48000, 128)
        ties = [{"id": "a", "sample": 135}, {"id": "b", "sample": 135}]
        self.assertEqual(metrics.score_control_response(expected, ties, 48000, 128)["status"], "pass")

    def test_controls_are_anchored_to_reference_rate_duration_identity_and_pcm(self):
        reference = {"schema": "voxide.controls.v2", "source_id": "test-source", "source_pcm_sha256": "0" * 64,
                     "sample_rate": 44100, "frames": 4410, "events": [
                         {"id": "event-a", "sample": 7, "kind": "note_on", "note": 60, "channel": 1, "velocity": 80}]}
        path = self.root / "controls.json"
        common.write_json(path, reference)
        applications = {"schema": "voxide.control-applications.v2", "reference_sha256": common.sha256(path),
                        "source_id": "test-source", "source_pcm_sha256": "0" * 64,
                        "sample_rate": 44100, "frames": 4410, "control_interval_samples": 256,
                        "events": [{"id": "event-a", "sample": 231}]}
        applied_path = self.root / "applied.json"
        applied_path.write_text(json.dumps(applications))
        result = evaluation.score_applications(path, applied_path)
        self.assertGreater(result["maximum_ms"], 5)
        self.assertEqual(result["status"], "fail")
        for key, value in (("sample_rate", 48000), ("frames", 4800), ("source_id", "other-source"),
                           ("source_pcm_sha256", "1" * 64)):
            changed = dict(applications, **{key: value})
            applied_path.write_text(json.dumps(changed))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "source/timebase mismatch"):
                evaluation.score_applications(path, applied_path)
        legacy = dict(reference, schema="voxide.controls.v1")
        with self.assertRaisesRegex(ValueError, "Unsupported controls"):
            common.validate_controls(legacy)

    def test_noise_and_silence_landmarks_follow_decoded_source_activity(self):
        for rate in (44100, 48000):
            for case in ("noise-bursts", "silence"):
                name = case + "-" + str(rate)
                reference = common.load_json(common.FIXTURES / (name + ".json"))
                info, samples = common.read_wav(common.FIXTURES / (name + ".wav"))
                onsets = [event for event in reference["landmarks"] if event["kind"] == "onset"]
                active = next((i for i, sample in enumerate(samples) if sample != 0), None)
                if case == "silence":
                    self.assertIsNone(active)
                    self.assertEqual(onsets, [])
                else:
                    self.assertEqual(len(onsets), 1)
                    self.assertEqual(onsets[0]["sample"], active)
                    self.assertEqual(active, info["frames"] // 3)

    def test_scoring_uses_current_contract_limits_and_reports_its_digest(self):
        data = common.load_json(common.CONTRACT)
        data["id"] = "test-stricter-contract"
        data["timing_ms"]["midi_target"] = 1
        data["timing_ms"]["recognition_high_p95"] = 10
        data["measurement"]["settling_dwell_ms"] = 30
        data["deterministic_tolerance"] = {"max_abs": 0, "rms": 0}
        path = self.root / "contract.json"
        common.write_json(path, data)
        policy = evaluation.validate_contract(path)
        expected, actual = [{"id": "a", "sample": 7}], [{"id": "a", "sample": 135}]
        self.assertEqual(metrics.score_control_response(expected, actual, 48000, 128)["status"], "pass")
        control = metrics.score_control_response(expected, actual, 48000, 128, policy)
        self.assertEqual(control["status"], "fail")
        self.assertEqual(control["target_ms"], 1)
        source, output = [0.1] * 8, [0.1 + 1e-8] * 8
        self.assertEqual(metrics.compare_delayed(source, output, 0)["status"], "pass")
        null = metrics.compare_delayed(source, output, 0, policy)
        self.assertEqual(null["status"], "fail")
        events = [{"id": "cold", "kind": "cold_onset", "sample": 0, "target_hz": 220}]
        frames = [{"sample": i * 480, "f0_hz": 220} for i in range(5)]
        response = metrics.score_response(events, frames, 48000, policy)
        high = next(g for g in response["groups"] if g["kind"] == "cold_onset" and g["register"] == "high")
        self.assertEqual(high["limit_ms"], 10)
        self.assertEqual(high["p95_ms"], 30)
        self.assertEqual(high["status"], "fail")
        self.assertEqual(response["dwell_ms"], 30)
        for result in (control, null, response):
            self.assertEqual(result["contract_sha256"], common.sha256(path))

    def test_revoked_contract_blocks_scoring_cli_entrypoints(self):
        data = common.load_json(common.CONTRACT)
        data["numerical_approval"]["status"] = "pending"
        path = self.root / "revoked.json"
        common.write_json(path, data)
        missing = str(self.root / "unused.json")
        # Contract rejection precedes input reads; no pass can be emitted under a
        # revoked policy, even by commands which previously bypassed validation.
        commands = (("score-controls", "--reference", missing, "--applications", missing),
                    ("score-response", "--reference", missing, "--decisions", missing),
                    ("score-pitch", "--reference", missing, "--observations", missing),
                    ("compare-lead", "--source", missing, "--output", missing, "--delay-samples", "0"))
        for arguments in commands:
            result = subprocess.run([sys.executable, "scripts/evaluation.py", "--contract", str(path), *arguments],
                                    cwd=ROOT, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Numerical contract approval missing", result.stderr)

    def test_control_render_uses_actual_written_wav_and_refuses_overwrite(self):
        entry = fixtures.validate(common.FIXTURES)["cases"][0]
        source = common.FIXTURES / entry["files"]["audio"]["path"]
        controls = common.FIXTURES / entry["files"]["controls"]["path"]
        report = evaluation.render_control(source, controls, self.root / "render", 137, [32, 257, 64])
        self.assertFalse(report["harmony_rendered"])
        self.assertEqual(report["lead_null"]["status"], "pass")
        self.assertEqual(report["output_frames"], report["input_frames"] + 137)
        with self.assertRaises(FileExistsError): evaluation.render_control(source, controls, self.root / "render", 137, [64])

    def test_annotation_validation_and_independent_agreement(self):
        _, first, _ = fixtures.synthesize("sine-mid", 48000)
        info = {"sample_rate": 48000, "frames": 12000}
        second = copy.deepcopy(first)
        second["annotator_id"] = "person-b"
        self.assertEqual(corpus.compare_annotations(first, second)["status"], "agreement")
        second["grid"][0]["f0_hz"] *= 2
        result = corpus.compare_annotations(first, second)
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["disagreement_samples"], [0])
        second["grid"][0]["sample"] = 1
        with self.assertRaises(ValueError): corpus.compare_annotations(first, second)
        for field, value in (("f0_hz", -1), ("f0_hz", math.nan), ("sample", 12000), ("voiced", 1)):
            broken = copy.deepcopy(first)
            broken["grid"][0][field] = value
            with self.assertRaises(ValueError): corpus.validate_annotation(broken, first["source_id"], info)
        first["grid"][0]["uncertain"] = True
        second = copy.deepcopy(first)
        second["annotator_id"] = "person-b"
        self.assertEqual(corpus.compare_annotations(first, second)["uncertain_frames"], 1)

    def test_annotation_template_is_explicitly_unreviewed_and_all_uncertain(self):
        entry = fixtures.validate(common.FIXTURES)["cases"][0]
        audio = common.FIXTURES / entry["files"]["audio"]["path"]
        output = self.root / "draft.json"
        result = evaluation.annotation_template(audio, entry["id"], "person-a", output)
        self.assertEqual(result["status"], "pending")
        draft = common.load_json(output)
        self.assertEqual(draft["review_status"], "draft")
        self.assertTrue(all(frame["uncertain"] and not frame["stable"] for frame in draft["grid"]))
        with self.assertRaises(FileExistsError): evaluation.annotation_template(audio, entry["id"], "person-a", output)

    def test_annotation_template_and_validation_share_contract_grid_and_pcm_binding(self):
        entry = fixtures.validate(common.FIXTURES)["cases"][0]
        audio = common.FIXTURES / entry["files"]["audio"]["path"]
        data = common.load_json(common.CONTRACT)
        data["id"] = "test-grid-revision"
        data["measurement"]["frame_hop_ms"] = 5
        contract_path = self.root / "fine-grid-policy.json"
        common.write_json(contract_path, data)
        output = self.root / "fine-grid-annotation.json"
        evaluation.annotation_template(audio, entry["id"], "person-a", output, contract_path)
        annotation = common.load_json(output)
        info, source_pcm = common.wav_identity(audio)
        self.assertEqual(annotation["source_pcm_sha256"], source_pcm)
        self.assertEqual(annotation["grid"][1]["sample"], round(5 * info["sample_rate"] / 1000))
        corpus.validate_annotation(annotation, entry["id"], info, source_pcm, evaluation.validate_contract(contract_path))
        with self.assertRaisesRegex(ValueError, "contract sample grid"):
            corpus.validate_annotation(annotation, entry["id"], info, source_pcm)

    def test_control_copy_preserves_pcm_words_at_all_supported_bit_depths(self):
        for bits in (16, 24, 32):
            source = self.root / ("source-" + str(bits) + ".wav")
            values = [-(1 << (bits - 1)), (1 << (bits - 1)) - 1, (1 << (bits - 2)) + 1, -7]
            info = {"sample_rate": 48000, "channels": 1, "bits": bits, "frames": len(values)}
            common.write_pcm(source, info, b"".join(x.to_bytes(bits // 8, "little", signed=True) for x in values))
            controls = self.root / ("controls-" + str(bits) + ".json")
            common.write_json(controls, {"schema": "voxide.controls.v2", "source_id": "test-source",
                "source_pcm_sha256": common.wav_identity(source)[1], "sample_rate": 48000,
                "frames": len(values), "events": []})
            report = evaluation.render_control(source, controls, self.root / ("render-" + str(bits)), 3, [2, 1])
            self.assertEqual(report["bits"], bits)
            self.assertEqual(report["lead_null"]["max_abs"], 0)

    def test_cli_reports_missing_corpus_as_pending_nonzero(self):
        evaluation.initialise_corpus(self.root / "intake")
        result = subprocess.run([sys.executable, "scripts/evaluation.py", "corpus-validate",
                                 str(self.root / "intake/corpus.json")], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "pending")

    def test_pitch_observation_identity_grid_and_failure_gates(self):
        entry = fixtures.validate(common.FIXTURES)["cases"][1]
        reference_path = common.FIXTURES / entry["files"]["reference"]["path"]
        reference = common.load_json(reference_path)
        observed = {"schema": "voxide.pitch-observations.v2", "source_id": reference["source_id"],
                    "source_pcm_sha256": reference["source_pcm_sha256"],
                    "reference_sha256": common.sha256(reference_path), "sample_rate": reference["sample_rate"],
                    "frames": reference["frames"], "producer": {"id": "test-only", "revision": "test"},
                    "grid": [{"sample": f["sample"], "f0_hz": f["f0_hz"]} for f in reference["grid"]]}
        path = self.root / "observed.json"
        path.write_text(json.dumps(observed))
        self.assertEqual(evaluation.score_observations(reference_path, path)["threshold_status"], "pass")
        observed["grid"][0]["f0_hz"] *= 2
        path.write_text(json.dumps(observed))
        self.assertEqual(evaluation.score_observations(reference_path, path)["threshold_status"], "fail")
        for fault in ("hash", "rate", "grid", "f0"):
            data = copy.deepcopy(observed)
            if fault == "hash": data["reference_sha256"] = "0" * 64
            if fault == "rate": data["sample_rate"] = 48000
            if fault == "grid": data["grid"].pop()
            if fault == "f0": data["grid"][0]["f0_hz"] = -1
            path.write_text(json.dumps(data))
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                evaluation.score_observations(reference_path, path)

    def test_response_cli_missing_groups_are_pending_and_controls_require_reference_hash(self):
        reference = self.root / "response.json"
        common.write_json(reference, {"schema": "voxide.response-reference.v1", "source_id": "test-source",
            "sample_rate": 48000, "events": [{"id": "onset", "kind": "cold_onset", "sample": 0, "target_hz": 220}]})
        decisions = self.root / "decisions.json"
        common.write_json(decisions, {"schema": "voxide.decisions.v1", "source_id": "test-source",
            "reference_sha256": common.sha256(reference), "sample_rate": 48000,
            "grid": [{"sample": i * 480, "f0_hz": 220} for i in range(5)]})
        result = subprocess.run([sys.executable, "scripts/evaluation.py", "score-response", "--reference",
                                 str(reference), "--decisions", str(decisions)], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "pending")
        controls = self.root / "controls.json"
        common.write_json(controls, {"schema": "voxide.controls.v2", "source_id": "test-source",
            "source_pcm_sha256": "0" * 64, "sample_rate": 48000, "frames": 4800, "events": [
            {"id": "note-a", "sample": 7, "kind": "note_on", "channel": 1, "note": 60, "velocity": 80}]})
        applications = self.root / "applications.json"
        applied = {"schema": "voxide.control-applications.v2", "reference_sha256": common.sha256(controls),
                   "source_id": "test-source", "source_pcm_sha256": "0" * 64,
                   "sample_rate": 48000, "frames": 4800, "control_interval_samples": 128,
                   "events": [{"id": "note-a", "sample": 135}]}
        applications.write_text(json.dumps(applied))
        command = [sys.executable, "scripts/evaluation.py", "score-controls", "--reference", str(controls),
                   "--applications", str(applications)]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "pass")
        applied["reference_sha256"] = "0" * 64
        applications.write_text(json.dumps(applied))
        self.assertNotEqual(subprocess.run(command, cwd=ROOT, capture_output=True).returncode, 0)

    def test_empty_corpus_is_pending_not_synthetic_human_qualification(self):
        result = evaluation.initialise_corpus(self.root / "intake")
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["sources"], 0)
        self.assertGreaterEqual(len(result["blockers"]), 8)
        manifest = self.root / "intake/corpus.json"
        self.assertEqual(corpus.select_sources(manifest), [])
        with self.assertRaises(ValueError): corpus.select_sources(manifest, "holdout")
        settings = self.root / "settings.json"
        common.write_json(settings, {"id": "settings-001", "approved_for_holdout": True})
        with self.assertRaises(ValueError): corpus.seal_corpus(manifest, settings, self.root / "seal.json")

    def test_percentiles_and_zero_denominator(self):
        self.assertEqual(metrics.percentile([4, 1, 3, 2], 0.5), 2)
        self.assertEqual(metrics.percentile([4, 1, 3, 2], 0.95), 4)
        self.assertIsNone(metrics.wilson(0, 0))
        with self.assertRaises(ValueError): metrics.percentile([], 0.95)


if __name__ == "__main__":
    unittest.main()
