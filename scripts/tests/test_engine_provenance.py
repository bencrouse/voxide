import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine_evaluation import capture_provenance, verify_provenance, private_sources
from evaluation_contract import load_contract


class EngineProvenanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="voxide-engine-provenance-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.build = self.root / "build"; self.build.mkdir()
        for name in ("voxide_signalsmith_eval","voxide_rubberband_eval","libengine_allocation_audit.dylib","CMakeCache.txt","compile_commands.json"):
            (self.build/name).write_text("identity-"+name)
        self.files = {"scripts/check.py":b"dirty tracked helper", "untracked/helper.py":b"new source"}
        for name,data in self.files.items():
            path = self.root/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
        def fingerprint():
            return {name:hashlib.sha256((self.root/name).read_bytes()).hexdigest() for name in self.files}
        for target,value in (("ROOT",self.root),("source_fingerprint",fingerprint),("verified_dependencies",lambda build:{"verified":True}),
                             ("compiled_source_identity",lambda:"compiled")):
            mock = patch("engine_evaluation."+target,value)
            mock.start(); self.addCleanup(mock.stop)
        mock = patch("engine_evaluation.subprocess.check_output",return_value="tool-identity\n")
        mock.start(); self.addCleanup(mock.stop)
        mock = patch("engine_evaluation.platform.platform",return_value="test-platform")
        mock.start(); self.addCleanup(mock.stop)
        mock = patch("engine_evaluation.sha256",side_effect=lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                     if Path(path).is_file() else "contract-or-protocol")
        mock.start(); self.addCleanup(mock.stop)

    def test_archive_includes_dirty_helpers_and_rejects_runtime_or_source_changes(self):
        directory = self.root / "evidence"; directory.mkdir()
        provenance = capture_provenance(self.build,directory)
        for name,data in self.files.items(): self.assertEqual((directory/"source-snapshot"/name).read_bytes(),data)
        self.assertEqual(json.loads((directory/"provenance.json").read_text()),provenance)
        for relative in ("build/libengine_allocation_audit.dylib","build/voxide_signalsmith_eval","build/CMakeCache.txt","scripts/check.py"):
            path = self.root/relative; original = path.read_bytes(); path.write_bytes(b"replacement")
            with self.subTest(path=relative), self.assertRaises(ValueError): verify_provenance(provenance,self.build)
            path.write_bytes(original)

    def test_private_preflight_retains_the_same_complete_build_provenance(self):
        manifest = self.root/"corpus.json"; manifest.write_text(json.dumps({"sources":[]}))
        directory = self.root/"evaluation/private"
        with patch("engine_evaluation.select_sources",return_value=[]):
            private_sources(manifest,directory,{},load_contract(),build=self.build)
        report = json.loads((directory/"private-report.json").read_text())
        self.assertTrue(report["source_build_unchanged"])
        provenance = json.loads((directory/report["provenance"]).read_text())
        self.assertEqual(set(provenance["binaries"]),{"signalsmith","rubberband"})
        self.assertIn("allocation_audit_library_sha256",provenance)
        self.assertEqual(provenance["dependencies"],{"verified":True})


if __name__ == "__main__": unittest.main()
