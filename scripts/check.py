#!/usr/bin/env python3
"""Local validation only: never install an AU or open an audio device."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def output(command):
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def source_fingerprint():
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    ).decode().split("\0")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in sorted(set(names)) if name and (ROOT / name).is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Debug/Release plus focused ASan/TSan")
    parser.add_argument("--profile", choices=["debug", "release", "asan", "tsan"])
    parser.add_argument("--offline", action="store_true", help="Require cached dependencies")
    parser.add_argument("--engines", action="store_true", help="Also run isolated PR04 engine checks/research; never links them into the AU")
    parser.add_argument("--interactions", action="store_true", help="Also run PR05 three-voice interaction qualification; isolated from the AU")
    parser.add_argument("--fresh", action="store_true", help="Build in new per-run directories without deleting anything")
    parser.add_argument("--jobs", type=int, default=6)
    args = parser.parse_args()
    if args.full and args.profile:
        parser.error("Choose --full or --profile")
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    reports = ROOT / "build" / "checks" / (stamp + "-" + uuid.uuid4().hex[:8])
    reports.mkdir(parents=True)
    metadata = {
        "started_utc": stamp, "architecture": platform.machine(), "macos": platform.mac_ver()[0],
        "python": sys.version, "revision": output(["git", "rev-parse", "HEAD"]),
        "git_status": output(["git", "status", "--short"]), "files": source_fingerprint(),
        "clang": output(["clang", "--version"]), "cmake": output(["cmake", "--version"]),
        "sdk": output(["xcrun", "--show-sdk-version"]), "steps": [], "status": "running",
    }
    manifest = reports / "environment.json"

    def run(label, command, env=None):
        print("+", " ".join(command), flush=True)
        step = {"label": label, "command": command, "log": label + ".log"}
        metadata["steps"].append(step)
        manifest.write_text(json.dumps(metadata, indent=2) + "\n")
        with (reports / step["log"]).open("w") as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env)
        step["exit_code"] = result.returncode
        if result.returncode:
            print((reports / step["log"]).read_text())
            raise subprocess.CalledProcessError(result.returncode, command)

    profiles = [args.profile] if args.profile else (["debug", "release", "asan", "tsan"] if args.full else ["debug"])
    metadata["profiles"] = profiles
    try:
        for profile in profiles:
            preset = "local-" + profile
            build_dir = reports / "build" / profile if args.fresh else ROOT / "build" / preset
            run(profile + "-configure", ["cmake", "--preset", preset,
                "-B", str(build_dir),
                "-DVOXIDE_OFFLINE=" + ("ON" if args.offline else "OFF"),
                "-DPython3_EXECUTABLE=" + sys.executable])
            targets = ["--target", "voxide_dsp_tests", "voxide_processor_tests", "voxide_studio_reference_tests"] if profile in ("asan", "tsan") else []
            run(profile + "-build", ["cmake", "--build", str(build_dir), "--parallel", str(args.jobs), *targets])
            env = os.environ.copy()
            if profile == "asan":
                env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1"
            if profile == "tsan":
                env["TSAN_OPTIONS"] = "halt_on_error=1"
            selection = ["-R", "^(dsp|processor|studio_ui|studio_reference)$"] if profile in ("asan", "tsan") else []
            run(profile + "-test", ["ctest", "--test-dir", str(build_dir), "--output-on-failure", "--no-tests=error", *selection], env)
            if profile == "release":
                run("release-tracking-research", [sys.executable, "scripts/tracking_evaluation.py",
                    "--binary", str(build_dir / "voxide_tracking_probe")])
            configuration = "Release" if profile == "release" else "Debug"
            binaries = [build_dir / "voxide_dsp_tests",
                        build_dir / "libvoxide_allocation_audit.dylib",
                        build_dir / "voxide_processor_tests_artefacts" / configuration / "voxide_processor_tests"]
            if profile in ("debug", "release"):
                binaries.append(build_dir / "voxide_tracking_probe")
                binaries.append(build_dir / "voxide_au_render_tests")
                binaries.append(build_dir / "voxide_artefacts" / configuration
                                / "AU/voxide.component/Contents/MacOS/voxide")
            metadata.setdefault("binaries", {})[profile] = {
                str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in binaries
            }
            dependency_manifest = build_dir / "_deps/juce-source.sha256"
            if dependency_manifest.exists():
                metadata.setdefault("dependency_content", {})[profile] = dependency_manifest.read_text().splitlines()
        if args.engines:
            engine_command = [sys.executable, "scripts/engine_evaluation.py", "check", "--jobs", str(args.jobs)]
            if args.full: engine_command.append("--full")
            if args.offline: engine_command.append("--offline")
            run("isolated-engine-checks", engine_command)
        if args.interactions:
            command = [sys.executable, "scripts/interaction_evaluation.py", "check", "--offline", "--jobs", str(args.jobs)]
            if args.full: command.append("--full")
            run("isolated-interaction-checks", command)
        metadata["source_unchanged"] = source_fingerprint() == metadata["files"]
        if not metadata["source_unchanged"]:
            raise RuntimeError("Project files changed during checks; rerun against a stable snapshot")
        metadata["status"] = "pass"
    except (subprocess.CalledProcessError, OSError, RuntimeError):
        metadata["status"] = "fail"
        raise
    finally:
        manifest.write_text(json.dumps(metadata, indent=2) + "\n")
        print("Validation evidence:", reports)


if __name__ == "__main__":
    main()
