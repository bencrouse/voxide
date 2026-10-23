import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine_evaluation import run_native, controls_for, compiled_source_identity


class EngineNativeIdentityTests(unittest.TestCase):
    def test_stale_binaries_and_sanitizer_timings_are_refused(self):
        for problem in ("stale","sanitizer","debug","audit"):
            with tempfile.TemporaryDirectory(prefix="voxide-engine-identity-") as temporary:
                directory = Path(temporary)/"case"
                def render(command, **kwargs):
                    report = {"source_frames":1,"sample_rate":48000,"voices":1,"profile":"Release","sanitizer":"",
                              "audit_available":True,"compiled_source_identity":compiled_source_identity()}
                    if problem == "stale": report["compiled_source_identity"] = "0"*64
                    if problem == "sanitizer": report["sanitizer"] = "address"
                    if problem == "debug": report["profile"] = "Debug"
                    if problem == "audit": report["audit_available"] = False
                    (directory/"render-native.json").write_text(json.dumps(report))
                    return subprocess.CompletedProcess(command,0,b"",b"")
                with patch("engine_evaluation.subprocess.run",side_effect=render), self.subTest(problem=problem), self.assertRaises(ValueError):
                    run_native(Path(temporary)/"not-executed",(512,128),[.1],48000,1,[controls_for([0,0,0],220)],directory)


if __name__ == "__main__": unittest.main()
