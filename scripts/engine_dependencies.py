#!/usr/bin/env python3
"""Checksum-pinned, isolated evaluator sources. No package installation or AU linkage."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / "cmake/engine-dependencies.json"


def require(value, message):
    if not value:
        raise ValueError(message)


def reject_symlink(path):
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Symlink dependency path refused")


def tree(directory):
    result = {}
    for path in directory.rglob("*"):
        require(not path.is_symlink(), "Symlink extracted source refused")
        name = path.relative_to(directory).as_posix()
        require(path.is_dir() or path.is_file(), "Nonregular extracted source refused")
        result[name] = "directory" if path.is_dir() else hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def prepare(package, cache, destination, offline=True):
    reject_symlink(cache); reject_symlink(destination)
    cache.mkdir(parents=True, exist_ok=True); destination.mkdir(parents=True, exist_ok=True)
    lock_path = destination / (package["name"] + ".lock")
    cache_lock_path = cache / (package["name"] + "-" + package["revision"] + ".lock")
    reject_symlink(lock_path); reject_symlink(cache_lock_path)
    with lock_path.open("a") as lock, cache_lock_path.open("a") as cache_lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        fcntl.flock(cache_lock, fcntl.LOCK_EX)
        archive = cache / (package["name"] + "-" + package["revision"] + ".tar.gz")
        reject_symlink(archive)
        if not archive.exists():
            require(not offline, "Offline engine archive missing: " + str(archive))
            url = "https://codeload.github.com/" + package["repository"] + "/tar.gz/" + package["revision"]
            data = urllib.request.urlopen(url, timeout=90).read()
            require(hashlib.sha256(data).hexdigest() == package["sha256"], "Downloaded engine archive checksum mismatch")
            with tempfile.TemporaryDirectory(prefix="engine-download-", dir=cache) as temporary:
                staged = Path(temporary) / "archive.tar.gz"
                staged.write_bytes(data)
                require(not archive.exists(), "Archive appeared during locked download; existing bytes preserved")
                staged.rename(archive)
        data = archive.read_bytes()
        require(hashlib.sha256(data).hexdigest() == package["sha256"], "Engine archive checksum mismatch")
        from io import BytesIO
        with tarfile.open(fileobj=BytesIO(data)) as tar:
            members = tar.getmembers()
            canonical = {}
            for member in members:
                name = PurePosixPath(member.name)
                require(not name.is_absolute() and ".." not in name.parts and name.parts[0] == package["root"], "Unsafe archive path")
                require(member.isdir() or member.isfile(), "Archive links/nonregular entries refused")
                relative = PurePosixPath(*name.parts[1:]).as_posix()
                if relative == ".":
                    require(member.isdir(), "Archive root must be a directory")
                    continue
                require(relative not in canonical, "Duplicate archive entry")
                canonical[relative] = "directory" if member.isdir() else hashlib.sha256(tar.extractfile(member).read()).hexdigest()
            # Include implicit directories so layout validation is independent of tar style.
            for name in list(canonical):
                for parent in PurePosixPath(name).parents:
                    if str(parent) != ".": canonical.setdefault(str(parent), "directory")
            source = destination / (package["name"] + "-" + package["revision"])
            reject_symlink(source)
            if source.exists():
                require(source.is_dir() and tree(source) == canonical, "Edited engine source preserved; use a fresh evaluator build directory")
            else:
                with tempfile.TemporaryDirectory(prefix="engine-stage-", dir=destination) as temporary:
                    stage = Path(temporary) / "source"
                    stage.mkdir()
                    for member in members:
                        parts = PurePosixPath(member.name).parts[1:]
                        if not parts: continue
                        target = stage.joinpath(*parts)
                        if member.isdir(): target.mkdir(parents=True, exist_ok=True)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            with target.open("xb") as output: output.write(tar.extractfile(member).read())
                    require(tree(stage) == canonical, "Engine extraction verification failed")
                    stage.rename(source)
        digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        require((source / package["notice"]).is_file(), "Dependency license notice missing")
        return dict(package, source=str(source.resolve()), tree_sha256=digest, files=len(canonical))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/dependencies")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    packages = json.loads(PINS.read_text())["packages"]
    results = [prepare(package, args.cache, args.destination, args.offline) for package in packages]
    (args.destination / "engine-sources.json").write_text(json.dumps({"schema": "voxide.engine-sources.v1", "packages": results}, indent=2) + "\n")
    print("Verified evaluator-only engine sources:", args.destination)


if __name__ == "__main__":
    main()
