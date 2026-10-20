#!/usr/bin/env python3
"""Read built bundle metadata without launching the standalone or accessing devices."""
from pathlib import Path
import plistlib
import sys

from au import check_identity


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: verify_bundle.py <standalone.app> <voxide.component>")
    app, component = map(Path, sys.argv[1:])
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    if not info.get("NSMicrophoneUsageDescription", "").strip():
        raise SystemExit("Standalone microphone privacy description is missing")
    check_identity(component)
    print("Standalone privacy metadata and AU identity passed; no device accessed")


if __name__ == "__main__":
    main()
