#!/usr/bin/env python3
"""PR08 synthetic exact-AU tests and opt-in installed checks; never operate Logic."""
import argparse
import datetime
from contextlib import ExitStack
import fcntl
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import uuid

import au
from evaluation_common import ROOT, load_json, require, sha256, write_json, write_wav
from verify_bundle import verify_linkage


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8]


def native_binary(build):
    cache=(build/"CMakeCache.txt").read_text()
    profile=re.search(r"^CMAKE_BUILD_TYPE:[^=]+=(Release|Debug)$",cache,re.MULTILINE)
    require(profile is not None,"Expected a normal Debug/Release build, not a sanitizer/native timing claim")
    sanitizer=re.search(r"^VOXIDE_SANITIZER:[^=]+=(.*)$",cache,re.MULTILINE)
    require(sanitizer is None or not sanitizer.group(1).strip(),"Native host checks must not run under a sanitizer profile")
    binary=au.no_symlinks(build/"voxide_host_integration_tests_artefacts"/profile.group(1)/"voxide_host_integration_tests")
    require(binary.is_file(),"Build voxide_host_integration_tests first")
    return binary,profile.group(1)


def validate_native(report,cases):
    require(report.get("schema")=="voxide.pr08-native-host.v1" and report.get("status")=="pass"
            and type(report.get("cases")) is int and report["cases"]==cases,"Incomplete/wrong native host report")
    require(report.get("exact_reference") is True and report.get("latency_notifications") is True
            and report.get("installed_registry_or_Logic_test") is False,"Native report overclaims or lacks checks")
    require(report.get("initial_parameters_checked") is True and type(report.get("recall_parameter_negative_controls")) is int
            and report["recall_parameter_negative_controls"]==2,"Native report lacks initial-parameter recall guards")
    require(type(report.get("pid")) is int and report["pid"]>0,"Missing native process identity")


def run_native(build,component,directory,report,fresh_only=False,*,expected_files=None):
    binary,_=native_binary(build);report["native_binary_sha256"]=sha256(binary)
    before=au.fingerprint(component) if expected_files is None else expected_files

    def unchanged():
        require(au.fingerprint(component)==before and sha256(binary)==report["native_binary_sha256"],"Tested binary/bundle changed from requested build")

    def run(label,options,cases):
        unchanged()
        result=directory/(label+".json");command=[str(binary),"--component",str(component),*options,"--report",str(result)]
        report.setdefault("commands",[]).append(command)
        with (directory/(label+".log")).open("x") as log:
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        unchanged()
        value=load_json(result);validate_native(value,cases);return value

    if not fresh_only:report["exact_AU"]=run("exact-au",[],14)
    state=directory/"state.plist";first=directory/"before.f32";second=directory/"reopened.f32"
    a=run("save-process",["--save-state",str(state),"--audio",str(first)],1);state_hash=sha256(state)
    b=run("reopen-process",["--restore-state",str(state),"--audio",str(second)],1)
    require(a["pid"]!=b["pid"],"Recall did not use a fresh process")
    require(sha256(state)==state_hash,"State changed during recall")
    require(first.stat().st_size==second.stat().st_size==76800*4,"Fresh-process audio duration/tail mismatch")
    payload=first.read_bytes()
    require(payload==second.read_bytes(),"Fresh-process settings/automation/bounce audio changed")
    samples=[sample[0] for sample in struct.iter_unpack("<f",payload)]
    require(all(math.isfinite(x) for x in samples) and any(abs(x)>1e-4 for x in samples),"Invalid/silent recall audio")
    unchanged()
    report["fresh_process_recall"]={"pids":[a["pid"],b["pid"]],"state_sha256":state_hash,
        "audio_sha256":sha256(first),"frames":76800,"sample_rate":48000,"format":"mono-f32le","exact":True}
    report["component_files"]=before


def check(build,output=None,*,fresh_only=False,installed=False,allow_installed=False,allow_auval=False):
    # Installed files, ownership ledgers and auval are untouched until both
    # explicit operation approvals are present. Normal checks use build artifacts.
    if installed:require(allow_installed and allow_auval,"Installed-AU and auval operations require both explicit approvals")
    with ExitStack() as stack:
        if installed:
            # Cooperate with au.install's exclusive publication lock throughout
            # preflight, auval, exact-path loading and final evidence publication.
            lock=au.no_symlinks(au.DEFAULT_STATE/"au-install.lock")
            stream=stack.enter_context(lock.open("a"));fcntl.flock(stream,fcntl.LOCK_SH)
        return _check_locked(build,output,fresh_only=fresh_only,installed=installed)


def _check_locked(build,output,*,fresh_only,installed):
    build=au.no_symlinks(Path(build).absolute());binary,profile=native_binary(build)
    source=build/"voxide_artefacts"/profile/"AU/voxide.component"
    expected=au.fingerprint(source)
    require(au.check_identity(source)=="0.4.0","Build the current product (0.4.0), not the older product/shell/evaluation AU")
    verify_linkage(source)
    component=source;ledger=None
    if installed:
        component=au.DEFAULT_INSTALL/au.COMPONENT;ledger=au.owned_component(component,au.DEFAULT_STATE/"au-install.json")
        require(ledger["files"]==expected,"Installed bundle differs from the requested build")

    def unchanged():
        require(au.fingerprint(source)==expected and au.fingerprint(component)==expected,"Component changed from requested build")

    unchanged()
    base=ROOT/("evaluation/pr-08" if installed else "build/pr-08-host-checks")
    directory=au.no_symlinks(Path(output).absolute() if output else base/stamp())
    if installed:require(directory.is_relative_to((ROOT/"evaluation/pr-08").absolute()),"Installed/private evidence must stay under ignored evaluation/pr-08")
    directory.mkdir(parents=True,exist_ok=False)
    report={"schema":"voxide.pr08-host-check.v1","status":"running","operation":"installed" if installed else "build-only",
        "component":str(component),"profile":profile,"installed_auval_executed":False,"Logic_operated":False,
        "private_recording_read":False,"host_acceptance":"pending_user_session",
        "requested_component_files":expected,
        "scope":"Synthetic functional AU/recall evidence, not actual Logic PDC, vocal pitch or performance qualification"}
    write_json(directory/"started.json",report)
    try:
        unchanged()
        if installed:
            command=["launchctl","asuser",str(os.getuid()),"/usr/bin/auval","-v",*[au.IDENTITY[key] for key in ("type","subtype","manufacturer")]]
            report["auval_command"]=command
            with (directory/"auval.log").open("x") as log:
                report["installed_auval_executed"]=True
                subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
            au.verify_validation_output((directory/"auval.log").read_text(),ledger["version"])
            unchanged()
            report["registry_scope"]="Identity/version validation, not cryptographic proof of a cached registry image or Logic execution"
        run_native(build,component,directory,report,fresh_only,expected_files=expected)
        unchanged()
        report["status"]="native_functional_pass_logic_pending"
    except Exception as error:
        report["status"]="fail";report["error"]=str(error);raise
    finally:write_json(directory/"report.json",report)
    return directory


CASES=("installed_identity_auval","recorded_source_route_no_doubled_lead","unity_PDC_null",
       "three_voices_and_scale_automation","cycle_seek_stop_resume_midphrase","bypass_reset_silence",
       "save_close_quit_reopen","duplicate_and_fresh_instance","low_latency_mode_off",
       "low_latency_mode_on_restrictions","realtime_offline_bounce_and_tails")


def kit(output=None):
    directory=au.no_symlinks(Path(output).absolute() if output else ROOT/"evaluation/pr-08"/("logic-kit-"+stamp()))
    require(directory.is_relative_to((ROOT/"evaluation/pr-08").absolute()),"Logic-session materials must stay under ignored evaluation/pr-08")
    directory.mkdir(parents=True,exist_ok=False);files={}
    for rate in (44100,48000):
        source=[(.01 if i==0 else .02*math.sin(2*math.pi*220*i/rate)) if i<rate else 0. for i in range(rate*16//10)]
        for prefix,samples in (("first-sample",source),("preroll",[0.]*(rate//4)+source)):
            name=f"{prefix}-{rate}.wav";write_wav(directory/name,rate,samples);files[name]=sha256(directory/name)
    worksheet={"schema":"voxide.pr08-Logic-worksheet.v1","status":"pending_user_session","expected_product_version":"0.4.0",
        "source_kind":"generated_synthetic_probe_not_recorded_vocal","private_recording_selected":None,"private_read_or_render_approval":None,
        "Logic_version":None,"macOS_version":None,"project_path":None,"project_sha256":None,
        "sample_rate":None,"IO_buffer":128,"process_buffer":"Small","PDC":"All","low_latency_mode":"Off",
        "supported_source_bus":None,"original_gain_db":0,"harmony_gain_policy":"one-third per voice, explicit trims/enables",
        "frozen_unity_null_limits":{"max_abs":1e-6,"rms":1e-7,"integer_alignment_error_samples":0},
        "cases":{name:{"status":"pending","observations":None,"evidence_paths":[]} for name in CASES},
        "prior_evaluation_AU_manual_acceptance":"accepted as previously reported; not transferred to this new product binary",
        "files_sha256":files,"limitations":["No .logicx project is fabricated or opened by this command.",
            "No playback, microphone, device or private recording is accessed.","Live physical input must be recorded first.",
            "Known track-fed/Low Latency Mode limitation is not regraded.","Low Latency Mode is inactive during bounce.",
            "MIDI synthesis/chase is deferred; unseen host events cannot be reconstructed."]}
    write_json(directory/"worksheet.json",worksheet)
    instructions=(ROOT/"docs/PR08_LOGIC_CHECKLIST.md").read_text();(directory/"CHECKLIST.md").write_text(instructions)
    return directory


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="action",required=True)
    for name in ("check","recall","installed"):
        command=sub.add_parser(name);command.add_argument("--build-dir",type=Path,default=ROOT/"build/local-release");command.add_argument("--output",type=Path)
        if name=="installed":command.add_argument("--allow-installed-au",action="store_true");command.add_argument("--allow-auval",action="store_true")
    command=sub.add_parser("kit");command.add_argument("--output",type=Path)
    args=parser.parse_args()
    if args.action=="kit":result=kit(args.output)
    else:result=check(args.build_dir,args.output,fresh_only=args.action=="recall",installed=args.action=="installed",
        allow_installed=getattr(args,"allow_installed_au",False),allow_auval=getattr(args,"allow_auval",False))
    print(result)


if __name__=="__main__":main()
