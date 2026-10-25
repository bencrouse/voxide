#!/usr/bin/env python3
"""Prepare only the existing pinned Rubber Band sources, always offline."""
import argparse
import json
from pathlib import Path
from engine_dependencies import ROOT, PINS, prepare


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination",type=Path,required=True)
    parser.add_argument("--cache",type=Path,default=ROOT/".cache/dependencies")
    args=parser.parse_args()
    package=next(p for p in json.loads(PINS.read_text())["packages"] if p["name"]=="rubberband")
    result=prepare(package,args.cache,args.destination,offline=True)
    (args.destination/"product-engine.json").write_text(json.dumps(result,indent=2)+"\n")
    print(result["source"])


if __name__=="__main__":main()
