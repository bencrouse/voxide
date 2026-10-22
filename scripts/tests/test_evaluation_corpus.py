import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
common = importlib.import_module("evaluation_common")
corpus = importlib.import_module("evaluation_corpus")


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="voxide-corpus-tests-")
        cls.root = Path(cls.temp.name).resolve()
        # Completely synthetic stand-ins exercise validation, NEVER count as real
        # singers/consent/listening evidence in a report. The manifest is test-only.
        reviewers = [{"id": "person-" + str(i), "independent": i < 4,
                      "roles": ["listener", "annotator", "singer", "engineer_producer"]}
                     for i in range(6)]
        cls.baseline = {"schema": "voxide.corpus.v1", "id": "test-corpus", "split_approved": True,
                        "reviewers": reviewers, "sources": []}
        for i in range(26):
            source_id = "test-source-" + str(i)
            audio = cls.root / (source_id + ".wav")
            raw = (i + 1).to_bytes(2, "little", signed=True) + bytes(48000 * 10 * 2 - 2)
            with wave.open(str(audio), "wb") as stream:
                stream.setparams((1, 2, 48000, 480000, "NONE", "not compressed"))
                stream.writeframes(raw)
            annotations = []
            for person in (0, 1):
                path = cls.root / (source_id + "-" + str(person) + ".json")
                annotation = {"schema": "voxide.annotation.v2", "source_id": source_id,
                              "source_pcm_sha256": common.wav_identity(audio)[1],
                              "annotator_id": "person-" + str(person), "origin": "human", "review_status": "completed",
                              "sample_rate": 48000, "frames": 480000,
                              "grid": [{"sample": sample, "voiced": True, "f0_hz": 220.0,
                                        "stable": True, "uncertain": False}
                                       for sample in range(0, 480000, 480)], "landmarks": []}
                common.write_json(path, annotation)
                annotations.append({"path": path.name, "sha256": common.sha256(path)})
            speaker = i % 6
            cls.baseline["sources"].append({"id": source_id, "speaker_id": "singer-" + str(speaker),
                "split": "holdout" if speaker >= 4 else "development", "origin": "recording",
                "purpose": "corpus_excerpt" if i < 24 else "user_session", "coverage_tags": ["test-only"],
                "rights": {"local_evaluation_permitted": True, "consent_id": "test-only-not-real-consent"},
                "sample_rate": 48000, "channels": 1, "bits": 16, "frames": 480000,
                "audio": {"path": audio.name, "sha256": common.sha256(audio)}, "annotations": annotations})

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def manifest(self, data=None):
        path = self.root / "test-manifest.json"
        path.write_text(json.dumps(self.baseline if data is None else data))
        return path

    def test_structural_positive_control_and_default_development_selection(self):
        path = self.manifest()
        result = corpus.validate_corpus(path)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["sources"], 26)
        selected = corpus.select_sources(path)
        self.assertTrue(selected)
        expected = {s["id"] for s in self.baseline["sources"] if s["split"] == "development"}
        self.assertEqual(set(selected), expected)

    def test_negative_controls_for_rights_hashes_timebase_paths_duplicates_and_leakage(self):
        for fault in ("rights", "hash", "metadata", "leak", "path", "duplicate_id", "duplicate_audio", "reviewer", "purpose"):
            with self.subTest(fault=fault):
                data = copy.deepcopy(self.baseline)
                source = data["sources"][0]
                if fault == "rights": source["rights"]["local_evaluation_permitted"] = False
                if fault == "hash": source["audio"]["sha256"] = "0" * 64
                if fault == "metadata": source["frames"] -= 1
                if fault == "leak": source["split"] = "holdout"
                if fault == "path": source["audio"]["path"] = "../escape.wav"
                if fault == "duplicate_id": data["sources"][1]["id"] = source["id"]
                if fault == "duplicate_audio": data["sources"][1]["audio"] = source["audio"]
                if fault == "reviewer": data["reviewers"][1]["id"] = data["reviewers"][0]["id"]
                if fault == "purpose": source["purpose"] = "invented"
                with self.assertRaises(ValueError): corpus.validate_corpus(self.manifest(data))

    def test_missing_annotations_or_people_or_split_approval_cannot_qualify(self):
        for fault in ("annotation", "people", "approval", "passages", "independence"):
            data = copy.deepcopy(self.baseline)
            if fault == "annotation": data["sources"][0]["annotations"] = []
            if fault == "people": data["reviewers"] = data["reviewers"][:2]
            if fault == "approval": data["split_approved"] = False
            if fault == "passages":
                for s in data["sources"]: s["purpose"] = "corpus_excerpt"
            if fault == "independence":
                for p in data["reviewers"]: p["independent"] = False
            with self.subTest(fault=fault):
                self.assertEqual(corpus.validate_corpus(self.manifest(data))["status"], "pending")

    def test_replaced_audio_cannot_reuse_same_id_duration_and_old_annotations(self):
        data = copy.deepcopy(self.baseline)
        audio = self.root / "replacement.wav"
        info = {"sample_rate": 48000, "channels": 1, "bits": 16, "frames": 480000}
        common.write_pcm(audio, info, (3000).to_bytes(2, "little", signed=True) + bytes(480000 * 2 - 2))
        data["sources"][0]["audio"] = {"path": audio.name, "sha256": common.sha256(audio)}
        path = self.manifest(data)
        with self.assertRaisesRegex(ValueError, "Annotation source PCM mismatch"):
            corpus.validate_corpus(path)

    def test_duplicate_pcm_is_rejected_even_when_riff_metadata_differs(self):
        data = copy.deepcopy(self.baseline)
        original = (self.root / data["sources"][0]["audio"]["path"]).read_bytes()
        chunk = b"JUNK" + (4).to_bytes(4, "little") + b"test"
        content = original[:4] + (len(original) - 8 + len(chunk)).to_bytes(4, "little") + original[8:12] + chunk + original[12:]
        audio = self.root / "different-container.wav"
        audio.write_bytes(content)
        self.assertNotEqual(common.sha256(audio), data["sources"][0]["audio"]["sha256"])
        data["sources"][1]["audio"] = {"path": audio.name, "sha256": common.sha256(audio)}
        with self.assertRaisesRegex(ValueError, "Duplicate recording PCM"):
            corpus.validate_corpus(self.manifest(data))

    def test_all_holdout_approvals_are_required_by_sealing_and_selection(self):
        path = self.manifest()
        approved = common.load_json(common.CONTRACT)
        approved["musical_policy_approval"] = approved["measurement_protocol_approval"] = approved["resource_approval"] = "approved"
        approved["listening"]["protocol_status"] = "approved"
        contract = self.root / "approvals-contract.json"
        settings = self.root / "approvals-settings.json"
        seal = self.root / "approvals-seal.json"
        for key in ("musical_policy_approval", "measurement_protocol_approval", "resource_approval", "listening", "numerical_approval"):
            data = copy.deepcopy(approved)
            if key == "listening": data[key]["protocol_status"] = "pending"
            elif key == "numerical_approval": data[key]["status"] = "pending"
            else: data[key] = "pending"
            contract.write_text(json.dumps(data))
            configuration = {"schema": "voxide.frozen-settings.v1", "id": "test-settings",
                "approved_for_holdout": True, "contract_sha256": common.sha256(contract),
                "candidate": {"id": "test-only", "revision": "test-only", "parameters": {"shift": 0}}}
            settings.write_text(json.dumps(configuration))
            seal.unlink(missing_ok=True)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "approval"):
                corpus.seal_corpus(path, settings, seal, contract)
            # Even a self-consistent seal fabricated by the old implementation
            # cannot bypass the approval checks on the selection entry point.
            seal.write_text(json.dumps({"schema": "voxide.holdout-seal.v1", "corpus_files": corpus.corpus_files(path),
                "contract_sha256": common.sha256(contract), "settings_sha256": common.sha256(settings)}))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "approval"):
                corpus.select_sources(path, "holdout", seal, settings, True, contract)

    def test_holdout_seal_rejects_unapproved_access_changed_settings_and_changed_annotations(self):
        path = self.manifest()
        contract = self.root / "test-contract.json"
        policy = common.load_json(common.CONTRACT)
        policy["musical_policy_approval"] = "approved"  # Test-only approval, not project evidence.
        policy["measurement_protocol_approval"] = "approved"
        policy["listening"]["protocol_status"] = "approved"
        policy["resource_approval"] = "approved"
        contract.write_text(json.dumps(policy))
        settings = self.root / "test-settings.json"
        settings.write_text(json.dumps({"id": "candidate-settings", "approved_for_holdout": False}))
        seal = self.root / "test-seal.json"
        with self.assertRaises(ValueError): corpus.seal_corpus(path, settings, seal, contract)
        settings.write_text(json.dumps({"schema": "voxide.frozen-settings.v1", "id": "candidate-settings",
            "approved_for_holdout": True, "contract_sha256": common.sha256(contract),
            "candidate": {"id": "test-only", "revision": "test-only", "parameters": {"shift": 0}}}))
        seal.unlink(missing_ok=True)
        with self.assertRaisesRegex(ValueError, "Musical-policy"):
            corpus.seal_corpus(path, settings, seal)  # Real project approval is still pending.
        corpus.seal_corpus(path, settings, seal, contract)
        with self.assertRaises(ValueError): corpus.select_sources(path, "holdout", seal, settings, contract_path=contract)
        selected = corpus.select_sources(path, "holdout", seal, settings, True, contract)
        self.assertTrue(selected)
        with self.assertRaises(FileExistsError): corpus.seal_corpus(path, settings, seal, contract)
        original = settings.read_text()
        settings.write_text(original + " ")
        with self.assertRaises(ValueError): corpus.select_sources(path, "holdout", seal, settings, True, contract)
        settings.write_text(original)
        annotation = self.root / self.baseline["sources"][0]["annotations"][0]["path"]
        contents = annotation.read_text()
        try:
            annotation.write_text(contents + " ")
            with self.assertRaises(ValueError): corpus.select_sources(path, "holdout", seal, settings, True, contract)
        finally:
            annotation.write_text(contents)
        contents = contract.read_text()
        contract.write_text(contents + " ")
        with self.assertRaises(ValueError): corpus.select_sources(path, "holdout", seal, settings, True, contract)


if __name__ == "__main__":
    unittest.main()
