#!/usr/bin/env python3
"""Verify the separate evaluation AU, without installing, launching or scanning hosts."""
from pathlib import Path
import plistlib
import subprocess
import sys

from evaluation_common import require


def verify(component):
    info=plistlib.loads((component/"Contents/Info.plist").read_bytes())
    require(info["CFBundleIdentifier"]=="com.voxide.audio.studioeval", "Wrong evaluation bundle identity")
    entries=info["AudioComponents"]
    require(len(entries)==1, "Unexpected AU component count")
    entry=entries[0]
    require((entry["type"],entry["subtype"],entry["manufacturer"])
            ==("aufx","Vx6b","Vxid"), "Evaluation AU must not replace the product component")
    binary=component/"Contents/MacOS"/info["CFBundleExecutable"]
    require(subprocess.check_output(["lipo","-archs",str(binary)],text=True).strip()=="arm64", "Wrong AU architecture")
    linked=subprocess.check_output(["otool","-L",str(binary)],text=True).splitlines()[1:]
    libraries=[line.strip().split(" (",1)[0] for line in linked]
    require(libraries and all(path.startswith(("/System/","/usr/lib/")) for path in libraries),
            "AU contains a non-system/test dynamic dependency")
    require(not any("allocation" in path.lower() or "trace" in path.lower() for path in libraries),
            "Test allocator interposer must never be loaded into Logic")
    subprocess.run(["codesign","--verify","--strict",str(component)],check=True,capture_output=True)
    return {"bundle_id":info["CFBundleIdentifier"],"type":entry["type"],"subtype":entry["subtype"],"libraries":libraries}


if __name__=="__main__":
    require(len(sys.argv)==2, "Pass the built evaluation component path")
    print(verify(Path(sys.argv[1])))
