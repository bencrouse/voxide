from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import verify_bundle


class ProductBundleTests(unittest.TestCase):
    def verify(self,library="/usr/lib/libc++.1.dylib",section="__text",arch="arm64"):
        with tempfile.TemporaryDirectory() as temp:
            component=Path(temp)/"voxide.component";(component/"Contents").mkdir(parents=True)
            (component/"Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable":"voxide"}))
            def output(command,**_):
                if command[0]=="lipo":return arch
                if command[1]=="-L":return f"voxide:\n\t{library} (compatibility version 1)\n"
                return f"  sectname {section}\n  segname __DATA_CONST\n"
            with patch.object(verify_bundle.subprocess,"check_output",side_effect=output),patch.object(verify_bundle.subprocess,"run"):
                return verify_bundle.verify_linkage(component)

    def test_system_only_product_passes(self):
        self.assertEqual(self.verify(),["/usr/lib/libc++.1.dylib"])

    def test_build_and_audit_libraries_rejected(self):
        for library in ("@rpath/libvoxide_allocation_audit.dylib","/Code/libevaluation.dylib"):
            with self.assertRaisesRegex(ValueError,"dependency"):self.verify(library=library)

    def test_static_interposer_rejected(self):
        with self.assertRaisesRegex(ValueError,"interpose"):self.verify(section="__interpose")

    def test_wrong_architecture_rejected(self):
        with self.assertRaisesRegex(ValueError,"architecture"):self.verify(arch="x86_64")
