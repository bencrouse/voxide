#!/usr/bin/env python3
"""Explicit, local-only Voxide AU installation and validation; never terminate a DAW."""
import argparse
import ctypes
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = "voxide.component"
BUNDLE_ID = "com.voxide.audio.voxide"
IDENTITY = {"type": "aumf", "subtype": "Vx00", "manufacturer": "Vxid"}
DEFAULT_INSTALL = Path.home() / "Library/Audio/Plug-Ins/Components"
DEFAULT_STATE = Path.home() / ".local/state/voxide"


def no_symlinks(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError("Refusing symlink path: " + str(item))
    return Path(os.path.abspath(path))


def present(path):
    return path.exists() or path.is_symlink()


def entry_identity(path):
    stat = path.lstat()
    return stat.st_dev, stat.st_ino


def rename_exclusive(source, destination):
    # Darwin sys/stdio.h: RENAME_EXCL = 0x00000004 (macOS 10.12+).
    # Unlike Path.rename(), this cannot overwrite even an empty directory or link
    # that another process creates after our last ownership check.
    rename = ctypes.CDLL(None, use_errno=True).renamex_np
    rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(os.fsencode(source), os.fsencode(destination), 0x00000004) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))


class InstallStage:
    """Only discard positively owned staging content, never an uncertain moved entry."""

    def __init__(self, parent):
        self.path = Path(tempfile.mkdtemp(prefix="au-stage-", dir=parent))
        self.safe_to_remove = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        if self.safe_to_remove:
            shutil.rmtree(self.path)
        else:
            print(f"Unverified rollback entry retained for manual recovery at {self.path}", file=sys.stderr)


def fingerprint(bundle):
    no_symlinks(bundle)
    files = {}
    for path in sorted(bundle.rglob("*")):
        if path.is_symlink():
            raise ValueError("Refusing symlink in component: " + str(path))
        if path.is_file():
            files[str(path.relative_to(bundle))] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "mode": path.stat().st_mode & 0o777,
            }
    if not files:
        raise ValueError("Empty component")
    return files


def check_identity(bundle):
    fingerprint(bundle)
    with (bundle / "Contents/Info.plist").open("rb") as stream:
        info = plistlib.load(stream)
    if info.get("CFBundleIdentifier") != BUNDLE_ID:
        raise ValueError("Not a Voxide component")
    components = info.get("AudioComponents", [])
    if len(components) != 1 or any(components[0].get(key) != value for key, value in IDENTITY.items()):
        raise ValueError("Wrong AU type/subtype/manufacturer")
    return info.get("CFBundleShortVersionString", "unknown")


def sign(bundle):
    subprocess.run(["codesign", "--force", "--sign", "-", "--timestamp=none", str(bundle)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(bundle)], check=True)


def verify_validation_output(text, expected_version):
    if "AU VALIDATION SUCCEEDED." not in text:
        raise ValueError("auval did not report successful validation")
    identity = "VALIDATING AUDIO UNIT: 'aumf' - 'Vx00' - 'Vxid'"
    if identity not in text:
        raise ValueError("auval validated a different component identity")
    version = re.search(r"Component Version:\s*(\d+\.\d+\.\d+)", text)
    if version is None or version.group(1) != expected_version:
        actual = version.group(1) if version else "missing"
        raise ValueError(f"AU registry version is {actual}, expected {expected_version}. "
                         "Rescan only Voxide in Logic's Plug-in Manager before claiming installed-host acceptance; do not reset broad caches.")


def owned_component(target, ledger):
    no_symlinks(target)
    no_symlinks(ledger)
    if not ledger.exists():
        raise ValueError("Existing component has no Voxide ownership ledger; refusing replacement")
    data = json.loads(ledger.read_text())
    if data.get("path") != str(target) or data.get("files") != fingerprint(target):
        raise ValueError("Installed component was edited or is not owned; refusing replacement")
    check_identity(target)
    return data


def install(source, install_dir, state_dir, signer=sign):
    source = no_symlinks(source)
    install_dir = no_symlinks(install_dir)
    state_dir = no_symlinks(state_dir)
    version = check_identity(source)
    target = install_dir / COMPONENT
    if source == target or source in target.parents or target in source.parents:
        raise ValueError("Source and destination must be separate")
    install_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    ledger = no_symlinks(state_dir / "au-install.json")
    lock = no_symlinks(state_dir / "au-install.lock")
    with lock.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        if present(target):
            owned_component(target, ledger)
        backup = None
        # Recovery stages are outside AU discovery as well as outside automatic
        # TemporaryDirectory cleanup. Publication still uses an exclusive rename;
        # cross-volume destinations fail safely rather than falling back to a copy.
        with InstallStage(state_dir) as stage:
            staged = stage.path / COMPONENT
            shutil.copytree(source, staged)
            signer(staged)
            check_identity(staged)
            data = {"path": str(target), "version": version, "files": fingerprint(staged)}
            candidate_identity = entry_identity(staged)
            pending = state_dir / ("au-install-" + uuid.uuid4().hex + ".json")
            published = False
            try:
                # Signing may take time. Revalidate whatever occupies the target
                # now, even if it did not exist at the first check.
                if present(target):
                    previous = owned_component(target, ledger)
                    previous_identity = entry_identity(target)
                    backup_dir = no_symlinks(state_dir / "backups")
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    backup = backup_dir / ("voxide-" + uuid.uuid4().hex + ".component")
                    rename_exclusive(target, backup)
                    if (entry_identity(backup) != previous_identity
                            or fingerprint(backup) != previous["files"]):
                        raise RuntimeError("Component changed during replacement; refusing publication")
                rename_exclusive(staged, target)
                published = True
                pending.write_text(json.dumps(data, indent=2) + "\n")
                os.replace(pending, ledger)
            except Exception as failure:
                try:
                    if published and present(target):
                        # Never move/delete a concurrently replaced or edited bundle.
                        if (entry_identity(target) != candidate_identity
                                or fingerprint(target) != data["files"]):
                            raise RuntimeError("Published component changed; refusing destructive rollback")
                        # RENAME_EXCL checks the destination, not the source. A
                        # different source may arrive after our pre-move check.
                        stage.safe_to_remove = False
                        rename_exclusive(target, staged)
                        if (entry_identity(staged) != candidate_identity
                                or fingerprint(staged) != data["files"]):
                            raise RuntimeError(f"Rollback source changed; unverified entry retained at {staged}")
                        stage.safe_to_remove = True
                    if backup is not None and present(backup):
                        rename_exclusive(backup, target)
                except Exception as rollback_error:
                    raise RuntimeError(f"Rollback could not restore the target; any previous bundle is preserved at {backup}: {rollback_error}") from failure
                finally:
                    try:
                        pending.unlink(missing_ok=True)
                    except OSError as cleanup_error:
                        print(f"Pending ledger cleanup failed at {pending}: {cleanup_error}", file=sys.stderr)
                raise
        return {"installed": str(target), "version": version,
                "backup": str(backup) if backup else None, "files": data["files"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "validate"])
    parser.add_argument("--build-dir", type=Path, default=ROOT / "build/local-release")
    args = parser.parse_args()
    report_dir = ROOT / "build/au-checks" / (datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    report_dir.mkdir(parents=True)
    result = {"action": args.action, "identity": IDENTITY, "status": "running"}
    try:
        if args.action == "install":
            result.update(install(args.build_dir / "voxide_artefacts/Release/AU" / COMPONENT,
                                  DEFAULT_INSTALL, DEFAULT_STATE))
        else:
            target = DEFAULT_INSTALL / COMPONENT
            installed = owned_component(target, DEFAULT_STATE / "au-install.json")
            subprocess.run(["codesign", "--verify", "--deep", "--strict", str(target)], check=True)
            result["files"] = fingerprint(target)
            command = ["launchctl", "asuser", str(os.getuid()), "/usr/bin/auval", "-v",
                       IDENTITY["type"], IDENTITY["subtype"], IDENTITY["manufacturer"]]
            result["command"] = command
            with (report_dir / "auval.log").open("w") as log:
                process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
            result["exit_code"] = process.returncode
            print((report_dir / "auval.log").read_text())
            if process.returncode:
                raise subprocess.CalledProcessError(process.returncode, command)
            verify_validation_output((report_dir / "auval.log").read_text(), installed["version"])
        result["status"] = "pass"
    except Exception as error:
        result["status"] = "fail"
        result["error"] = str(error)
        raise
    finally:
        (report_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print("AU evidence:", report_dir)


if __name__ == "__main__":
    main()
