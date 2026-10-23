import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine_evaluation import private_sources
from evaluation_common import write_wav, sha256, wav_identity
from evaluation_contract import load_contract


class PrivateEngineReferenceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="voxide-engine-human-reference-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.audio = self.root / "development.wav"; write_wav(self.audio,48000,[.1]*1000)
        self.info, self.pcm_hash = wav_identity(self.audio)
        self.source = {"id":"development", "audio":{"path":"development.wav","sha256":sha256(self.audio)}, "annotations":[]}
        self.manifest = self.root / "corpus.json"

    def write_manifest(self):
        self.manifest.write_text(json.dumps({"sources":[self.source]}))

    def references(self, origin="human", status="completed"):
        for i in range(2):
            data = {"schema":"voxide.annotation.v2","source_id":"development","source_pcm_sha256":self.pcm_hash,
                    "annotator_id":"person-"+str(i),"origin":origin,"review_status":status,**self.info,
                    "grid":[{"sample":n,"voiced":True,"stable":True,"uncertain":False,"f0_hz":220}
                            for n in range(0,1000,480)]}
            path = self.root / f"annotation-{i}.json"; path.write_text(json.dumps(data))
            self.source["annotations"].append({"path":path.name,"sha256":sha256(path)})

    def run_private(self, output):
        # Production CLI requires ignored evaluation/. Unit evidence stays inside
        # this owned temporary tree; no actual private recording is used.
        with patch("engine_evaluation.ROOT",self.root), patch("engine_evaluation.CONFIGS",[("signalsmith",512,128)]), patch("engine_evaluation.SHIFTS",(0,)):
            return private_sources(self.manifest,output,{"signalsmith":self.root/"not-executed"},load_contract())

    def test_missing_or_unreviewed_references_never_invent_or_render_pitch_truth(self):
        for state in ("missing","draft","synthetic"):
            self.source["annotations"] = []
            if state != "missing": self.references(origin="synthetic" if state=="synthetic" else "human",status="draft" if state=="draft" else "completed")
            self.write_manifest()
            with patch("engine_evaluation.select_sources",return_value=["development"]), patch("engine_evaluation.run_native") as render:
                result = self.run_private(self.root / state)
            self.assertEqual(result["reference_ready_sources"],0)
            render.assert_not_called()

    def test_completed_references_are_not_confused_with_successful_native_render(self):
        self.references(); self.write_manifest()
        with patch("engine_evaluation.select_sources",return_value=["development"]), patch("engine_evaluation.run_native",return_value=None):
            result = self.run_private(self.root / "ready")
        self.assertEqual(result["reference_ready_sources"],1)
        report = json.loads((self.root/"ready/private-report.json").read_text())
        self.assertEqual(report["sources"][0]["successful_renders"],0)
        self.assertEqual(report["sources"][0]["renders"][0]["status"],"native_failed")

    def test_replacement_after_permission_validation_is_rejected(self):
        self.references(); self.write_manifest()
        def replace(*args,**kwargs):
            self.audio.write_bytes(b"unregistered substitute")
            return ["development"]
        with patch("engine_evaluation.select_sources",side_effect=replace), self.assertRaisesRegex(ValueError,"Unregistered private audio"):
            self.run_private(self.root/"replacement")


if __name__ == "__main__": unittest.main()
