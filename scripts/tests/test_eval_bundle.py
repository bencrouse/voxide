from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import verify_eval_bundle as bundle


class EvalBundleTests(unittest.TestCase):
    def fixture(self,root,identifier="com.voxide.audio.studioeval"):
        component=root/"Eval.component";contents=component/"Contents";contents.mkdir(parents=True)
        info={"CFBundleIdentifier":identifier,"CFBundleExecutable":"Eval",
              "AudioComponents":[{"type":"aufx","subtype":"Vx6b","manufacturer":"Vxid"}]}
        (contents/"Info.plist").write_bytes(plistlib.dumps(info))
        return component

    def verify(self,path,arch="arm64",library="/usr/lib/libc++.1.dylib",sign_error=False,sections="sectname __text\n"):
        def output(command,**kwargs):
            if command[:2]==["otool","-l"]:return sections
            return arch if command[0]=="lipo" else "Eval:\n\t"+library+" (compatibility version 1.0.0)\n"
        with patch.object(bundle.subprocess,"check_output",side_effect=output), \
             patch.object(bundle.subprocess,"run",side_effect=subprocess.CalledProcessError(1,"codesign") if sign_error else None):
            return bundle.verify(path)

    def test_separate_component_and_only_system_dependencies_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            result=self.verify(self.fixture(Path(temp)))
            self.assertEqual(result["subtype"],"Vx6b")

    def test_product_identity_is_refused_before_native_tools(self):
        with tempfile.TemporaryDirectory() as temp:
            path=self.fixture(Path(temp),"com.voxide.audio.voxide")
            with patch.object(bundle.subprocess,"check_output") as tools,self.assertRaisesRegex(ValueError,"identity"):
                bundle.verify(path)
            tools.assert_not_called()

    def test_allocator_interposer_or_other_build_dylib_is_rejected(self):
        for library in ("/Code/build/libengine_allocation_audit.dylib","@rpath/libcustom.dylib"):
            with tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(ValueError,"dependency"):self.verify(self.fixture(Path(temp)),library=library)

    def test_wrong_architecture_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,"architecture"):self.verify(self.fixture(Path(temp)),arch="x86_64")

    def test_static_interposer_is_rejected_even_with_system_only_dependencies(self):
        for segment in ("__DATA","__DATA_CONST"):
            with tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(ValueError,"interpose"):
                    self.verify(self.fixture(Path(temp)),sections=f"Section\n  sectname __interpose\n  segname {segment}\n")

    def test_unsigned_bundle_is_not_reported_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(subprocess.CalledProcessError):self.verify(self.fixture(Path(temp)),sign_error=True)
