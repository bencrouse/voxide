from pathlib import Path
import json
import struct
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import host_integration as host


class HostIntegrationTests(unittest.TestCase):
    def fixture(self,root):
        root=root.resolve()
        build=root/"build";build.mkdir();(build/"CMakeCache.txt").write_text("CMAKE_BUILD_TYPE:STRING=Release\nVOXIDE_SANITIZER:STRING=\n")
        binary=build/"voxide_host_integration_tests_artefacts/Release/voxide_host_integration_tests";binary.parent.mkdir(parents=True);binary.write_bytes(b"test-only executable")
        return build

    def runner(self,fault=None):
        calls=[]
        def run(command,**_):
            calls.append(command)
            report=Path(command[command.index("--report")+1]);label=report.stem
            if "--save-state" in command:Path(command[command.index("--save-state")+1]).write_bytes(b"synthetic AU state")
            if "--audio" in command:
                payload=struct.pack("<f",.02)*76800
                if fault=="nonfinite":payload=struct.pack("<f",float("nan"))*76800
                if fault=="duration":payload=payload[:-4]
                if fault=="different" and label=="reopen-process":payload=struct.pack("<f",.03)*76800
                Path(command[command.index("--audio")+1]).write_bytes(payload)
            value={"schema":"voxide.pr08-native-host.v1","status":"pass","pid":123 if fault=="same-pid" else 123+len(calls),
                "cases":14 if label=="exact-au" else 1,"exact_reference":True,"latency_notifications":True,"installed_registry_or_Logic_test":False}
            if fault=="scope":value["installed_registry_or_Logic_test"]=True
            if fault=="old-report":value["schema"]="voxide.native-au.v2"
            if fault=="cases":value["cases"]=0
            report.write_text(json.dumps(value))
        return run,calls

    def native(self,root,fault=None):
        root=root.resolve();build=self.fixture(root);directory=root/"run";directory.mkdir();report={};run,calls=self.runner(fault)
        with patch.object(host.au,"fingerprint",return_value={"fixture":"only"}),patch.object(host.subprocess,"run",side_effect=run):
            host.run_native(build,root/"fake.component",directory,report)
        return report,calls

    def test_fresh_process_audio_and_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            report,calls=self.native(Path(temp))
            self.assertEqual(len(calls),3);self.assertTrue(report["fresh_process_recall"]["exact"])
            self.assertEqual(report["fresh_process_recall"]["frames"],76800)
            self.assertNotEqual(*report["fresh_process_recall"]["pids"])

    def test_wrong_or_overclaimed_native_report_rejected(self):
        for fault in ("scope","old-report","cases"):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp,self.assertRaises(ValueError):self.native(Path(temp),fault)

    def test_nonfresh_different_nonfinite_or_short_recall_rejected(self):
        for fault in ("same-pid","different","nonfinite","duration"):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp,self.assertRaises(ValueError):self.native(Path(temp),fault)

    def test_installed_requires_both_approvals_before_any_access(self):
        for installed,auval in ((False,False),(True,False),(False,True)):
            with patch.object(host,"native_binary") as binary,patch.object(host.au,"no_symlinks") as access,self.assertRaisesRegex(ValueError,"approvals"):
                host.check(Path("not-accessed"),installed=True,allow_installed=installed,allow_auval=auval)
            binary.assert_not_called();access.assert_not_called()

    def test_sanitized_native_execution_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            build=self.fixture(Path(temp));(build/"CMakeCache.txt").write_text("CMAKE_BUILD_TYPE:STRING=Debug\nVOXIDE_SANITIZER:STRING=thread\n")
            with self.assertRaisesRegex(ValueError,"sanitizer"):host.native_binary(build)

    def test_symlinked_native_executable_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();build=self.fixture(root);binary,_=host.native_binary(build)
            other=root/"not-the-built-helper";binary.rename(other);binary.symlink_to(other)
            with self.assertRaisesRegex(ValueError,"symlink"):host.native_binary(build)

    def test_boolean_claims_must_be_boolean(self):
        value={"schema":"voxide.pr08-native-host.v1","status":"pass","pid":123,"cases":14,
               "exact_reference":1,"latency_notifications":True,"installed_registry_or_Logic_test":False}
        with self.assertRaises(ValueError):host.validate_native(value,14)

    def test_kit_is_synthetic_pending_append_only_and_inside_evaluation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();(root/"docs").mkdir();(root/"docs/PR08_LOGIC_CHECKLIST.md").write_text("Fixture checklist, not host evidence")
            directory=root/"evaluation/pr-08/kit"
            with patch.object(host,"ROOT",root):host.kit(directory)
            worksheet=host.load_json(directory/"worksheet.json")
            self.assertEqual(worksheet["status"],"pending_user_session")
            self.assertTrue(all(row["status"]=="pending" for row in worksheet["cases"].values()))
            self.assertIsNone(worksheet["private_recording_selected"])
            self.assertEqual(len(worksheet["files_sha256"]),4)
            with patch.object(host,"ROOT",root),self.assertRaises(FileExistsError):host.kit(directory)
            with patch.object(host,"ROOT",root),self.assertRaisesRegex(ValueError,"ignored"):host.kit(root/"outside")

    def test_failed_native_check_keeps_report_and_never_claims_Logic_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();build=self.fixture(root);output=root/"run"
            with patch.object(host.au,"check_identity",return_value="0.3.0"),patch.object(host,"verify_linkage"), \
                 patch.object(host,"run_native",side_effect=RuntimeError("native failed")),self.assertRaises(RuntimeError):
                host.check(build,output)
            report=host.load_json(output/"report.json")
            self.assertEqual(report["status"],"fail");self.assertEqual(report["host_acceptance"],"pending_user_session")
            self.assertFalse(report["Logic_operated"])

    def test_default_kit_refuses_symlink_evidence_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();(root/"outside").mkdir();(root/"evaluation").symlink_to(root/"outside",target_is_directory=True)
            with patch.object(host,"ROOT",root),self.assertRaisesRegex(ValueError,"symlink"):host.kit()
            self.assertEqual(list((root/"outside").iterdir()),[])

    def test_failed_approved_auval_attempt_is_recorded_not_hidden(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();build=self.fixture(root);output=root/"evaluation/pr-08/run"
            with patch.object(host,"ROOT",root),patch.object(host.au,"check_identity",return_value="0.3.0"), \
                 patch.object(host,"verify_linkage"),patch.object(host.au,"owned_component",return_value={"files":{},"version":"0.3.0"}), \
                 patch.object(host.au,"fingerprint",return_value={}),patch.object(host,"run_native") as native, \
                 patch.object(host.subprocess,"run",side_effect=host.subprocess.CalledProcessError(1,["mock-auval"])) as run, \
                 self.assertRaises(host.subprocess.CalledProcessError):
                host.check(build,output,installed=True,allow_installed=True,allow_auval=True)
            run.assert_called_once();native.assert_not_called()
            report=host.load_json(output/"report.json")
            self.assertEqual(report["status"],"fail");self.assertTrue(report["installed_auval_executed"])
            self.assertFalse(report["Logic_operated"])
