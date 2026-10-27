#!/usr/bin/env python3
"""PR10 local-only identity/evidence checks and cache-only clean-checkout validation."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import shutil
import subprocess
import sys

import au
from evaluation_common import ROOT, load_json, require, sha256, write_json
from host_integration import stamp
from verify_bundle import verify_linkage

BLOCKERS=["44.1 kHz variable-block audio delivery failure remains unresolved",
    "Corrected v2 timing screen has not been measured; old v1 observations are not regraded",
    "Actual representative Logic soak/whole-host timing and allocation observations missing",
    "Independent final listening/revised PR06B rubric, formal full-support accuracy and challenge c remain open",
    "Distribution/licensing clearance and final studio acceptance are not granted"]
BUNDLE_FILES={"Contents/Info.plist","Contents/PkgInfo","Contents/MacOS/voxide","Contents/_CodeSignature/CodeResources"}


def build_path(path):
    path=au.no_symlinks(Path(path).absolute())
    require(path.is_relative_to(ROOT/"build"),"Handoff checks accept only local build/artifact paths, never installed/private paths")
    return path


def relative_path(name,prefix=None):
    require(type(name) is str and name and "\\" not in name,"Invalid handoff path")
    path=PurePosixPath(name)
    require(path.parts and not path.is_absolute() and all(p not in ("..", ".") for p in path.parts),"Unsafe handoff path")
    require(path.as_posix()==name and (prefix is None or path.parts[0]==prefix),"Noncanonical/out-of-scope handoff path")
    return path


def inspect_component(component,expected_sha256=None):
    if expected_sha256 is not None:require(type(expected_sha256) is str and re.fullmatch("[0-9a-f]{64}",expected_sha256),"Invalid expected binary SHA-256")
    component=build_path(component);require(component.name==au.COMPONENT,"Expected the product voxide.component")
    entries=list(component.rglob("*"))
    require(not any(p.is_symlink() for p in entries),"Symlink bundle entry refused")
    require(all(p.is_dir() or p.is_file() for p in entries),"Nonregular bundle entry refused")
    require({p.relative_to(component).as_posix() for p in entries if p.is_file()}==BUNDLE_FILES,"Unexpected bundle layout/resources; refusing unrelated payloads")
    info=plistlib.loads((component/"Contents/Info.plist").read_bytes())
    require(info.get("CFBundleExecutable")=="voxide","Unexpected/unsafe product executable path")
    require(au.check_identity(component)=="0.4.0","Expected current product 0.4.0, not Studio Eval/older shell")
    before=au.fingerprint(component);binary=component/"Contents/MacOS/voxide";digest=sha256(binary)
    if expected_sha256 is not None:require(digest==expected_sha256,"Candidate binary differs from expected identity")
    libraries=verify_linkage(component)
    symbols=subprocess.check_output(["nm","-a",str(binary)],text=True)
    require(not re.search(r"Signalsmith|signalsmith|voxide.*(?:audit|evaluation)|__interpose|traceAllocation",symbols),"Forbidden evaluator/audit/interpose product symbols")
    require(au.fingerprint(component)==before,"Candidate changed during handoff verification")
    return {"component":str(component),"version":"0.4.0","binary_sha256":digest,"files":before,"libraries":libraries,
        "scope":"Signed arm64/system-only exact local bundle identity; not installed registry, cached image, Logic or quality qualification"}


def inspect_artifact(directory):
    directory=build_path(directory);manifest_path=au.no_symlinks(directory/"artifacts.json")
    require(manifest_path.is_file(),"Missing/nonregular artifact manifest");manifest=load_json(manifest_path)
    require(manifest.get("schema")=="voxide.artifacts.v1" and type(manifest.get("files_sha256")) is dict and manifest["files_sha256"],"Wrong/empty artifact manifest")
    entries=list(directory.rglob("*"))
    require(not any(p.is_symlink() for p in entries) and all(p.is_dir() or p.is_file() for p in entries),"Unsafe artifact entries")
    names={p.relative_to(directory).as_posix() for p in entries if p.is_file() and p!=manifest_path}
    require(names==set(manifest["files_sha256"]),"Artifact manifest does not cover exact file set")
    for name,digest in manifest["files_sha256"].items():
        relative_path(name);require(type(digest) is str and re.fullmatch("[0-9a-f]{64}",digest),"Invalid artifact digest")
        require(sha256(au.no_symlinks(directory/name))==digest,"Artifact bytes changed: "+name)
    return {"path":str(directory),"manifest_sha256":sha256(manifest_path),"verified_files":len(names)}


def evidence_index():
    path=au.no_symlinks(ROOT/"docs/evidence/pr-10/handoff-index.json");index=load_json(path)
    require(index.get("schema")=="voxide.pr10-evidence-index.v1" and index.get("qualification")=="not_qualified","Unexpected qualification/index schema")
    result=[];ids=set()
    for entry in index["entries"]:
        require(type(entry.get("id")) is str and entry["id"] not in ids,"Invalid/duplicate evidence ID");ids.add(entry["id"])
        document=ROOT/str(relative_path(entry["document"],"docs"));au.no_symlinks(document)
        require(document.is_file(),"Missing tracked evidence document")
        row=dict(entry,document_sha256=sha256(document))
        if entry.get("artifact_manifest"):
            artifact=ROOT/str(relative_path(entry["artifact_manifest"],"build"));au.no_symlinks(artifact)
            row["raw_artifact_available_in_this_checkout"]=artifact.is_file()
        result.append(row)
    return {"index_sha256":sha256(path),"entries":result,"scope":"Tracked evidence plus optional local build availability only; private evaluation evidence is never opened"}


def verify(component,output=None,*,artifact=None,expected_sha256=None):
    component=build_path(component)
    artifact=build_path(artifact) if artifact is not None else None
    directory=build_path(output if output else ROOT/"build/pr-10-checks"/stamp())
    for source in (component,artifact):
        if source is not None:require(not (directory==source or directory.is_relative_to(source) or source.is_relative_to(directory)),"Report output must be disjoint from verified inputs")
    directory.mkdir(parents=True,exist_ok=False)
    report={"schema":"voxide.pr10-local-check.v1","status":"running","qualification":"not_qualified","blockers":BLOCKERS,
        "installed_files_accessed":False,"Logic_operated":False,"private_recordings_read":False,"distribution_authorized":False}
    try:
        report["candidate"]=inspect_component(component,expected_sha256)
        if artifact is not None:
            artifact=build_path(artifact);require(component==artifact/au.COMPONENT,"Artifact/candidate path mismatch")
            report["artifact"]=inspect_artifact(artifact)
        report["evidence"]=evidence_index();report["status"]="local_identity_and_evidence_check_pass_NOT_qualification"
    except Exception as error:report.update(status="fail",error=str(error));raise
    finally:write_json(directory/"report.json",report)
    return directory


def cache_inventory(cache):
    cache=au.no_symlinks(Path(cache).absolute());pin=(ROOT/"cmake/JucePin.cmake").read_text()
    def value(key):
        match=re.search(r"set\("+key+r'\s+"([^"]+)"\)',pin);require(match is not None,"Missing JUCE pin");return match.group(1)
    rb=next(p for p in load_json(ROOT/"cmake/engine-dependencies.json")["packages"] if p["name"]=="rubberband")
    expected={"juce-"+value("VOXIDE_JUCE_REVISION")+".tar.gz":value("VOXIDE_JUCE_SHA256"),"rubberband-"+rb["revision"]+".tar.gz":rb["sha256"]}
    for name,digest in expected.items():
        path=au.no_symlinks(cache/name);require(path.is_file() and sha256(path)==digest,"Missing/corrupt offline archive: "+name)
    return {"directory":str(cache),"archives_sha256":expected,"downloads_performed":False}


def reproduce(cache,output=None,*,jobs=6):
    require(type(jobs) is int and jobs>0,"Jobs must be positive")
    def git(*args,cwd=ROOT):return subprocess.check_output(["git",*args],cwd=cwd,text=True).strip()
    require(not git("status","--porcelain"),"Reproduction requires committed, clean source; no changes are discarded")
    revision=git("rev-parse","HEAD");tree=git("rev-parse","HEAD^{tree}");cache=cache_inventory(cache)
    directory=build_path(output if output else ROOT/"build/pr-10-reproduction"/stamp());directory.mkdir(parents=True,exist_ok=False);checkout=directory/"checkout"
    report={"schema":"voxide.pr10-reproduction.v1","status":"running","qualification":"not_qualified","blockers":BLOCKERS,
        "source_commit":revision,"source_tree":tree,"cache":cache,"commands":[],"network_operations_requested":False,
        "installed_files_accessed":False,"Logic_operated":False,"private_recordings_read":False,
        "scope":"Fresh local Git checkout and pinned cache-only build/tests; not bit-identical across paths/toolchains or studio qualification"}
    def run(label,command,*,cwd=checkout,env=None):
        report["commands"].append({"label":label,"argv":command})
        write_json(directory/(label+"-command.json"),report["commands"][-1])
        with (directory/(label+".log")).open("x") as log:
            result=subprocess.run(command,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,env=env)
        report["commands"][-1]["returncode"]=result.returncode
        return result
    try:
        run("clone",["git","-c","core.hooksPath=/dev/null","clone","--local","--no-hardlinks","--no-checkout","--no-recurse-submodules",str(ROOT),str(checkout)],cwd=ROOT).check_returncode()
        run("checkout",["git","-c","core.hooksPath=/dev/null","checkout","--detach",revision]).check_returncode()
        require(git("rev-parse","HEAD",cwd=checkout)==revision and not git("status","--porcelain",cwd=checkout),"Clone identity/cleanliness mismatch")
        for profile,sanitizer in (("release",""),("debug",""),("asan","address"),("tsan","thread")):
            build=checkout/"build"/profile
            run(profile+"-configure",["cmake","-G","Unix Makefiles","-S",str(checkout),"-B",str(build),"-DCMAKE_BUILD_TYPE="+("Release" if profile=="release" else "Debug"),"-DVOXIDE_OFFLINE=ON","-DVOXIDE_DEPENDENCY_CACHE="+cache["directory"],"-DVOXIDE_SANITIZER="+sanitizer,"-DPython3_EXECUTABLE="+sys.executable]).check_returncode()
            targets=[] if not sanitizer else ["--target","voxide_dsp_tests","voxide_processor_tests","voxide_studio_reference_tests"]
            run(profile+"-build",["cmake","--build",str(build),"--parallel",str(jobs),*targets]).check_returncode()
            env=os.environ.copy();selection=[] if not sanitizer else ["-R","^(dsp|processor|studio_ui|studio_reference)$"]
            if profile=="asan":env["ASAN_OPTIONS"]="detect_leaks=0:halt_on_error=1"
            if profile=="tsan":env["TSAN_OPTIONS"]="halt_on_error=1"
            result=run(profile+"-tests",["ctest","--test-dir",str(build),"--output-on-failure","--no-tests=error",*selection],env=env)
            shutil.copy2(build/"Testing/Temporary/LastTest.log",directory/(profile+"-LastTest.log"));result.check_returncode()
            print(profile+" clean-checkout checks pass",flush=True)
        report["candidate"]=inspect_component(checkout/"build/release/voxide_artefacts/Release/AU/voxide.component")
        require(not git("status","--porcelain",cwd=checkout) and git("rev-parse","HEAD^{tree}",cwd=checkout)==tree,"Reproduction checkout changed")
        require(cache_inventory(Path(cache["directory"]))==cache,"Dependency archives changed")
        report["status"]="clean_checkout_cache_only_checks_pass_NOT_qualification"
    except Exception as error:report.update(status="fail",error=str(error));raise
    finally:write_json(directory/"report.json",report)
    return directory


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="action",required=True)
    command=sub.add_parser("verify");command.add_argument("--component",type=Path,required=True);command.add_argument("--artifact",type=Path);command.add_argument("--expected-sha256");command.add_argument("--output",type=Path)
    command=sub.add_parser("reproduce");command.add_argument("--cache",type=Path,default=ROOT/".cache/dependencies");command.add_argument("--output",type=Path);command.add_argument("--jobs",type=int,default=6)
    args=parser.parse_args()
    if args.action=="verify":result=verify(args.component,args.output,artifact=args.artifact,expected_sha256=args.expected_sha256)
    else:result=reproduce(args.cache,args.output,jobs=args.jobs)
    print(result);print("Local engineering checks only; studio qualification remains NOT PASSED.")


if __name__=="__main__":main()
