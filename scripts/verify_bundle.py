#!/usr/bin/env python3
"""Read built bundle metadata without launching the standalone or accessing devices."""
from pathlib import Path
import plistlib
import subprocess
import sys

from au import check_identity


def verify_linkage(component):
    info=plistlib.loads((component/"Contents/Info.plist").read_bytes())
    binary=component/"Contents/MacOS"/info["CFBundleExecutable"]
    if subprocess.check_output(["lipo","-archs",str(binary)],text=True).strip()!="arm64":
        raise ValueError("Wrong product AU architecture")
    linked=subprocess.check_output(["otool","-L",str(binary)],text=True).splitlines()[1:]
    libraries=[line.strip().split(" (",1)[0] for line in linked]
    if not libraries or not all(path.startswith(("/System/","/usr/lib/")) for path in libraries):
        raise ValueError("Product AU contains a non-system/evaluation dependency")
    sections=subprocess.check_output(["otool","-l",str(binary)],text=True)
    if any(line.split()==["sectname","__interpose"] for line in sections.splitlines()):
        raise ValueError("Product AU contains a test interpose section")
    subprocess.run(["codesign","--verify","--strict",str(component)],check=True,capture_output=True)
    return libraries


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: verify_bundle.py <standalone.app> <voxide.component>")
    app, component = map(Path, sys.argv[1:])
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    if not info.get("NSMicrophoneUsageDescription", "").strip():
        raise SystemExit("Standalone microphone privacy description is missing")
    check_identity(component)
    verify_linkage(component)
    print("Standalone privacy metadata and AU identity passed; no device accessed")


if __name__ == "__main__":
    main()
