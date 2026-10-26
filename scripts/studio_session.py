#!/usr/bin/env python3
"""PR09 synthetic AU screen and opt-in metadata analysis; never operate Logic/audio."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess

import au
from evaluation_common import ROOT, load_json, require, sha256, write_json
from evaluation_metrics import percentile
from engine_metrics import callback_metrics
from host_integration import native_binary, stamp
from verify_bundle import verify_linkage

CONTRACT=ROOT/"docs/evidence/pr-02/contract.json"
SCOPE="Processor-body metadata is not full AU-wrapper timing, allocation proof, dropout detection, pitch grading or independent listening"
CALLBACK_KEYS={"kind","sequence","tick","elapsed_ticks","frames","rate","status","active","enabled","root","scale","epoch","offline","bypassed","transport_known","playing","peak","nonfinite"}
HEADER_KEYS={"kind","schema","version","revision","profile","instance","module_path","module_file_sha256","os","cpu","unix_ms","tick_hz","scope","pcm_recorded","allocation_audit_available"}
END_KEYS={"kind","callbacks","last_sequence","dropped","unix_ms"}


def integer(value,minimum=0):
    require(type(value) is int and value>=minimum,"Invalid integer metadata");return value


def finite(value,minimum=0):
    require(type(value) in (int,float) and math.isfinite(value) and value>=minimum,"Invalid finite metadata");return value


def stats(values):
    require(values,"No callback observations")
    return {"p50":percentile(values,.5),"p95":percentile(values,.95),"p999":percentile(values,.999),"max":max(values)}


def unique_pairs(pairs):
    result={}
    for key,value in pairs:
        require(key not in result,"Duplicate metadata field");result[key]=value
    return result


def analyse_screen(rows):
    quality=load_json(CONTRACT)["quality"];cases=[]
    names={f"{rate}-{mode}" for rate in (44100,48000) for mode in range(3)}
    require({r["case"] for r in rows}==names,"Incomplete screen matrix")
    for name in sorted(names):
        rate,mode=map(int,name.split("-"));selected=[r for r in rows if r["case"]==name]
        partitions=([128],[512],[32,128,257,512,1024])[mode];at=0;wet=[0]*5
        for i,row in enumerate(selected):
            require(int(row["rate"])==rate and int(row["begin"])==at and int(row["frames"])==min(partitions[i%len(partitions)],rate*5-at),"Screen timeline/block sequence changed")
            change=at//rate;even=change>0 and change%2==0
            require(tuple(int(row[k]) for k in ("requested_root","requested_scale","degree1","degree2","degree3"))
                ==((5+change)%12,change%3 if change else 1,-2 if even else 2,3 if even else 4,5 if even else 6),"Screen musical workload changed")
            for key in ("ns","allocations","nonfinite","wet_samples"):require(int(row[key])>=0,"Negative screen observation")
            require(int(row["wet_samples"])<=int(row["frames"]),"Invalid wet observation")
            finite(float(row["peak"]));at+=int(row["frames"])
            wet[min(4,int(row["begin"])//rate)]+=int(row["wet_samples"])
        require(at==rate*5,"Truncated screen")
        timing=callback_metrics(selected,rate,True,quality,rate*5)
        timing["scope"]="Full exact-built AudioUnitRender invocation including input callbacks; synthetic paced Release host, not Logic"
        occupancy=[int(r["ns"])*rate/(1e9*int(r["frames"])) for r in selected]
        peak=max(float(r["peak"]) for r in selected)
        gates={"occupancy":timing["occupancy_target_met_on_this_run_only"],"zero_overdue":timing["overdue_callbacks"]==0,
            "zero_allocations":timing["allocation_calls"]==0,"finite":all(int(r["nonfinite"])==0 for r in selected),
            "headroom":peak<1,"api":all(int(r["api_error"])==0 for r in selected),"aggregate_wet_each_body_second":all(wet[1:])}
        cases.append({"case":name,"rate":rate,"block":"variable" if mode==2 else partitions[0],"timing":timing,"occupancy":stats(occupancy),
            "peak":peak,"wet_samples_by_second":wet,"scheduler_lag_ns":stats([int(r["scheduler_lag_ns"]) for r in selected]),
            "gates":gates,"status":"pass_this_screen_only" if all(gates.values()) else "failed_screen"})
    return cases


def screen(build,output=None):
    build=au.no_symlinks(Path(build).absolute());binary,profile=native_binary(build)
    require(profile=="Release","Timing requires Release; Debug/sanitizers are not performance evidence")
    component=build/"voxide_artefacts/Release/AU/voxide.component"
    require(au.check_identity(component)=="0.4.0","Build the PR09 instrumented product first");verify_linkage(component)
    expected=au.fingerprint(component);helper_hash=sha256(binary);contract_hash=sha256(CONTRACT)
    directory=au.no_symlinks(Path(output).absolute() if output else ROOT/"build/pr-09-screens"/stamp());directory.mkdir(parents=True,exist_ok=False)
    report={"schema":"voxide.pr09-screen-report.v1","status":"running","cases":[],"component":str(component),"component_files":expected,
        "native_binary_sha256":helper_hash,"contract_sha256":contract_hash,"environment":{"platform":platform.platform(),"load_start":os.getloadavg()},
        "Logic_operated":False,"private_recording_read":False,"qualification":"incomplete_studio_qualification","scope":"Controlled synthetic screen only; all failures/outliers retained"}
    write_json(directory/"started.json",report)
    try:
        pids=[]
        for repeat in range(2):
            require(au.fingerprint(component)==expected and sha256(binary)==helper_hash,"Screen build changed")
            result=directory/f"process-{repeat}.json";raw=directory/f"process-{repeat}.csv"
            command=[str(binary),"--component",str(component),"--screen",str(raw),"--report",str(result)]
            with (directory/f"process-{repeat}.log").open("x") as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
            native=load_json(result)
            require(native.get("schema")=="voxide.pr09-screen.v1" and native.get("status")=="captured_not_qualified"
                and native.get("profile")=="Release" and native.get("cases")==6 and native.get("voices")==3 and native.get("seconds_per_case")==5
                and native.get("full_AudioUnitRender_timing") is True and native.get("allocation_audit") is True and native.get("Logic_operated") is False,"Wrong/incomplete screen report")
            require(all(type(native[k]) is int for k in ("cases","voices","seconds_per_case")),"Invalid screen counters")
            pids.append(integer(native.get("pid"),1))
            with raw.open() as stream:cases=analyse_screen(list(csv.DictReader(stream)))
            report["cases"].append({"repeat":repeat,"pid":pids[-1],"raw_sha256":sha256(raw),"cases":cases})
            require(au.fingerprint(component)==expected and sha256(binary)==helper_hash and sha256(CONTRACT)==contract_hash,"Screen build/contract changed")
        require(pids[0]!=pids[1],"Screen repeat did not use a fresh process")
        report["status"]="controlled_screen_pass_not_Logic_qualification" if all(c["status"]=="pass_this_screen_only" for r in report["cases"] for c in r["cases"]) else "failed_controlled_screen"
    except Exception as error:report.update(status="fail",error=str(error));raise
    finally:write_json(directory/"report.json",report)
    return directory


def parse_log(path,expected_binary_sha256):
    """Strict metadata-only parser; caller must establish access consent first."""
    require(re.fullmatch(r"[0-9a-f]{64}",expected_binary_sha256) is not None,"Expected exact module-file SHA-256")
    occupancy=[];costs=[];rates=set();roots=set();scales=set();epochs=set();frames=0;count=0;previous_end=None;first=None;last=None
    bad_status=offline=bypassed=nonfinite=overdue=active3=enabled3=playing_frames=zero_frames=0;peak=0;header=end=None
    with path.open() as stream:
        for line in iter(lambda:stream.readline(16385),""):
            require(len(line)<=16384 and line.endswith("\n"),"Oversized/truncated/non-metadata log line")
            row=json.loads(line,object_pairs_hook=unique_pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError("Nonfinite JSON")))
            require(type(row) is dict and end is None,"Unexpected data after footer")
            if header is None:
                require(set(row)==HEADER_KEYS and row.get("kind")=="header" and row.get("schema")=="voxide.pr09-session.v1","Wrong session metadata header")
                require(row.get("version")=="0.4.0" and row.get("profile")=="Release" and row.get("pcm_recorded") is False
                    and row.get("allocation_audit_available") is False and row.get("scope")=="processor render body only; excludes AU wrapper, telemetry collection and file IO","Wrong/unqualified capture scope")
                require(row.get("module_file_sha256")==expected_binary_sha256,"Module file differs from requested candidate")
                integer(row["tick_hz"],1);integer(row["unix_ms"],1);header=row;continue
            if row.get("kind")=="end":
                require(set(row)==END_KEYS,"Wrong footer fields");end=row;continue
            require(set(row)==CALLBACK_KEYS and row.get("kind")=="callback","Unknown, aborted or non-metadata record")
            count+=1;require(integer(row["sequence"],1)==count,"Lost/repeated callback record")
            tick=integer(row["tick"],1);elapsed=integer(row["elapsed_ticks"]);n=integer(row["frames"]);rate=integer(row["rate"],1)
            require(rate in (44100,48000) and (previous_end is None or tick>=previous_end),"Invalid callback clock/rate")
            require(all(type(row[k]) is bool for k in ("offline","bypassed","transport_known","playing")),"Invalid processing/transport mode")
            for key in ("status","active","enabled","root","scale","epoch","nonfinite"):integer(row[key])
            require(row["status"]<=6 and row["active"]<=7 and row["enabled"]<=7 and row["root"]<12 and row["scale"]<42,"Invalid callback state")
            first=tick if first is None else first;last=tick+elapsed;previous_end=last;rates.add(rate);frames+=n
            cost=elapsed/header["tick_hz"];costs.append(cost)
            if n:
                value=cost*rate/n;occupancy.append(value);overdue+=value>1
            else:zero_frames+=1 # Retained control callback; no audio deadline exists.
            peak=max(peak,finite(row["peak"]));nonfinite+=row["nonfinite"];offline+=row["offline"];bypassed+=row["bypassed"];bad_status+=row["status"]!=1
            active3+=row["active"]==7;enabled3+=row["enabled"]==7;roots.add(row["root"]);scales.add(row["scale"]);epochs.add(row["epoch"])
            if row["transport_known"] and row["playing"] and not row["offline"] and not row["bypassed"]:playing_frames+=n
    require(header and end and count>0 and occupancy,"Missing header/audio callbacks/explicit stop")
    require(integer(end["callbacks"])==integer(end["last_sequence"])==count and integer(end["dropped"])==0,"Truncated/dropped capture")
    require(integer(end["unix_ms"],1)>=header["unix_ms"] and len(rates)==1,"Capture rate/configuration changed; analyse separate sessions")
    rate=next(iter(rates));wall=(end["unix_ms"]-header["unix_ms"])/1000;span=(last-first)/header["tick_hz"];exposure=frames/rate
    quality=load_json(CONTRACT)["quality"]
    gates={"body_occupancy":percentile(occupancy,.999)<quality["callback_occupancy_p999_max_exclusive"],"zero_body_overdue":overdue==0,
        "finite":nonfinite==0,"headroom":peak<1,"healthy":bad_status==0,"realtime_only":offline==0,
        "30_minute_exposure":min(wall,span,playing_frames/rate)>=quality["logic_dropout_session_minutes"]*60,
        "three_active_observed":active3>0,"scale_automation_observed":len(roots)>1 and len(scales)>1}
    return {"schema":"voxide.pr09-session-analysis.v1","status":"metadata_gates_pass_qualification_still_incomplete" if all(gates.values()) else "failed_or_incomplete_metadata_gates",
        "qualification":"incomplete_studio_qualification","scope":SCOPE,"module_file_sha256":expected_binary_sha256,"callbacks":count,"rate":rate,
        "wall_seconds":wall,"callback_span_seconds":span,"rendered_seconds":exposure,"reported_playing_seconds":playing_frames/rate,"body_occupancy":stats(occupancy),"body_seconds":stats(costs),
        "overdue":overdue,"zero_frame_callbacks":zero_frames,"peak":peak,"bad_status_callbacks":bad_status,"offline_callbacks":offline,"bypassed_callbacks":bypassed,
        "three_enabled_callbacks":enabled3,"three_active_callbacks":active3,"roots_observed":sorted(roots),"scales_observed":sorted(scales),"epochs_observed":len(epochs),"gates":gates,
        "unmeasured":["complete Logic AU-wrapper callback occupancy/allocations","dropouts/overload alerts/stuck output observations","multiple-instance/editor/transport exercise attestation",
            "approved PR06B processed-character rubric and independent final listening including challenge c","formal pitch/full-support and licensing","exact cached loaded image identity (hash is module file at capture start)"]}


def analyse(path,expected_binary_sha256,*,allow_session_log=False,output=None):
    require(allow_session_log,"Session metadata access requires --allow-session-log; no audio access is implied")
    path=au.no_symlinks(Path(path).absolute());require(path.is_relative_to(ROOT/"evaluation/pr-09") and path.suffix==".jsonl","Session metadata must remain under ignored evaluation/pr-09")
    directory=au.no_symlinks(Path(output).absolute() if output else ROOT/"evaluation/pr-09"/("analysis-"+stamp()))
    require(directory.is_relative_to(ROOT/"evaluation/pr-09"),"Private session report must remain under evaluation/pr-09");directory.mkdir(parents=True,exist_ok=False)
    report={"schema":"voxide.pr09-session-analysis.v1","status":"running","qualification":"incomplete_studio_qualification","audio_read":False}
    try:
        before=sha256(path);report.update(parse_log(path,expected_binary_sha256));require(sha256(path)==before,"Session log changed during analysis");report["metadata_sha256"]=before
    except Exception as error:report.update(status="fail",error=str(error));raise
    finally:write_json(directory/"report.json",report)
    return directory


def kit():
    directory=au.no_symlinks(ROOT/"evaluation/pr-09"/("session-kit-"+stamp()));directory.mkdir(parents=True,exist_ok=False)
    (directory/"CHECKLIST.md").write_text((ROOT/"docs/PR09_STUDIO_SESSION.md").read_text())
    write_json(directory/"status.json",{"schema":"voxide.pr09-kit.v1","qualification":"incomplete_studio_qualification","Logic_operated":False,"audio_access":False,
        "actual_30_minute_Logic_soak":"pending","independent_final_listening":"pending_rubric_and_listeners","prior_PR08_user_acceptance":"accepted, not a PR09 performance/soak result"})
    return directory


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="action",required=True)
    command=sub.add_parser("screen");command.add_argument("--build-dir",type=Path,default=ROOT/"build/local-release");command.add_argument("--output",type=Path)
    command=sub.add_parser("analyse");command.add_argument("metadata",type=Path);command.add_argument("--expected-binary-sha256",required=True);command.add_argument("--allow-session-log",action="store_true");command.add_argument("--output",type=Path)
    sub.add_parser("kit");args=parser.parse_args()
    if args.action=="screen":result=screen(args.build_dir,args.output)
    elif args.action=="analyse":result=analyse(args.metadata,args.expected_binary_sha256,allow_session_log=args.allow_session_log,output=args.output)
    else:result=kit()
    print(result)
    if args.action in ("screen","analyse"):
        status=load_json(result/"report.json")["status"]
        if status not in ("controlled_screen_pass_not_Logic_qualification","metadata_gates_pass_qualification_still_incomplete"):raise SystemExit(2)


if __name__=="__main__":main()
