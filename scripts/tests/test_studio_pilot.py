import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import studio_pilot


class StudioPilotPreparationTests(unittest.TestCase):
    def test_versioned_scope_preserves_original_contract_and_two_candidates(self):
        scope, protocol = studio_pilot.validate_documents()
        original = studio_pilot.load_json(studio_pilot.ROOT / "docs/evidence/pr-02/contract.json")
        self.assertEqual(original["support"]["shift_semitones_max"], 24)
        self.assertEqual(scope["support"]["shift_semitones_max"], 12)
        self.assertEqual(len(protocol["candidates"]), 2)
        self.assertFalse(protocol["reference"]["assistant_auditioned"])

    def test_candidate_expansion_and_musical_change_are_refused(self):
        scope, protocol = studio_pilot.validate_documents()
        for mutation in ("candidate", "voicing", "shift", "approval"):
            changed = copy.deepcopy(protocol)
            if mutation == "candidate": changed["candidates"].append(copy.deepcopy(changed["candidates"][0]))
            elif mutation == "voicing": changed["initial_trial"]["degrees"] = [0, 0, 0]
            elif mutation == "shift": changed["initial_trial"]["shift_guard_semitones"] = [-7, 7]
            else: changed["status"] = "approved"
            with patch("studio_pilot.load_json", side_effect=[scope, changed]), self.subTest(mutation=mutation), self.assertRaises(ValueError):
                studio_pilot.validate_documents()

    def test_retained_quality_gate_cannot_be_weakened(self):
        scope, protocol = studio_pilot.validate_documents()
        scope["retained"]["pitch_tolerance_cents"] = 100
        with patch("studio_pilot.load_json", side_effect=[scope, protocol]), self.assertRaisesRegex(ValueError, "Retained technical gate changed"):
            studio_pilot.validate_documents()

    def prepare_fixture(self, root, split="development", permission=True):
        directory = root / "evaluation/existing"
        directory.mkdir(parents=True)
        audio = directory / "private.wav"
        audio.write_bytes(b"not audio: preparation must never decode or hash this payload")
        source = {"id": "development-a", "split": split, "origin": "recording", "sample_rate": 48000,
                  "frames": 576000, "channels": 1, "rights": {"local_evaluation_permitted": permission, "consent_id": "local-consent"},
                  "audio": {"path": "private.wav", "sha256": "a"*64}, "annotations": []}
        manifest = directory / "corpus.json"
        manifest.write_text(json.dumps({"schema": "voxide.corpus.v1", "sources": [source]}))
        return manifest, audio

    def test_preparation_never_reads_audio_or_invents_render_approval(self):
        documents = studio_pilot.validate_documents()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            manifest, audio = self.prepare_fixture(root)
            original = Path.read_bytes
            original_hash = studio_pilot.sha256
            def guarded(path):
                if path == audio: raise AssertionError("Private audio was read before trial approval")
                return original(path)
            def guarded_hash(path):
                if Path(path) == audio: raise AssertionError("Private audio was hashed before trial approval")
                return original_hash(path)
            with patch("studio_pilot.ROOT", root), patch("studio_pilot.validate_documents", return_value=documents), \
                 patch("studio_pilot.evidence_summary", return_value={"scope": "test fixture"}), patch.object(Path, "read_bytes", guarded), \
                 patch("studio_pilot.sha256", side_effect=guarded_hash):
                result = studio_pilot.propose(manifest)
            record = json.loads(result.read_text())
            self.assertEqual(record["status"], "pending_explicit_trial_approval")
            self.assertFalse(record["audio_payload_read"])
            self.assertFalse(record["audio_identity_verified"])
            self.assertFalse(record["private_render_authorized"])
            self.assertFalse(record["annotation_exception_approved"])
            self.assertEqual(record["target_key_scale"], "pending_user_selection")
            self.assertEqual(record["source"]["registered_annotations"], 0)

    def test_holdout_and_missing_permission_are_refused(self):
        documents = studio_pilot.validate_documents()
        for split, permission in (("holdout", True), ("development", False)):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                manifest, _ = self.prepare_fixture(root, split, permission)
                with patch("studio_pilot.ROOT", root), patch("studio_pilot.validate_documents", return_value=documents), self.assertRaises(ValueError):
                    studio_pilot.propose(manifest)
                self.assertFalse((root / "evaluation/pr-06a").exists())

    def test_outside_manifest_is_refused(self):
        documents = studio_pilot.validate_documents()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            with patch("studio_pilot.ROOT", root), patch("studio_pilot.validate_documents", return_value=documents), self.assertRaises(ValueError):
                studio_pilot.propose(root / "outside.json")

    def test_output_ancestor_symlinks_are_rejected_before_metadata_read(self):
        documents = studio_pilot.validate_documents()
        for ancestor in ("evaluation", "evaluation/pr-06a"):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                public = root/"docs/public-output"; public.mkdir(parents=True)
                link = root/ancestor; link.parent.mkdir(parents=True, exist_ok=True); link.symlink_to(public, target_is_directory=True)
                with patch.object(studio_pilot, "ROOT", root), patch.object(studio_pilot, "validate_documents", return_value=documents), \
                     patch.object(Path, "read_bytes", side_effect=AssertionError("Metadata read before destination check")), self.assertRaisesRegex(ValueError, "Symlink"):
                    studio_pilot.propose(root/"evaluation/missing/corpus.json")
                self.assertEqual(list(public.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
