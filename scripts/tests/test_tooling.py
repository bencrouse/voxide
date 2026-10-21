import importlib.util
import hashlib
import contextlib
import io
from pathlib import Path
import plistlib
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("voxide_au", ROOT / "scripts/au.py")
au = importlib.util.module_from_spec(spec)
spec.loader.exec_module(au)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="voxide-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "build/voxide.component"
        contents = self.source / "Contents"
        contents.mkdir(parents=True)
        (contents / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleIdentifier": au.BUNDLE_ID, "CFBundleShortVersionString": "0.0.1",
            "AudioComponents": [au.IDENTITY],
        }))
        (contents / "binary").write_bytes(b"test executable")
        self.destination = self.root / "Components"
        self.state = self.root / "state"

    def install(self, signer=lambda _: None):
        return au.install(self.source, self.destination, self.state, signer)

    def test_auval_requires_matching_identity_version_and_success(self):
        output = "VALIDATING AUDIO UNIT: 'aumf' - 'Vx00' - 'Vxid'\nComponent Version: 0.1.0 (0x100)\nAU VALIDATION SUCCEEDED.\n"
        au.verify_validation_output(output, "0.1.0")
        with self.assertRaisesRegex(ValueError, "registry version"):
            au.verify_validation_output(output, "0.0.1")
        with self.assertRaises(ValueError):
            au.verify_validation_output(output.replace("Vxid", "NTRD"), "0.1.0")
        with self.assertRaises(ValueError):
            au.verify_validation_output(output.replace("AU VALIDATION SUCCEEDED.", "FAILED"), "0.1.0")

    def test_install_and_owned_replacement_preserve_other_plugins(self):
        unrelated = self.destination / "nitride.component/user-data"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("untouched")
        first = self.install()
        target = self.destination / au.COMPONENT
        self.assertEqual(first["files"], au.fingerprint(target))
        second = self.install()
        self.assertEqual(au.fingerprint(Path(second["backup"])), first["files"])
        self.assertFalse(Path(second["backup"]).is_relative_to(self.destination))
        self.assertEqual(unrelated.read_text(), "untouched")

    def test_unknown_existing_component_is_refused(self):
        target = self.destination / au.COMPONENT
        target.mkdir(parents=True)
        (target / "user-file").write_text("preserve")
        with self.assertRaisesRegex(ValueError, "ownership ledger"):
            self.install()
        self.assertEqual((target / "user-file").read_text(), "preserve")

    def test_edited_component_is_refused(self):
        self.install()
        edited = self.destination / au.COMPONENT / "Contents/binary"
        edited.write_bytes(b"user changed this")
        with self.assertRaisesRegex(ValueError, "edited"):
            self.install()
        self.assertEqual(edited.read_bytes(), b"user changed this")

    def test_symlink_destination_is_refused(self):
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        self.destination.symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.install()
        self.assertFalse(list(elsewhere.iterdir()))

    def test_symlink_component_is_refused(self):
        self.destination.mkdir()
        (self.destination / au.COMPONENT).symlink_to(self.source)
        with self.assertRaises(ValueError):
            self.install()

    def test_wrong_identity_is_refused(self):
        (self.source / "Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "nitride"}))
        with self.assertRaisesRegex(ValueError, "Not a Voxide"):
            self.install()
        self.assertFalse(self.destination.exists())

    def test_sign_failure_preserves_existing_install(self):
        self.install()
        original = au.fingerprint(self.destination / au.COMPONENT)
        ledger = (self.state / "au-install.json").read_bytes()

        def fail(_):
            raise RuntimeError("deliberate sign failure")

        with self.assertRaises(RuntimeError):
            self.install(signer=fail)
        self.assertEqual(au.fingerprint(self.destination / au.COMPONENT), original)
        self.assertEqual((self.state / "au-install.json").read_bytes(), ledger)

    def test_ledger_failure_rolls_back_install(self):
        self.install()
        original = au.fingerprint(self.destination / au.COMPONENT)
        ledger = (self.state / "au-install.json").read_bytes()
        (self.source / "Contents/binary").write_bytes(b"new build")
        with mock.patch.object(au.os, "replace", side_effect=OSError("ledger failed")):
            with self.assertRaises(OSError):
                self.install()
        self.assertEqual(au.fingerprint(self.destination / au.COMPONENT), original)
        self.assertEqual((self.state / "au-install.json").read_bytes(), ledger)

    def test_unknown_target_created_during_signing_is_refused(self):
        target = self.destination / au.COMPONENT

        def newcomer(_):
            shutil.copytree(self.source, target)
            (target / "Contents/binary").write_bytes(b"unowned newcomer")

        with self.assertRaisesRegex(ValueError, "ownership ledger"):
            self.install(signer=newcomer)
        self.assertEqual((target / "Contents/binary").read_bytes(), b"unowned newcomer")
        self.assertFalse((self.state / "au-install.json").exists())

    def test_owned_target_edited_during_signing_is_refused(self):
        self.install()
        target = self.destination / au.COMPONENT
        ledger = (self.state / "au-install.json").read_bytes()

        def edit(_):
            (target / "Contents/binary").write_bytes(b"concurrent user edit")

        with self.assertRaisesRegex(ValueError, "edited"):
            self.install(signer=edit)
        self.assertEqual((target / "Contents/binary").read_bytes(), b"concurrent user edit")
        self.assertEqual((self.state / "au-install.json").read_bytes(), ledger)

    def test_no_clobber_rename_refuses_even_an_empty_target(self):
        source, target = self.root / "original", self.root / "newcomer"
        source.mkdir()
        target.mkdir()
        (source / "user-file").write_text("preserve")
        with self.assertRaises(FileExistsError):
            au.rename_exclusive(source, target)
        self.assertEqual((source / "user-file").read_text(), "preserve")
        self.assertEqual(list(target.iterdir()), [])

    def test_late_collision_preserves_newcomer_and_original_backup(self):
        self.install()
        target = self.destination / au.COMPONENT
        original = au.fingerprint(target)
        rename = au.rename_exclusive

        def collide(source, destination):
            if destination == target and source.name == au.COMPONENT:
                target.mkdir()
                (target / "user-file").write_text("late newcomer")
            rename(source, destination)

        with mock.patch.object(au, "rename_exclusive", side_effect=collide):
            with self.assertRaisesRegex(RuntimeError, "previous bundle is preserved"):
                self.install()
        self.assertEqual((target / "user-file").read_text(), "late newcomer")
        backups = list((self.state / "backups").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual(au.fingerprint(backups[0]), original)

    def test_cleanup_failure_does_not_prevent_rollback(self):
        self.install()
        original = au.fingerprint(self.destination / au.COMPONENT)
        (self.source / "Contents/binary").write_bytes(b"new build")
        unlink = Path.unlink

        def fail_pending(path, *args, **kwargs):
            if path.name.startswith("au-install-"):
                raise PermissionError("deliberate cleanup failure")
            return unlink(path, *args, **kwargs)

        with mock.patch.object(au.os, "replace", side_effect=OSError("ledger failed")), \
                mock.patch.object(Path, "unlink", new=fail_pending), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(OSError, "ledger failed"):
                self.install()
        self.assertEqual(au.fingerprint(self.destination / au.COMPONENT), original)

    def test_replacement_during_rollback_is_retained_not_deleted(self):
        self.install()
        target = self.destination / au.COMPONENT
        original = au.fingerprint(target)
        ledger = (self.state / "au-install.json").read_bytes()
        (self.source / "Contents/binary").write_bytes(b"candidate build")
        rename = au.rename_exclusive

        def replace_just_before_rollback(source, destination):
            if source == target and destination.parent.name.startswith("au-stage-"):
                # Replace only this test's known published candidate in its fake root.
                shutil.rmtree(target)
                target.mkdir()
                (target / "unowned-user-data").write_text("must survive cleanup")
            rename(source, destination)

        with mock.patch.object(au.os, "replace", side_effect=OSError("ledger failed")), \
                mock.patch.object(au, "rename_exclusive", side_effect=replace_just_before_rollback), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "unverified entry retained"):
                self.install()
        retained = list(self.state.glob("au-stage-*/voxide.component/unowned-user-data"))
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0].read_text(), "must survive cleanup")
        backups = list((self.state / "backups").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual(au.fingerprint(backups[0]), original)
        self.assertEqual((self.state / "au-install.json").read_bytes(), ledger)


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="voxide-dependency-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def cmake(self, body):
        driver = self.root / "verify.cmake"
        driver.write_text('include("' + str(ROOT / "cmake/VerifyDependency.cmake") + '")\n' + body)
        return subprocess.run(["cmake", "-P", str(driver)], text=True, capture_output=True)

    def git(self, *arguments):
        return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null",
                                        "-C", str(self.root), *arguments], text=True).strip()

    def test_bad_archive_checksum(self):
        archive = self.root / "bad.tar.gz"
        archive.write_bytes(b"not the pinned archive")
        result = self.cmake(f'voxide_verify_archive("{archive}")\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum mismatch", result.stderr)

    def test_archive_verifier_positive_control(self):
        archive = self.root / "fixture.tar.gz"
        archive.write_bytes(b"known fixture, not the real dependency")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        result = self.cmake(f'set(VOXIDE_JUCE_SHA256 "{digest}")\n'
                            f'voxide_verify_archive("{archive}")\n')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_offline_cache_fails_before_download(self):
        driver = self.root / "offline.cmake"
        driver.write_text(f'set(PROJECT_SOURCE_DIR "{self.root}")\n'
                          f'set(PROJECT_BINARY_DIR "{self.root}/build")\n'
                          'set(VOXIDE_OFFLINE ON CACHE BOOL "" FORCE)\n'
                          f'include("{ROOT}/cmake/JuceDependency.cmake")\n')
        result = subprocess.run(["cmake", "-P", str(driver)], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Offline JUCE archive missing", result.stderr)
        self.assertFalse((self.root / ".cache").exists())

    def test_checkout_pin_and_dirty_rejection(self):
        self.git("init", "--quiet")
        (self.root / "CMakeLists.txt").write_text("# synthetic checkout\n")
        nested = self.root / "nested"
        nested.mkdir()
        (nested / "CMakeLists.txt").write_text("# not the checkout root\n")
        self.git("add", "CMakeLists.txt", "nested/CMakeLists.txt")
        self.git("-c", "user.name=Voxide Tests", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "fixture")
        revision = self.git("rev-parse", "HEAD")
        # Isolate wrong-revision rejection from the dirty-checkout cases below.
        (self.root / ".git/info/exclude").write_text("verify.cmake\n")
        result = self.cmake(f'voxide_verify_checkout("{self.root}")\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("clean pinned checkout", result.stderr)
        # Match this synthetic repository only inside the test driver. Never alter
        # the real pin or depend on a developer's downloaded JUCE checkout.
        body = f'set(VOXIDE_JUCE_REVISION "{revision}")\nvoxide_verify_checkout("{self.root}")\n'
        self.assertEqual(self.cmake(body).returncode, 0)
        self.assertNotEqual(self.cmake(f'set(VOXIDE_JUCE_REVISION "{revision}")\n'
                                      f'voxide_verify_checkout("{nested}")\n').returncode, 0)
        (self.root / "CMakeLists.txt").write_text("# dirty\n")
        self.assertNotEqual(self.cmake(body).returncode, 0)
        self.git("add", "CMakeLists.txt")
        self.assertNotEqual(self.cmake(body).returncode, 0)
        self.git("-c", "user.name=Voxide Tests", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "changed fixture")
        revision = self.git("rev-parse", "HEAD")
        (self.root / "untracked.txt").write_text("untracked")
        self.assertNotEqual(self.cmake(f'set(VOXIDE_JUCE_REVISION "{revision}")\n'
                                      f'voxide_verify_checkout("{self.root}")\n').returncode, 0)

    def fixture_archive(self):
        source = self.root / "input/JUCE-fixture"
        source.mkdir(parents=True)
        (source / "CMakeLists.txt").write_text("# verified fixture\n")
        (source / ".hidden").write_text("hidden content also protected\n")
        archive = self.root / "juce-fixture.tar.gz"
        with tarfile.open(archive, "w:gz") as package:
            package.add(source, arcname="JUCE-fixture")
        return archive

    def prepare(self, archive, dependencies):
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        return self.cmake(f'include("{ROOT}/cmake/PrepareJuce.cmake")\n'
                          'set(VOXIDE_JUCE_REVISION "fixture")\n'
                          f'set(VOXIDE_JUCE_SHA256 "{digest}")\n'
                          f'voxide_prepare_juce("{archive}" "{dependencies}" source)\n')

    def test_extracted_source_edits_additions_and_symlinks_are_rejected(self):
        archive = self.fixture_archive()
        for change in ("edit", "add", "hidden", "symlink"):
            with self.subTest(change=change):
                dependencies = self.root / change
                first = self.prepare(archive, dependencies)
                self.assertEqual(first.returncode, 0, first.stderr)
                self.assertEqual(self.prepare(archive, dependencies).returncode, 0)
                source = dependencies / "JUCE-fixture"
                if change == "symlink":
                    (source / "link").symlink_to(source / "CMakeLists.txt")
                else:
                    name = {"edit": "CMakeLists.txt", "add": "extra.cpp", "hidden": ".hidden"}[change]
                    (source / name).write_text("user edit must not be overwritten\n")
                result = self.prepare(archive, dependencies)
                self.assertNotEqual(result.returncode, 0)
                if change == "symlink":
                    self.assertTrue((source / "link").is_symlink())
                else:
                    self.assertEqual((source / name).read_text(), "user edit must not be overwritten\n")

    def test_unverified_old_source_is_adopted_only_if_pristine(self):
        archive = self.fixture_archive()
        dependencies = self.root / "old-build"
        source = dependencies / "JUCE-fixture"
        source.mkdir(parents=True)
        (source / "CMakeLists.txt").write_text("user edit\n")
        result = self.prepare(archive, dependencies)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("extracted source mismatch", result.stderr)
        self.assertEqual((source / "CMakeLists.txt").read_text(), "user edit\n")


if __name__ == "__main__":
    unittest.main()
