import contextlib
import io
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import au


class AURefreshTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="voxide-refresh-tests-");self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve();self.source=self.root/"build/voxide.component"
        contents=self.source/"Contents";contents.mkdir(parents=True)
        (contents/"Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier":au.BUNDLE_ID,
            "CFBundleShortVersionString":"0.5.0","AudioComponents":[au.IDENTITY]}))
        (contents/"binary").write_bytes(b"generated fixture, not an AU")
        self.components=self.root/"Components";self.state=self.root/"state"
        self.target=self.components/au.COMPONENT;self.ledger=self.state/"au-install.json"
        self.output=self.root/"report";self.output.mkdir();self.result={};self.sleep=Mock();self.commands=[]

    def install(self):return au.install(self.source,self.components,self.state,signer=lambda _:None)

    @staticmethod
    def text(version):
        return "VALIDATING AUDIO UNIT: 'aumf' - 'Vx00' - 'Vxid'\nComponent Version: "+version+"\nAU VALIDATION SUCCEEDED.\n"

    def validate_fixture(self,outputs,*,delays=(.01,.02),mutate=None):
        responses=iter(outputs)
        def process(command,**kwargs):
            self.commands.append(command)
            if command[0]=="codesign":
                self.assertNotIn("--force",command)
                return subprocess.CompletedProcess(command,0)
            self.assertEqual(command,["launchctl","asuser",str(au.os.getuid()),"/usr/bin/auval","-v","aumf","Vx00","Vxid"])
            code,text=next(responses);kwargs["stdout"].write(text)
            if mutate:mutate()
            return subprocess.CompletedProcess(command,code)
        with patch.object(au.subprocess,"run",side_effect=process),contextlib.redirect_stdout(io.StringIO()):
            au.validate(self.components,self.state,self.output,self.result,retry_delays=delays,sleeper=self.sleep)

    def test_install_refreshes_only_copied_bundle_timestamp(self):
        au.os.utime(self.source,(1_500_000_000,1_500_000_000))
        before=au.fingerprint(self.source);stamp=self.source.stat().st_mtime_ns
        self.install()
        self.assertEqual(self.source.stat().st_mtime_ns,stamp)
        self.assertGreater(self.target.stat().st_mtime_ns,stamp)
        self.assertEqual(au.fingerprint(self.source),before);self.assertEqual(au.fingerprint(self.target),before)

    def test_matching_version_refreshes_owned_directory_without_retry(self):
        self.install();before=au.fingerprint(self.target);ledger=self.ledger.read_bytes()
        neighbor=self.components/"nitride.component";neighbor.mkdir();(neighbor/"keep").write_bytes(b"untouched")
        stamp=neighbor.stat().st_mtime_ns;au.os.utime(self.target,(1_500_000_000,1_500_000_000))
        self.validate_fixture([(0,self.text("0.5.0"))])
        self.sleep.assert_not_called();self.assertEqual(len(self.commands),2)
        self.assertEqual(self.result["validation_attempts"],[{"log":"auval.log","status":"pass","exit_code":0}])
        self.assertTrue(self.result["bundle_timestamp_refreshed"])
        self.assertGreater(self.target.stat().st_mtime,1_500_000_000)
        self.assertEqual(au.fingerprint(self.target),before);self.assertEqual(self.ledger.read_bytes(),ledger)
        self.assertEqual(neighbor.stat().st_mtime_ns,stamp);self.assertEqual((neighbor/"keep").read_bytes(),b"untouched")

    def test_stale_version_retries_and_retains_every_attempt(self):
        self.install();self.validate_fixture([(0,self.text("0.3.0")),(0,self.text("0.3.0")),(0,self.text("0.5.0"))])
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list],[.01,.02])
        self.assertEqual([r["status"] for r in self.result["validation_attempts"]],["stale_registry_version","stale_registry_version","pass"])
        self.assertEqual({p.name for p in self.output.iterdir()},{"auval.log","auval-retry-1.log","auval-retry-2.log"})
        self.assertIn("0.3.0",(self.output/"auval.log").read_text())

    def test_exhausted_stale_version_still_fails(self):
        self.install()
        with self.assertRaises(au.RegistryVersionMismatch):self.validate_fixture([(0,self.text("0.3.0"))]*3)
        self.assertEqual(self.sleep.call_count,2);self.assertEqual(len(self.result["validation_attempts"]),3)
        self.assertTrue(all(r["status"]=="stale_registry_version" for r in self.result["validation_attempts"]))

    def test_failure_wrong_identity_or_missing_version_never_retried(self):
        for kind in ("exit","identity","version","success"):
            with self.subTest(kind=kind):
                self.install();self.output=self.root/("report-"+kind);self.output.mkdir();self.sleep.reset_mock()
                code=1 if kind=="exit" else 0;text=self.text("0.3.0")
                if kind=="identity":text=text.replace("Vxid","NTRD")
                if kind=="version":text=text.replace("Component Version: 0.3.0\n","")
                if kind=="success":text=text.replace("AU VALIDATION SUCCEEDED.","FAILED")
                with self.assertRaises((ValueError,subprocess.CalledProcessError)):self.validate_fixture([(code,text)])
                self.sleep.assert_not_called();self.assertEqual(len(self.result["validation_attempts"]),1)

    def test_changed_bundle_between_attempts_stops_without_another_process(self):
        self.install()
        def edit(_):
            (self.target/"Contents/binary").write_bytes(b"user edit")
        self.sleep.side_effect=edit
        with self.assertRaisesRegex(RuntimeError,"changed during validation"):
            self.validate_fixture([(0,self.text("0.3.0"))])
        self.assertEqual(len(self.commands),2);self.assertEqual((self.target/"Contents/binary").read_bytes(),b"user edit")

    def test_validation_holds_exclusive_installer_lock_across_retry_wait(self):
        self.install()
        def check(_):
            with (self.state/"au-install.lock").open("a") as lock:
                with self.assertRaises(BlockingIOError):au.fcntl.flock(lock,au.fcntl.LOCK_SH|au.fcntl.LOCK_NB)
        self.sleep.side_effect=check;self.validate_fixture([(0,self.text("0.3.0")),(0,self.text("0.5.0"))])
        with (self.state/"au-install.lock").open("a") as lock:au.fcntl.flock(lock,au.fcntl.LOCK_EX|au.fcntl.LOCK_NB)

    def test_edited_owned_component_never_refreshed(self):
        self.install();(self.target/"Contents/binary").write_bytes(b"user edit")
        with patch.object(au.os,"utime") as touch,patch.object(au.subprocess,"run") as process,self.assertRaisesRegex(ValueError,"edited"):
            au.validate(self.components,self.state,self.output,self.result)
        touch.assert_not_called();process.assert_not_called()

    def test_missing_ownership_ledger_never_refreshes_component(self):
        self.install();self.ledger.unlink()
        with patch.object(au.os,"utime") as touch,patch.object(au.subprocess,"run") as process,self.assertRaisesRegex(ValueError,"ownership ledger"):
            au.validate(self.components,self.state,self.output,self.result)
        touch.assert_not_called();process.assert_not_called()

    def test_symlinked_component_never_refreshed(self):
        self.install();retained=self.root/"retained.component";self.target.rename(retained)
        self.target.symlink_to(retained,target_is_directory=True)
        with patch.object(au.os,"utime") as touch,patch.object(au.subprocess,"run") as process,self.assertRaisesRegex(ValueError,"symlink"):
            au.validate(self.components,self.state,self.output,self.result)
        touch.assert_not_called();process.assert_not_called()

    def test_cli_records_final_failure_and_retry_history(self):
        self.install()
        def process(command,**kwargs):
            if command[0]!="codesign":kwargs["stdout"].write(self.text("0.3.0"))
            return subprocess.CompletedProcess(command,0)
        validate=au.validate
        def quick(*args):return validate(*args,retry_delays=(0,),sleeper=lambda _:None)
        with patch.object(sys,"argv",["au.py","validate"]),patch.object(au,"ROOT",self.root), \
             patch.object(au,"DEFAULT_INSTALL",self.components),patch.object(au,"DEFAULT_STATE",self.state), \
             patch.object(au,"validate",side_effect=quick),patch.object(au.subprocess,"run",side_effect=process), \
             contextlib.redirect_stdout(io.StringIO()),self.assertRaises(au.RegistryVersionMismatch):au.main()
        paths=list((self.root/"build/au-checks").glob("*/result.json"));self.assertEqual(len(paths),1)
        report=json.loads(paths[0].read_text());self.assertEqual(report["status"],"fail")
        self.assertEqual(len(report["validation_attempts"]),2)
