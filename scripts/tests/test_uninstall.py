from pathlib import Path
import contextlib
import io
import json
import plistlib
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import au


class UninstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="voxide-uninstall-tests-");self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.source=self.root/"build/voxide.component";self.destination=self.root/"Components";self.state=self.root/"state"
        (self.source/"Contents/MacOS").mkdir(parents=True)
        (self.source/"Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier":au.BUNDLE_ID,"CFBundleShortVersionString":"0.4.0","AudioComponents":[au.IDENTITY]}))
        (self.source/"Contents/MacOS/voxide").write_bytes(b"synthetic test executable")
        self.target=self.destination/au.COMPONENT;self.ledger=self.state/"au-install.json"

    def install(self):return au.install(self.source,self.destination,self.state,signer=lambda _:None)
    def remove(self):return au.uninstall(self.destination,self.state,allow=True)
    def failures(self):return list((self.state/"uninstalled").glob("*/failure.json"))

    def test_consent_precedes_all_path_access(self):
        with patch.object(au,"no_symlinks") as access,self.assertRaisesRegex(ValueError,"allow-uninstall"):
            au.uninstall(Path("not-accessed"),Path("not-accessed"))
        access.assert_not_called()

    def test_owned_uninstall_retains_bundle_receipt_backups_and_other_plugins(self):
        self.install();self.install();expected=au.fingerprint(self.target);ledger=self.ledger.read_bytes()
        neighbors=[self.destination/"nitride.component/user-data",self.destination/"voxide Studio Eval.component/user-data"]
        for path in neighbors:path.parent.mkdir(parents=True);path.write_text("must survive")
        backups={str(p):au.fingerprint(p) for p in (self.state/"backups").iterdir()}
        with patch.object(au.shutil,"rmtree") as delete:result=self.remove()
        delete.assert_not_called();self.assertEqual(result["status"],"uninstalled_recoverable")
        self.assertFalse(self.target.exists());self.assertFalse(self.ledger.exists())
        self.assertEqual(au.fingerprint(Path(result["retained_component"])),expected)
        self.assertEqual(Path(result["retained_ledger"]).read_bytes(),ledger)
        self.assertFalse(Path(result["retained_component"]).is_relative_to(self.destination))
        for name,value in backups.items():self.assertEqual(au.fingerprint(Path(name)),value)
        for path in neighbors:self.assertEqual(path.read_text(),"must survive")

    def test_unknown_and_edited_component_refused_without_quarantine(self):
        self.target.mkdir(parents=True);self.state.mkdir();(self.target/"user-data").write_text("unknown")
        with self.assertRaisesRegex(ValueError,"ownership ledger"):self.remove()
        self.assertEqual((self.target/"user-data").read_text(),"unknown")
        self.assertFalse((self.state/"uninstalled").exists())

    def test_edited_owned_component_is_preserved(self):
        self.install();ledger=self.ledger.read_bytes();edited=self.target/"Contents/MacOS/voxide";edited.write_bytes(b"user edit")
        with self.assertRaisesRegex(ValueError,"edited"):self.remove()
        self.assertEqual(edited.read_bytes(),b"user edit");self.assertEqual(self.ledger.read_bytes(),ledger)
        self.assertFalse((self.state/"uninstalled").exists())

    def test_symlink_target_and_ledger_refused(self):
        self.install();moved=self.root/"owned-away";self.target.rename(moved);self.target.symlink_to(moved,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,"symlink"):self.remove()
        self.target.unlink();moved.rename(self.target)
        ledger_copy=self.root/"ledger-copy";self.ledger.rename(ledger_copy);self.ledger.symlink_to(ledger_copy)
        with self.assertRaisesRegex(ValueError,"symlink"):self.remove()
        self.assertTrue(self.target.is_dir());self.assertTrue(ledger_copy.exists())

    def test_symlink_retention_root_refused(self):
        self.install();elsewhere=self.root/"elsewhere";elsewhere.mkdir();(self.state/"uninstalled").symlink_to(elsewhere,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,"symlink"):self.remove()
        self.assertTrue(self.target.exists());self.assertTrue(self.ledger.exists());self.assertEqual(list(elsewhere.iterdir()),[])

    def test_missing_target_preserves_stale_ledger(self):
        self.install();ledger=self.ledger.read_bytes();self.target.rename(self.root/"removed-by-user")
        with self.assertRaisesRegex(ValueError,"No installed"):self.remove()
        self.assertEqual(self.ledger.read_bytes(),ledger);self.assertFalse((self.state/"uninstalled").exists())

    def test_overlapping_state_and_discovery_paths_refused(self):
        with self.assertRaisesRegex(ValueError,"disjoint"):au.uninstall(self.destination,self.destination/"state",allow=True)
        self.assertFalse(self.destination.exists())

    def test_receipt_move_failure_rolls_back_known_original(self):
        self.install();expected=au.fingerprint(self.target);ledger=self.ledger.read_bytes();rename=au.rename_exclusive
        def fail(source,destination):
            if source==self.ledger:raise OSError("receipt move failed")
            rename(source,destination)
        with patch.object(au,"rename_exclusive",side_effect=fail),self.assertRaisesRegex(OSError,"receipt move failed"):self.remove()
        self.assertEqual(au.fingerprint(self.target),expected);self.assertEqual(self.ledger.read_bytes(),ledger)
        self.assertEqual(json.loads(self.failures()[0].read_text())["status"],"failed_rolled_back")

    def test_result_write_failure_rolls_back_both_entries(self):
        self.install();expected=au.fingerprint(self.target);ledger=self.ledger.read_bytes();write=au.write_exclusive_json
        def fail(path,value):
            if path.name=="result.json":raise OSError("result write failed")
            write(path,value)
        with patch.object(au,"write_exclusive_json",side_effect=fail),self.assertRaisesRegex(OSError,"result write failed"):self.remove()
        self.assertEqual(au.fingerprint(self.target),expected);self.assertEqual(self.ledger.read_bytes(),ledger)
        self.assertEqual(json.loads(self.failures()[0].read_text())["status"],"failed_rolled_back")

    def test_interrupt_immediately_after_either_rename_rolls_back(self):
        for interrupted_source in (self.target,self.ledger):
            with self.subTest(source=str(interrupted_source)):
                self.install();expected=au.fingerprint(self.target);ledger=self.ledger.read_bytes()
                previous=set(self.failures());rename=au.rename_exclusive
                def interrupt(source,destination):
                    rename(source,destination)
                    if source==interrupted_source:raise KeyboardInterrupt()
                with patch.object(au,"rename_exclusive",side_effect=interrupt),self.assertRaises(KeyboardInterrupt):self.remove()
                self.assertEqual(au.fingerprint(self.target),expected);self.assertEqual(self.ledger.read_bytes(),ledger)
                receipt=json.loads((set(self.failures())-previous).pop().read_text())
                self.assertEqual(receipt["status"],"failed_rolled_back");self.assertEqual(receipt["error_type"],"KeyboardInterrupt")

    def test_interrupt_during_result_write_rolls_back_and_failure_takes_precedence(self):
        for complete in (False,True):
            with self.subTest(complete=complete):
                self.install();expected=au.fingerprint(self.target);ledger=self.ledger.read_bytes()
                previous=set(self.failures());write=au.write_exclusive_json
                def interrupt(path,value):
                    if path.name=="result.json":
                        if complete:write(path,value)
                        else:path.write_text('{"status":')
                        raise KeyboardInterrupt()
                    write(path,value)
                with patch.object(au,"write_exclusive_json",side_effect=interrupt),self.assertRaises(KeyboardInterrupt):self.remove()
                self.assertEqual(au.fingerprint(self.target),expected);self.assertEqual(self.ledger.read_bytes(),ledger)
                failure=(set(self.failures())-previous).pop()
                self.assertEqual(json.loads(failure.read_text())["status"],"failed_rolled_back")
                self.assertTrue((failure.parent/"result.json").exists())

    def test_second_interrupt_during_rollback_records_manual_recovery(self):
        self.install();expected=au.fingerprint(self.target);ledger=self.ledger.read_bytes();rename=au.rename_exclusive
        original=KeyboardInterrupt("initial")
        def interrupt(source,destination):
            if source==self.ledger:raise original
            if source.name==au.COMPONENT and source!=self.target:raise KeyboardInterrupt("rollback")
            rename(source,destination)
        stderr=io.StringIO()
        with patch.object(au,"rename_exclusive",side_effect=interrupt),contextlib.redirect_stderr(stderr),self.assertRaises(KeyboardInterrupt) as raised:
            self.remove()
        self.assertIs(raised.exception,original);self.assertIn("manual recovery",stderr.getvalue())
        receipt=json.loads(self.failures()[0].read_text())
        self.assertEqual(receipt["status"],"failed_manual_recovery");self.assertEqual(receipt["rollback_errors"],["rollback"])
        self.assertFalse(self.target.exists());self.assertEqual(self.ledger.read_bytes(),ledger)
        self.assertEqual(au.fingerprint(Path(receipt["retained_component"])),expected)

    def test_interrupted_collision_preserves_newcomer_and_quarantined_original(self):
        self.install();expected=au.fingerprint(self.target);rename=au.rename_exclusive
        def interrupt(source,destination):
            rename(source,destination)
            if source==self.target:
                self.target.mkdir();(self.target/"user-data").write_text("newcomer");raise KeyboardInterrupt()
        with patch.object(au,"rename_exclusive",side_effect=interrupt),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(KeyboardInterrupt):self.remove()
        receipt=json.loads(self.failures()[0].read_text())
        self.assertEqual(receipt["status"],"failed_manual_recovery")
        self.assertEqual((self.target/"user-data").read_text(),"newcomer")
        self.assertEqual(au.fingerprint(Path(receipt["retained_component"])),expected)

    def test_cli_interruption_records_failure_and_reraises(self):
        self.install();rename=au.rename_exclusive
        def interrupt(source,destination):
            rename(source,destination)
            if source==self.target:raise KeyboardInterrupt()
        with patch.object(sys,"argv",["au.py","uninstall","--allow-uninstall"]), \
             patch.object(au,"ROOT",self.root),patch.object(au,"DEFAULT_INSTALL",self.destination),patch.object(au,"DEFAULT_STATE",self.state), \
             patch.object(au,"rename_exclusive",side_effect=interrupt),contextlib.redirect_stdout(io.StringIO()),self.assertRaises(KeyboardInterrupt):au.main()
        reports=list((self.root/"build/au-checks").glob("*/result.json"));self.assertEqual(len(reports),1)
        result=json.loads(reports[0].read_text())
        self.assertEqual(result["status"],"fail");self.assertEqual(result["error_type"],"KeyboardInterrupt")
        self.assertTrue(self.target.exists());self.assertTrue(self.ledger.exists())

    def test_edit_during_move_is_retained_not_deleted_or_restored(self):
        self.install();rename=au.rename_exclusive
        def edit(source,destination):
            if source==self.target:(source/"Contents/MacOS/voxide").write_bytes(b"late user edit")
            rename(source,destination)
        with patch.object(au,"rename_exclusive",side_effect=edit),self.assertRaisesRegex(RuntimeError,"manual recovery"):self.remove()
        retained=list((self.state/"uninstalled").glob("*/voxide.component/Contents/MacOS/voxide"))
        self.assertEqual(len(retained),1);self.assertEqual(retained[0].read_bytes(),b"late user edit")
        self.assertTrue(self.ledger.exists());self.assertFalse(self.target.exists())

    def test_late_newcomer_is_not_overwritten_by_rollback(self):
        self.install();expected=au.fingerprint(self.target);rename=au.rename_exclusive
        def collide(source,destination):
            if source==self.ledger:
                self.target.mkdir();(self.target/"user-data").write_text("newcomer");raise OSError("late collision")
            rename(source,destination)
        with patch.object(au,"rename_exclusive",side_effect=collide),self.assertRaisesRegex(RuntimeError,"manual recovery"):self.remove()
        self.assertEqual((self.target/"user-data").read_text(),"newcomer")
        retained=list((self.state/"uninstalled").glob("*/voxide.component"));self.assertEqual(au.fingerprint(retained[0]),expected)

    def test_changed_receipt_is_retained_without_uncertain_rollback(self):
        self.install();rename=au.rename_exclusive
        def replace(source,destination):
            if source==self.ledger:source.write_bytes(b"unknown user receipt")
            rename(source,destination)
        with patch.object(au,"rename_exclusive",side_effect=replace),self.assertRaisesRegex(RuntimeError,"manual recovery"):self.remove()
        retained=list((self.state/"uninstalled").glob("*/au-install.json"))
        self.assertEqual(retained[0].read_bytes(),b"unknown user receipt");self.assertFalse(self.target.exists())
        self.assertTrue(list((self.state/"uninstalled").glob("*/voxide.component")))

    def test_shared_and_exclusive_installer_lock_are_held_then_released(self):
        self.install();rename=au.rename_exclusive
        def check(source,destination):
            with (self.state/"au-install.lock").open("a") as stream:
                for mode in (au.fcntl.LOCK_SH,au.fcntl.LOCK_EX):
                    with self.assertRaises(BlockingIOError):au.fcntl.flock(stream,mode|au.fcntl.LOCK_NB)
            rename(source,destination)
        with patch.object(au,"rename_exclusive",side_effect=check):self.remove()
        with (self.state/"au-install.lock").open("a") as stream:au.fcntl.flock(stream,au.fcntl.LOCK_EX|au.fcntl.LOCK_NB)

    def test_cli_requires_explicit_uninstall_flag_before_any_path_access(self):
        with patch.object(sys,"argv",["au.py","uninstall"]),patch.object(au,"no_symlinks") as access, \
             patch.object(Path,"mkdir") as mkdir,contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):au.main()
        access.assert_not_called();mkdir.assert_not_called()

    def test_recovery_reinstall_keeps_quarantined_source(self):
        self.install();result=self.remove();retained=Path(result["retained_component"]);expected=au.fingerprint(retained)
        au.install(retained,self.destination,self.state,signer=lambda _:None)
        self.assertEqual(au.fingerprint(self.target),expected);self.assertEqual(au.fingerprint(retained),expected)

    def test_cli_exact_component_install_selects_supplied_path(self):
        with patch.object(sys,"argv",["au.py","install","--component",str(self.source)]),patch.object(au,"ROOT",self.root), \
             patch.object(au,"install",return_value={"installed":"fixture"}) as install,contextlib.redirect_stdout(io.StringIO()):au.main()
        self.assertEqual(install.call_args.args[0],self.source)
