#!/usr/bin/env python3
"""PR05 three-voice research. No product engine selection, installs, playback or devices."""
import argparse
import array
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import uuid

from check import source_fingerprint
from evaluation_common import ROOT, CONTRACT, FIXTURES, require, sha256, write_json, load_json, write_wav, read_wav_bytes
from evaluation_common import contained, read_pcm_stream, pcm_sha256
from evaluation_corpus import select_sources, validate_annotation, compare_annotations
from evaluation_contract import load_contract
from evaluation_fixtures import validate as validate_fixtures
from engine_evaluation import CONFIGS, calibrate_instruments, verified_dependencies
from engine_metrics import read_float, write_float_wav, read_csv, callback_metrics, reference_pitch_measurements, estimate_output_pitch
from evaluation_metrics import percentile, cents, measure_unity_delay

IDENTITY_FILES = sorted([
    "InteractionEvaluation/CMakeLists.txt", "InteractionEvaluation/InteractionProcessor.cpp", "InteractionEvaluation/InteractionProcessor.h",
    "InteractionEvaluation/InteractionProbe.cpp", "InteractionEvaluation/InteractionTests.cpp", "Source/DSP/PitchTracker.cpp", "Source/DSP/PitchTracker.h",
    "Source/DSP/HarmonySelector.cpp", "Source/DSP/HarmonySelector.h", "EngineEvaluation/EngineAdapter.cpp", "EngineEvaluation/EngineAdapter.h",
    "Source/Tests/AllocationAudit.cpp", "Source/Tests/AllocationAudit.h", "cmake/engine-dependencies.json"])
CHANNELS = ("lead-direct", "lead-aligned", "native1", "native2", "native3", "voice1", "voice2", "voice3", "sum-direct", "sum-aligned")
VOICINGS = {"upper": (3,7,12), "lower": (-12,-7,-3), "mixed": (-24,7,24)}
DEGREES = {"upper": ((2,4,0),(0,0,1)), "lower": ((-2,-4,0),(0,0,-1)), "mixed": ((0,4,0),(-2,0,2))}
REGIONS = (("low-vowel",.35), ("high-vowel",.35), ("pitch-step",.35), ("breathy",.30), ("z",.20), ("s",.20),
           ("sh",.20), ("plosive",.10), ("bend",.35), ("ending",.25), ("silence",.15), ("bleed",.25))


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8]


def identity():
    return hashlib.sha256("".join(name+"|"+sha256(ROOT/name)+"\n" for name in IDENTITY_FILES).encode()).hexdigest()


def provenance(build, directory):
    files=source_fingerprint()
    binaries={engine:sha256(build/("voxide_"+engine+"_interaction")) for engine in ("signalsmith","rubberband")}
    result={"files":files,"binaries":binaries,"audit_sha256":sha256(build/"engines/libengine_allocation_audit.dylib"),
            "dependencies":verified_dependencies(build/"engines"),"cache_sha256":sha256(build/"CMakeCache.txt"),
            "compiled_source_identity":identity(),"git_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "compiler":subprocess.check_output(["clang","--version"],text=True).strip(),"sdk":subprocess.check_output(["xcrun","--show-sdk-version"],text=True).strip(),
            "contract_sha256":sha256(CONTRACT),"protocol_sha256":sha256(ROOT/"docs/evidence/pr-05/protocol.json")}
    for name,digest in files.items():
        target=directory/"source-snapshot"/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target); require(sha256(target)==digest,"Source changed during archival")
    target=directory/"binaries"; target.mkdir()
    for engine in binaries:
        source=build/("voxide_"+engine+"_interaction"); shutil.copyfile(source,target/source.name)
        require(sha256(target/source.name)==binaries[engine],"Binary changed during archival")
    for source in (build/"engines/libengine_allocation_audit.dylib",build/"CMakeCache.txt",build/"compile_commands.json"):
        shutil.copyfile(source,target/source.name)
    verify_provenance(build,result)
    require(sha256(target/"libengine_allocation_audit.dylib")==result["audit_sha256"] and sha256(target/"CMakeCache.txt")==result["cache_sha256"],"Runtime/configuration changed during archival")
    write_json(directory/"provenance.json",result)
    return result


def verify_provenance(build, p):
    require(source_fingerprint()==p["files"] and identity()==p["compiled_source_identity"],"Source changed during interaction research")
    require(all(sha256(build/("voxide_"+engine+"_interaction"))==digest for engine,digest in p["binaries"].items()),"Interaction binary changed")
    require(sha256(build/"engines/libengine_allocation_audit.dylib")==p["audit_sha256"] and sha256(build/"CMakeCache.txt")==p["cache_sha256"],"Interaction runtime/build changed")
    require(verified_dependencies(build/"engines")==p["dependencies"],"Pinned dependencies changed")


def fixture(directory, rate, impulse=False):
    """New analytic fixtures; never modify or regenerate PR02 assets."""
    values=[]; grid=[]; regions=[]; rng=random.Random(0x50523035); phase=0.; smooth=0.
    if impulse:
        values=[0.]*(rate//3); values[rate//16]=.1
        grid=[{"sample":0,"f0_hz":220.,"voiced":True,"stable":True,"uncertain":False}]
        regions=[{"name":"unity-impulse","begin":0,"end":len(values)}]
    else:
        for name,seconds in REGIONS:
            begin=len(values); count=round(rate*seconds)
            for i in range(count):
                hz=82.4068892282175 if name=="low-vowel" else 1046.5022612023945 if name=="high-vowel" else 220.*2**((i/max(1,count-1))*2/12) if name=="bend" else 220.
                voiced=name not in ("s","sh","plosive","silence")
                phase+=2*math.pi*hz/rate
                harmonic=sum(.08/h*math.sin(h*phase) for h in range(1,min(6,int(rate*.45/hz))+1))
                noise=rng.uniform(-1,1); smooth=.8*smooth+.2*noise
                envelope=min(1.,i/max(1,round(rate*.003)),(count-1-i)/max(1,round(rate*.003)))
                if name=="breathy": value=.6*harmonic+.045*noise
                elif name=="z": value=.5*harmonic+.04*(noise-smooth)
                elif name=="s": value=.06*(noise-smooth)
                elif name=="sh": value=.1*smooth
                elif name=="plosive": value=.15*noise*math.exp(-i/(rate*.012))
                elif name=="silence": value=0.
                elif name=="ending": value=harmonic*(1-i/count)**2
                elif name=="bleed": value=harmonic+.04*math.sin(2*math.pi*311*(begin+i)/rate)
                else: value=harmonic
                values.append(value*envelope)
                if (begin+i)%round(rate*.01)==0:
                    stable=voiced and name not in ("bend","ending") and rate*.05<=i<count-rate*.05
                    grid.append({"sample":begin+i,"f0_hz":hz if voiced else None,"voiced":voiced,"stable":stable,"uncertain":False})
            regions.append({"name":name,"begin":begin,"end":len(values)})
    path=directory/(str(rate)+("-impulse.wav" if impulse else "-suite.wav"))
    write_wav(path,rate,values)
    encoded=path.read_bytes(); info,values=read_wav_bytes(encoded)
    reference={"schema":"voxide.interaction-analytic.v1","sample_rate":rate,"frames":len(values),"grid":grid,"regions":regions,
               "scope":"Synthetic speech-like challenges, not human consonant intelligibility or real-vocal truth"}
    write_json(path.with_suffix(".json"),reference)
    return {"path":path,"sha256":hashlib.sha256(encoded).hexdigest(),"values":values,"reference":reference}


def scale_shift(midi,voicing):
    notes=(0,2,4,5,7,9,11)
    def at(degree): return (degree//7)*12+notes[degree%7]
    anchor=min(range(-21,85),key=lambda degree:(abs(at(degree)-midi),at(degree)))
    degrees,octaves=DEGREES[voicing]
    return [at(anchor+d)-at(anchor)+12*o for d,o in zip(degrees,octaves)]


def events_and_reference(source, mode, voicing, impulse=False):
    events=[]; desired=[[],[],[]]; previous=None; last=57.; previous_targets=None
    degrees,octaves=DEGREES[voicing]
    if mode==2: events.append((0,0,"H",(0,0,0x0ab5,*degrees,*octaves)))
    for frame in source["reference"]["grid"]:
        sample=frame["sample"]; hz=frame["f0_hz"] or 0.
        if mode==0: events.append((sample,sample,"P",(hz,1 if frame["voiced"] else 0,int(frame["voiced"]),sample,sample)))
        if frame["voiced"]:
            last=69+12*math.log2(hz/440)
            shifts=(0,0,0) if impulse else VOICINGS[voicing]
            targets=[last+shift for shift in shifts]
            if mode in (0,1) and targets!=previous_targets:
                events.append((sample,sample,"T",(*targets,7))); previous_targets=targets
            midi_targets=[math.floor(value+.5) for value in targets]
            if mode==3 and midi_targets!=previous:
                if previous is not None:
                    for note in previous: events.append((sample,sample,"M",(0x80,note,0)))
                for note in midi_targets: events.append((sample,sample,"M",(0x90,note,100)))
                previous=midi_targets
        else: targets=[last+shift for shift in VOICINGS[voicing]]
        expected_shifts=scale_shift(last,voicing) if mode==2 else None
        for voice in range(3):
            target=last+expected_shifts[voice] if mode==2 else previous[voice] if mode==3 and previous else targets[voice]
            desired[voice].append(dict(frame,f0_hz=440*2**((target-69)/12) if frame["voiced"] else None))
    return sorted(events,key=lambda event:event[0]),desired


def trials(quick=False):
    for rate in ((48000,) if quick else (44100,48000)):
        for engine,window,hop in (CONFIGS[::4] if quick else CONFIGS):
            for profile in (0,1):
                for policy in (0,1):
                    for mode in ((0,3) if quick else range(4)):
                        for voicing in (("mixed",) if quick else VOICINGS):
                            yield rate,engine,window,hop,profile,policy,mode,voicing,False
                    yield rate,engine,window,hop,profile,policy,0,"upper",True


def render(build, case, source, trial, blocks="128"):
    rate,engine,window,hop,profile,policy,mode,voicing,impulse=trial
    case.mkdir(parents=True,exist_ok=False)
    events,desired=events_and_reference(source,mode,voicing,impulse)
    event_path=case/"events.txt"
    with event_path.open("x") as stream:
        for available,sample,kind,values in events:
            stream.write(f"{available} {sample} {kind} "+" ".join(format(value,".17g") for value in values)+"\n")
    settings={"rate":rate,"engine":engine,"window":window,"hop":hop,"reserve_profile":profile,"treatment":policy,"mode":mode,"voicing":voicing,
              "lead_routes":["direct","aligned"],"voices":3,"lead_gain":1,"harmony_gain_each":1/3,"ramp_semitones_per_second":2400,"crossfade_ms":10}
    write_json(case/"settings.json",settings)
    # Persist/reload the exact explicit stopped preset; no offline-bounce quality switch.
    require(load_json(case/"settings.json")==settings,"Settings round-trip changed processing")
    binary=build/("voxide_"+engine+"_interaction")
    command=[str(binary),str(rate),str(window),str(hop),str(mode),str(policy),str(profile),str(event_path),str(case/"render"),blocks,str(round(rate*.6))]
    data=array.array("f",source["values"]).tobytes()
    run=subprocess.run(command,input=data,capture_output=True)
    (case/"stdout.txt").write_bytes(run.stdout); (case/"stderr.txt").write_bytes(run.stderr)
    write_json(case/"invocation.json",{"command":command,"return_code":run.returncode,"source_sha256":source["sha256"],"input_float32_sha256":hashlib.sha256(data).hexdigest()})
    record={"case":case.name,**settings,"impulse":impulse,"status":"rendered" if run.returncode==0 else "native_failed"}
    if run.returncode: return record
    native=load_json(case/"render-native.json")
    require(native["compiled_source_identity"]==identity() and native["profile"]=="Release" and not native["sanitizer"] and native["audit_available"],"Stale, sanitized or unaudited research binary")
    require((native["sample_rate"],native["window"],native["hop"],native["mode"],native["treatment"],native["reserve_profile"])
            ==(rate,window,hop,mode,policy,profile),"Native settings identity mismatch")
    require(native["source_frames"]==len(source["values"]) and native["output_frames"]==len(source["values"])+round(rate*.6),"Input/output duration mismatch")
    output={}
    for channel in CHANNELS:
        values,payload=read_float(case/("render-"+channel+".f32"))
        require(len(values)==native["output_frames"],"Truncated interaction stem")
        write_float_wav(case/(channel+".wav"),rate,payload); output[channel]=values
    record["native"]=native
    record["measurements"]=measure(native,output,source,desired,case,load_contract(),impulse)
    return record


def measure(native, output, source, desired, case, policy, impulse=False):
    rate=native["sample_rate"]; offset=native["latency_samples"]; frames=native["source_frames"]
    values=array.array("f",source["values"])
    lead={}
    for name,delay in (("lead-direct",0),("lead-aligned",offset)):
        expected=[0.]*delay+list(values)+[0.]*(native["output_frames"]-frames-delay)
        errors=[float(a)-b for a,b in zip(output[name],expected)]
        lead[name]={"delay_samples":delay,"max_abs":max(map(abs,errors),default=0),"rms":math.sqrt(sum(x*x for x in errors)/len(errors))}
    result={"lead_null":lead,"callback":callback_metrics(read_csv(case/"render-callbacks.csv"),rate,True,policy["quality"],native["output_frames"]),
            "peaks":{name:max(map(abs,audio),default=0) for name,audio in output.items()},"voices":[],"regions":[],
            "maximum_adjacent_steps":{name:max((abs(float(b)-a) for a,b in zip(audio,audio[1:])),default=0) for name,audio in output.items()}}
    for voice in range(3):
        item={"voice":voice,"pitch":reference_pitch_measurements(output["voice"+str(voice+1)],desired[voice][::5],1,offset,frames,rate,
                window=8192,provenance="Analytic desired three-voice target, not tracker truth or human references; centered observer may span transitions")}
        item["pitch"]["observer_hop_ms"]=50
        if impulse:
            try: item["unity_delay_samples"]=measure_unity_delay(values,output["native"+str(voice+1)],rate)["delay_samples"]
            except ValueError as error: item["unity_delay_status"]="unobservable"; item["reason"]=str(error)
        result["voices"].append(item)
    for region in source["reference"]["regions"]:
        begin,end=region["begin"]+offset,region["end"]+offset
        source_audio=values[region["begin"]:region["end"]]
        source_rms=math.sqrt(sum(x*x for x in source_audio)/len(source_audio))
        rms={name:math.sqrt(sum(float(x)**2 for x in audio[begin:end])/(end-begin)) for name,audio in output.items()}
        result["regions"].append({**region,"aligned_rms":rms,"source_rms":source_rms,
            "aligned_sum_to_source_rms":rms["sum-aligned"]/source_rms if source_rms>0 else None,
            "scope":"Complete-blend/stem energy proxy, not consonant intelligibility or perceptual acceptance; direct route retains native timing"})
        if region["name"] in ("s","sh","plosive","silence"):
            proxy={"region":region["name"],"status":"observed" if end-begin>=8192 else "insufficient_observer_support","channels":{}}
            if end-begin>=8192:
                center=(begin+end)//2
                for name in ("voice1","voice2","voice3","sum-aligned"):
                    proxy["channels"][name]=estimate_output_pitch(output[name][center-4096:center+4096],rate)
            result.setdefault("unvoiced_pitch_proxies",[]).append(proxy)
    timeline=read_csv(case/"render-telemetry.csv")
    controls=[row for row in timeline if int(row["kind"])==0]
    previous={}; bad=[]; midi=[]
    for row in controls:
        v=int(row["voice"]); wall=int(row["wall"]); source_at=int(row["source"]); shift=float(row["applied_shift"])
        require(-24<=shift<=24 and int(row["frame_available"])<=wall+1,"Invalid shift or future analysis used")
        if v in previous:
            old=previous[v]; require(abs(shift-float(old["applied_shift"]))<=2400*max(0,source_at-int(old["source"]))/rate+1e-6,"Unbounded API ratio transition")
        previous[v]=row
        if source_at>=int(row["requested"]): midi.append((wall-int(row["requested"])+1)*1000/rate)
        if int(row["available"])>wall+1: bad.append(row)
    require(not bad,"Applied a control before its availability")
    result["control_observations"]={"records":len(controls),"latest_request_age_ms_p95":percentile(midi,.95) if midi else None,
        "scope":"Age of latest music request at API call, NOT event response/settling or <5ms MIDI qualification; full requests/application chronology retained"}
    requests={int(row["requested"]):row for row in timeline if int(row["kind"])==2 and int(row["request_kind"])!=0}
    response=[]
    for sample,request in requests.items():
        for voice in range(3):
            application=next((row for row in controls if int(row["voice"])==voice and int(row["source"])>=sample and int(row["requested"])>=sample),None)
            status="missing" if application is None else "coalesced_with_later_request" if int(application["requested"])>sample else "applied"
            response.append({"requested_source_sample":sample,"voice":voice,"kind":int(request["request_kind"]),"status":status,
                             "request_to_api_ms":(int(application["wall"])+1-int(request["available"]))*1000/rate if application else None})
    result["request_response"]={"observations":response,"scope":"Actual request availability to first native API application, including analysis/control-lag/quantum delay. Coalesced requests are not on-time passes; audible response remains separate."}
    callback_rows=read_csv(case/"render-callbacks.csv")
    audible=[]; request_items=sorted(requests.items())
    for index,(sample,request) in enumerate(request_items):
        stop=request_items[index+1][0] if index+1<len(request_items) else frames
        for voice in result["voices"]:
            found=observed_dwell(voice["pitch"]["observations"],sample,stop,int(request["available"]),offset,rate,callback_rows)
            audible.append({"requested_source_sample":sample,"voice":voice["voice"],"status":"measured" if found else "unresolved","measurement":found})
    result["audible_response"]={"observations":audible,"window_samples":8192,"observer_hop_ms":50,"minimum_correct_dwell_ms":20,
        "scope":"Conservative independent output observer: completed sampled dwell + centered-window support + fixed delivery + callback return. Not intrinsic engine or physical monitoring latency. All unresolved observations retained."}
    result["gates"]={
        "lead_null":"pass" if all(row["max_abs"]<=policy["deterministic_tolerance"]["max_abs"] and row["rms"]<=policy["deterministic_tolerance"]["rms"] for row in lead.values()) else "fail",
        "fixed_delivery":"pass" if all(not row["underflows"] and not row["late_samples"] for row in native["voices"]) and not native["missing_metadata"] and not native["fifo_overflow"] else "fail",
        "control_chronology":"pass" if not native["bad_events"] and not native["late_controls"] and not native["telemetry_dropped"] else "fail",
        "allocation":"pass" if result["callback"]["allocation_calls"]==0 else "fail",
        "callback_budget":"pass" if result["callback"]["occupancy_target_met_on_this_run_only"] else "fail",
        "midi_state_response":"not_applicable_no_midi" if not any(row["kind"]==2 for row in response) else "pass" if all(row["status"]=="applied" and row["request_to_api_ms"]<=policy["timing_ms"]["midi_target"] for row in response if row["kind"]==2) else "fail",
        "headroom":"pass" if result["peaks"]["sum-aligned"]<1 and result["peaks"]["sum-direct"]<1 else "fail",
        "unity_alignment":"not_applicable_nonunity_suite" if not impulse else "pass" if all(row.get("unity_delay_samples")==offset for row in result["voices"]) else "fail",
        "tail":"pass" if native["unrendered_finish_peak"]<=1e-6 else "fail",
        "human_articulation":"pending","host_monitoring":"pending"}
    return result


def observed_dwell(observations,start,stop,request_available,offset,rate,callbacks):
    """Missing/unvoiced/uncertain grid points cannot bridge a sampled dwell."""
    began=None; previous=None
    for observation in observations:
        center=observation["source_sample"]
        if not start<=center<stop: continue
        if previous is not None and center-previous!=round(rate*.05): began=None
        previous=center
        good=observation["error_cents"] is not None and abs(observation["error_cents"])<=25
        if not good: began=None
        elif began is None: began=center
        elif center-began>=round(rate*.02):
            observer_end=center+offset+4096
            arrival=next((int(row["begin"])+int(row["frames"]) for row in callbacks if int(row["begin"])+int(row["frames"])>=observer_end),None)
            return {"observer_end":observer_end,"available_sample":arrival,"request_to_observed_ms":(arrival-request_available)*1000/rate} if arrival is not None else None
    return None


def summarize(cases):
    groups={}
    for case in cases:
        key=(case["engine"],case["window"],case["rate"],case["reserve_profile"],case["treatment"],case["mode"])
        group=groups.setdefault(key,{"engine":key[0],"window":key[1],"rate":key[2],"profile":key[3],"policy":key[4],"mode":key[5],
            "cases":0,"failed_cases":{},"unresolved_pitch_groups":[],"unresolved_audible_observations":[],"callback_occupancy_p999_max":0.,"underflows":0})
        group["cases"]+=1
        if case["status"]!="rendered": group["failed_cases"].setdefault("native_render",[]).append(case["case"]); continue
        m=case["measurements"]
        for gate,status in m["gates"].items():
            if status=="fail": group["failed_cases"].setdefault(gate,[]).append(case["case"])
        repeat=case.get("partition_repeat")
        if repeat and (repeat["status"]!="compared" or any(not row["within_tolerance"] for row in repeat["channels"].values())):
            group["failed_cases"].setdefault("native_partition_repeat",[]).append(case["case"])
        for row in m.get("audible_response",{}).get("observations",[]):
            if row["status"]!="measured": group["unresolved_audible_observations"].append(dict(row,case=case["case"]))
        for voice in m["voices"]:
            stable=voice["pitch"]["groups"]["stable"]
            if stable["frames"] and (stable["within_25c_fraction"] is None or stable["within_25c_fraction"]<.99):
                group["failed_cases"].setdefault("stable_pitch",[])
                if case["case"] not in group["failed_cases"]["stable_pitch"]: group["failed_cases"]["stable_pitch"].append(case["case"])
            if not stable["frames"]: group["unresolved_pitch_groups"].append({"case":case["case"],"voice":voice["voice"],"reason":"no stable supported truth frames"})
        group["callback_occupancy_p999_max"]=max(group["callback_occupancy_p999_max"],m["callback"]["occupancy_p999"])
        group["underflows"]+=sum(row["underflows"] for row in case["native"]["voices"])
    return list(groups.values())


def research(build,quick=False):
    directory=ROOT/"build/interaction-research"/stamp(); directory.mkdir(parents=True,exist_ok=False)
    p=provenance(build,directory)
    report={"schema":"voxide.interaction-research.v1","status":"running","quick_incomplete_coverage":quick,"cases":[],"provenance":"provenance.json",
            "scope":"PR05 three-voice research, not engine choice or product/Logic/live acceptance"}
    try:
        validate_fixtures(FIXTURES)
        report["instrument_calibration"]=calibrate_instruments(quick)
        require(report["instrument_calibration"]["status"]=="pass","Independent instrument calibration failed")
        sources_dir=directory/"sources"; sources_dir.mkdir()
        inputs={(rate,impulse):fixture(sources_dir,rate,impulse) for rate in ((48000,) if quick else (44100,48000)) for impulse in (False,True)}
        for index,trial in enumerate(trials(quick)):
            source=inputs[(trial[0],trial[-1])]
            require(sha256(source["path"])==source["sha256"],"Input source changed")
            case=directory/f"case-{index:04d}"
            record=render(build,case,source,trial)
            if record["status"]=="rendered" and (index==0 or (trial[6]==0 and trial[7]=="mixed" and not trial[-1])):
                repeat=render(build,case/"mixed-partition-repeat",source,trial,blocks="32,64,128,257,512,1024")
                comparison={"status":"compared" if repeat["status"]=="rendered" else "native_failed","channels":{}}
                if repeat["status"]=="rendered":
                    require(all(a["native_input_hash"]==b["native_input_hash"] and a["control_hash"]==b["control_hash"] for a,b in zip(record["native"]["voices"],repeat["native"]["voices"])),"Partitions changed engine input/control chronology")
                    for name in CHANNELS:
                        a,_=read_float(case/("render-"+name+".f32")); b,_=read_float(case/"mixed-partition-repeat"/("render-"+name+".f32"))
                        maximum=max((abs(float(x)-y) for x,y in zip(a,b)),default=0)
                        rms=math.sqrt(sum((float(x)-y)**2 for x,y in zip(a,b))/len(a))
                        comparison["channels"][name]={"max_abs":maximum,"rms":rms,"within_tolerance":len(a)==len(b) and maximum<=1e-6 and rms<=1e-7}
                record["partition_repeat"]=comparison
            report["cases"].append(record)
            if index%25==0: print("Interaction cases:",index+1,flush=True)
        verify_provenance(build,p)
        require(len(report["cases"])==sum(1 for _ in trials(quick)),"Incomplete interaction matrix")
        report["source_build_unchanged"]=True; report["configuration_summary"]=summarize(report["cases"])
        report["status"]="research_complete_not_product_pass"
    except Exception as error:
        report["status"]="fail"; report["error"]=str(error); raise
    finally:
        write_json(directory/"report.json",report); print("Interaction evidence:",directory/"report.json",flush=True)
    return directory/"report.json"


def check(args):
    directory=ROOT/"build/interaction-checks"/stamp(); directory.mkdir(parents=True,exist_ok=False)
    files=source_fingerprint()
    report={"schema":"voxide.interaction-check.v1","status":"running","files":files,"steps":[],"profiles":[],"scope":"Research engineering, not all candidate/product gates passing"}
    def run(label,command,env=None):
        step={"label":label,"command":command}; report["steps"].append(step)
        with (directory/(label+".log")).open("x") as log:
            result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=env)
        step["exit_code"]=result.returncode
        require(not result.returncode,(directory/(label+".log")).read_text())
    try:
        for profile in (("debug","release","asan","tsan") if args.full else ("release",)):
            build=ROOT/"build"/("interaction-"+profile); report["profiles"].append(profile)
            sanitizer={"asan":"address","tsan":"thread"}.get(profile,"")
            run(profile+"-configure",["cmake","-S","InteractionEvaluation","-B",str(build),"-DCMAKE_BUILD_TYPE="+("Release" if profile=="release" else "Debug"),
                "-DVOXIDE_SANITIZER="+sanitizer,"-DVOXIDE_OFFLINE=ON","-DPython3_EXECUTABLE="+sys.executable])
            run(profile+"-build",["cmake","--build",str(build),"--parallel",str(args.jobs)])
            env=dict(os.environ)
            if profile=="asan": env["ASAN_OPTIONS"]="detect_leaks=0:halt_on_error=1"
            if profile=="tsan": env["TSAN_OPTIONS"]="halt_on_error=1"
            run(profile+"-test",["ctest","--test-dir",str(build),"--output-on-failure","--no-tests=error"],env)
        report["research"]=str(research(ROOT/"build/interaction-release",args.quick).relative_to(ROOT))
        require(source_fingerprint()==files,"Source changed during qualification")
        report["source_unchanged"]=True; report["status"]="pass"
    except Exception as error:
        report["status"]="fail"; report["error"]=str(error); raise
    finally:
        write_json(directory/"report.json",report); print("Interaction check evidence:",directory/"report.json")


def private(build, manifest):
    """Explicit development only; all source identities/derived evidence stay private."""
    from io import BytesIO
    snapshot=manifest.read_bytes(); data=json.loads(snapshot)
    selected=select_sources(manifest,split="development")
    require(manifest.read_bytes()==snapshot,"Private manifest changed during permission validation")
    directory=ROOT/"evaluation/pr-05"/stamp(); directory.mkdir(parents=True,exist_ok=False)
    p=provenance(build,directory); policy=load_contract()
    report={"schema":"voxide.private-interaction.v1","status":"running","sources":[],"corpus_sha256":hashlib.sha256(snapshot).hexdigest(),"provenance":"provenance.json"}
    try:
        for source in data["sources"]:
            if source["id"] not in selected: continue
            record={"source_id":source["id"],"status":"pending_human_references","source_sha256":source["audio"]["sha256"]}
            report["sources"].append(record)
            if len(source.get("annotations",[]))!=2: continue
            path=contained(manifest.parent,source["audio"]["path"]); encoded=path.read_bytes()
            require(hashlib.sha256(encoded).hexdigest()==source["audio"]["sha256"],"Private source changed after selection")
            info,values=read_wav_bytes(encoded); pcm_info,pcm=read_pcm_stream(BytesIO(encoded)); digest=pcm_sha256(pcm_info,pcm)
            refs=[]
            for annotation in source["annotations"]:
                content=contained(manifest.parent,annotation["path"]).read_bytes()
                require(hashlib.sha256(content).hexdigest()==annotation["sha256"],"Private reference changed after selection")
                refs.append(validate_annotation(json.loads(content),source["id"],info,digest,policy))
            if any(ref["origin"]!="human" or ref.get("review_status")!="completed" for ref in refs) or compare_annotations(*refs,policy=policy)["status"]!="agreement": continue
            grid=[]
            for a,b in zip(refs[0]["grid"],refs[1]["grid"]):
                voiced=a["voiced"] and b["voiced"]; uncertain=a["uncertain"] or b["uncertain"]
                grid.append({"sample":a["sample"],"voiced":voiced,"uncertain":uncertain,"stable":a["stable"] and b["stable"],
                             "f0_hz":math.sqrt(a["f0_hz"]*b["f0_hz"]) if voiced and not uncertain else None})
            if not any(row["voiced"] and not row["uncertain"] for row in grid): continue
            # Uncertain oracle frames do not invent F0 or force ambiguous targets.
            for row in grid:
                if row["uncertain"]: row["voiced"]=False
            fixture_source={"path":path,"sha256":source["audio"]["sha256"],"values":values,
                            "reference":{"grid":grid,"regions":[{"name":"private-vocal","begin":0,"end":len(values)}]}}
            cases=[]
            for engine,window,hop in CONFIGS:
                for treatment in (0,1):
                    for mode in range(4):
                        trial=(info["sample_rate"],engine,window,hop,1,treatment,mode,"mixed",False)
                        case=directory/("source-"+str(len(report["sources"]))+"-"+str(len(cases)))
                        result=render(build,case,fixture_source,trial)
                        # The same observer can measure reviewed references but is
                        # not itself human truth or an expressive-accuracy guarantee.
                        if result["status"]=="rendered":
                            for voice in result["measurements"]["voices"]:
                                voice["pitch"]["scope"]="Two completed registered agreeing human references; sparse offline observer, not listening acceptance"
                        cases.append(result)
            require(sha256(path)==source["audio"]["sha256"],"Private source changed during render")
            record.update(status="reference_ready",cases=cases,successful_renders=sum(case["status"]=="rendered" for case in cases),
                          failed_renders=sum(case["status"]!="rendered" for case in cases),annotation_sha256=[a["sha256"] for a in source["annotations"]])
        verify_provenance(build,p)
        report["source_build_unchanged"]=True; report["status"]="development_complete_not_product_pass"
    except Exception as error:
        report["status"]="fail"; report["error"]=str(error); raise
    finally: write_json(directory/"private-report.json",report)
    print(json.dumps({"sources":len(report["sources"]),"reference_ready_sources":sum(s["status"]=="reference_ready" for s in report["sources"]),
                      "evidence":str((directory/"private-report.json").relative_to(ROOT)),"scope":"Development only; no holdout or fabricated vocal grades"},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("check","research","private"))
    parser.add_argument("--full",action="store_true"); parser.add_argument("--quick",action="store_true")
    parser.add_argument("--jobs",type=int,default=6); parser.add_argument("--offline",action="store_true",help="All interaction builds are offline")
    parser.add_argument("--development-corpus",type=Path)
    args=parser.parse_args(); require(args.jobs>0,"Positive jobs required")
    if args.command=="check": check(args)
    elif args.command=="research": research(ROOT/"build/interaction-release",args.quick)
    else:
        require(args.development_corpus is not None,"Explicit private development corpus required")
        manifest=args.development_corpus.resolve()
        require(manifest.is_relative_to(ROOT/"evaluation"),"Private corpus must stay under ignored evaluation/")
        private(ROOT/"build/interaction-release",manifest)


if __name__=="__main__": main()
