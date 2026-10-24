#!/usr/bin/env python3
"""Bounded architecture falsification, never an AU/device or product acceptance run."""
import argparse
import array
import bisect
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys

from check import source_fingerprint
from evaluation_common import ROOT, require, sha256, write_json, read_wav_bytes
from evaluation_contract import load_contract
from evaluation_metrics import cents
from engine_evaluation import verified_dependencies
from engine_metrics import estimate_output_pitch, read_csv, read_float
from interaction_evaluation import stamp

BASELINE=ROOT/"build/interaction-research/20261023T160456Z-ffcc2998"
PROTOCOL=ROOT/"docs/evidence/architecture/protocol.json"
FILES=sorted(["ArchitectureEvaluation/"+name for name in ("CMakeLists.txt","Probe.cpp","SignalsmithAdapter.cpp","TraceAllocations.cpp","TraceAllocations.h")]+
             ["EngineEvaluation/EngineAdapter.cpp","EngineEvaluation/EngineAdapter.h","Source/DSP/PitchTracker.cpp","Source/DSP/PitchTracker.h",
              "Source/DSP/HarmonySelector.cpp","Source/DSP/HarmonySelector.h","Source/Tests/AllocationAudit.cpp","Source/Tests/AllocationAudit.h","cmake/engine-dependencies.json"])


def identity():
    return hashlib.sha256("".join(name+"|"+sha256(ROOT/name)+"\n" for name in FILES).encode()).hexdigest()


def positive_crossings(values):
    # Deliberately independent of FFT/autocorrelation and no expected-F0 argument.
    return [i-1-float(a)/(float(b)-a) for i,(a,b) in enumerate(zip(values,values[1:]),1) if a<=0<b]


def period_pitch(values,rate):
    crossings=positive_crossings(values)
    periods=[b-a for a,b in zip(crossings,crossings[1:])]
    if len(periods)<2: return {"hz":None,"reason":"insufficient_complete_periods"}
    mean=statistics.mean(periods); variation=statistics.pstdev(periods)/mean
    hz=rate/mean
    if not 16<=hz<=5000 or variation>.02: return {"hz":None,"reason":"aperiodic_or_multiple_crossings","period_cv":variation}
    # A narrow applicability screen, NOT a vocal pitch estimator: reject windows
    # that cannot be explained mostly by one free-frequency sinusoid.
    energy=sum(float(x)**2 for x in values)
    sine=cosine=ss=cc=sc=0.
    for i,x in enumerate(values):
        s=math.sin(2*math.pi*hz*i/rate); c=math.cos(2*math.pi*hz*i/rate)
        sine+=x*s; cosine+=x*c; ss+=s*s; cc+=c*c; sc+=s*c
    determinant=ss*cc-sc*sc
    a=(sine*cc-cosine*sc)/determinant if determinant>0 else 0
    b=(cosine*ss-sine*sc)/determinant if determinant>0 else 0
    explained=(a*sine+b*cosine)/energy if energy>1e-15 else 0
    return {"hz":hz if explained>=.85 else None,"period_hz":hz,"period_cv":variation,"sine_energy_fraction":explained,
            "reason":"measured_sine_like" if explained>=.85 else "not_sine_like_not_adjudicated"}


def observed_response(values,rate,target,event,packets,offset=0,stop=None):
    """Restricted periodic-control observer, completed periods+dwell+arrival only.

    It cannot qualify generic vocal output. Incorrect/ambiguous output is never
    forced through an expected-frequency search. Low-period support can make a
    tight response ceiling unobservable; calibration reports this explicitly.
    """
    crossings=positive_crossings(values)
    began=None; previous=None
    for a,b in zip(crossings,crossings[1:]):
        if a-offset<event: continue
        if stop is not None and b-offset>=stop: break
        hz=rate/(b-a)
        good=16<=hz<=5000 and abs(cents(hz,target))<=25
        if not good: began=None; previous=None; continue
        if began is None: began=a; previous=b; continue
        previous=b
        if previous-began<round(rate*.020): continue
        end=math.ceil(b)+1
        window=values[max(0,math.floor(began)):end]
        estimate=period_pitch(window,rate)
        if estimate["hz"] is None or abs(cents(estimate["hz"],target))>25: continue
        arrival=next((int(row["wall"]) for row in packets if int(row["first"])<=end-1<int(row["first"])+int(row["count"])),None)
        if arrival is not None:
            return {"status":"measured_analytic_only","completed_output_sample":end,"available_sample":arrival,"ms":(arrival-event)*1000/rate,"estimate":estimate}
    return {"status":"unresolved","reason":"no_supported_correct_completed_dwell"}


def tone(rate,hz,seconds=.8):
    return array.array("f",(.1*math.sin(2*math.pi*hz*i/rate) for i in range(round(rate*seconds))))


def calibrate():
    result={"steady":[],"response":[],"scope":"Analytic sine-only independent cross-check, not a replacement vocal/listening truth instrument"}
    for rate in (44100,48000):
        for hz in (82.4068892282175/4,82.4068892282175,220,1046.5022612023945,1046.5022612023945*4):
            samples=tone(rate,hz); segment=samples[rate//4:rate//4+8192]
            cross=period_pitch(segment,rate); nacf=estimate_output_pitch(segment,rate)
            good=cross["hz"] is not None and nacf["f0_hz"] is not None and abs(cents(cross["hz"],hz))<=25 and abs(cents(nacf["f0_hz"],hz))<=25
            result["steady"].append({"rate":rate,"hz":hz,"period":cross,"nacf":nacf,"pass":good})
            require(good,"Independent steady calibration failed")
        for delay_ms in (0,80):
            event=round(rate*.2); delay=round(rate*delay_ms/1000); change=event+delay
            audio=array.array("f",(.1*math.sin(2*math.pi*(220 if i<change else 330)*(i-change)/rate) for i in range(rate//2)))
            packets=[{"first":begin,"count":min(32,len(audio)-begin),"wall":min(begin+32,len(audio))} for begin in range(0,len(audio),32)]
            response=observed_response(audio,rate,330,event,packets)
            require(response["status"]=="measured_analytic_only" and delay_ms+20<=response["ms"]<=delay_ms+40,"Response observer calibration failed")
            result["response"].append({"rate":rate,"known_delay_ms":delay_ms,**response,"correct_side_of_50ms_ceiling":(response["ms"]<=50)==(delay_ms==0)})
        wrong=tone(rate,660,.5)
        require(observed_response(wrong,rate,330,0,[{"first":0,"count":len(wrong),"wall":len(wrong)}])["status"]=="unresolved","Wrong octave passed response observer")
        require(period_pitch([0.]*8192,rate)["hz"] is None,"Silence passed pitch observer")
    result["status"]="pass"
    return result


def snapshot(build,directory):
    files=source_fingerprint()
    binaries={name:sha256(build/name) for name in ("architecture_accelerate","architecture_builtin","architecture_rubberband","libarchitecture_trace.dylib")}
    p={"files":files,"binaries":binaries,"identity":identity(),"dependencies":verified_dependencies(build/"engines"),"cache":sha256(build/"CMakeCache.txt"),
       "protocol":sha256(PROTOCOL),"git_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"platform":platform.platform(),
       "python":sys.version,"compiler":subprocess.check_output(["clang","--version"],text=True).strip(),"sdk":subprocess.check_output(["xcrun","--show-sdk-version"],text=True).strip()}
    for name,digest in files.items():
        target=directory/"source"/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/name,target); require(sha256(target)==digest,"Archival source race")
    target=directory/"binaries"; target.mkdir()
    for name,digest in binaries.items(): shutil.copyfile(build/name,target/name); require(sha256(target/name)==digest,"Archival binary race")
    for name in ("CMakeCache.txt","compile_commands.json"): shutil.copyfile(build/name,target/name)
    verify(build,p); write_json(directory/"provenance.json",p); return p


def verify(build,p):
    require(source_fingerprint()==p["files"] and identity()==p["identity"],"Source changed during architecture batch")
    require(all(sha256(build/name)==digest for name,digest in p["binaries"].items()) and sha256(build/"CMakeCache.txt")==p["cache"],"Native build changed during batch")
    require(verified_dependencies(build/"engines")==p["dependencies"],"Canonical dependency sources changed")


def native(build,directory,name,backend,rate,window,hop,values,events,hold=0,warm=0,trace=0,mode=0):
    case=directory/name; case.mkdir()
    source=case/"source.f32"; source.write_bytes(array.array("f",values).tobytes()); eventfile=case/"events.txt"
    eventfile.write_text("".join(" ".join(format(v,".17g") for v in (sample,hz,*shifts))+"\n" for sample,hz,shifts in events))
    command=[str(build/("architecture_"+backend)),str(rate),str(window),str(hop),str(hold),str(eventfile),str(case/"render"),str(warm),str(trace),str(mode),str(source)]
    run=subprocess.run(command,capture_output=True)
    (case/"stdout.txt").write_bytes(run.stdout); (case/"stderr.txt").write_bytes(run.stderr)
    row={"case":name,"backend":backend,"rate":rate,"window":window,"hop":hop,"hold":hold,"warm":warm,"trace":trace,"mode":mode,"command":command,
         "source_sha256":sha256(source),"events_sha256":sha256(eventfile),"return_code":run.returncode,"status":"rendered" if not run.returncode else "native_failed"}
    write_json(case/"invocation.json",row)
    if run.returncode: return row
    metadata=json.loads((case/"render.json").read_text())
    require(metadata["identity"]==identity() and metadata["build"]=="Release" and not metadata["sanitizer"] and metadata["audit_available"],"Stale/sanitized/unaudited architecture binary")
    require(not run.stderr,"Native diagnostics require investigation, not suppression")
    row["native"]=metadata
    if any(v["nonfinite"] for v in metadata["voices"]):
        row["status"]="native_nonfinite"
        row["scope"]="Unchanged raw nonfinite stems retained; no playable WAV or quality pass generated"
        write_json(case/"analysis.json",row)
        return row
    row["allocation_calls"]=sum(int(r["calls"]) for r in read_csv(case/"render-allocations.csv"))
    row["allocation_quantums"]=[r for r in read_csv(case/"render-allocations.csv") if int(r["calls"])]
    packets=read_csv(case/"render-packets.csv"); controls=read_csv(case/"render-controls.csv")
    offsets=metadata["offset"]+metadata["trim"]
    row["delivery"]={}; row["steady"]=[]; row["response"]=[]; row["api_response"]=[]
    for control in controls:
        require(int(control["frame_available"])<=int(control["wall"]),"Unavailable frame consumed")
        if mode==1: require(int(control["frame_end"])<=int(control["source"])+1 or int(control["frame_end"])==0,"Future source frame used")
        if mode!=2: require(int(control["request"])<=max(0,int(control["source"])),"Premature musical control")
    for voice in range(3):
        audio,_=read_float(case/("render-voice"+str(voice)+".f32"))
        timeline=[r for r in packets if int(r["voice"])==voice]
        starts=[int(r["first"]) for r in timeline]
        # Primary source ends before the explicitly supplied 1/3-second zero tail.
        # The tail and finalization remain captured; neither can conceal missing
        # PRIMARY output or its actual native availability.
        delays=[]; missing=0
        for sample in range(0,len(values)-rate//3,32):
            index=sample+offsets
            position=bisect.bisect_right(starts,index)-1
            packet=timeline[position] if position>=0 and index<starts[position]+int(timeline[position]["count"]) else None
            if packet is None: missing+=1
            else: delays.append((int(packet["wall"])-sample)*1000/rate)
        row["delivery"][str(voice)]={"max_ms":max(delays) if delays else None,"missing":missing,"within_15ms":not missing and bool(delays) and max(delays)<=15,
                                      "scope":"Sampled native availability including native quantum return; not host callback/device or shifted envelope latency"}
        if mode!=2:
            # Long steady plateaus only. Both independently measured estimates
            # are retained; crossing-inapplicable does not become a quality pass.
            for index,(sample,hz,shifts) in enumerate(events):
                stop=events[index+1][0] if index+1<len(events) else len(values)-round(rate*.2)
                center=(sample+stop)//2; begin=center+offsets-4096
                if center-sample<4096+round(rate*.05) or stop-center<4096+round(rate*.05): continue
                expected=hz*2**(shifts[voice]/12)
                segment=audio[max(0,begin):max(0,begin)+8192] if begin>=0 else []
                cross=period_pitch(segment,rate) if len(segment)==8192 else {"hz":None,"reason":"missing_output"}
                nacf=estimate_output_pitch(segment,rate) if len(segment)==8192 else {"f0_hz":None}
                row["steady"].append({"voice":voice,"sample":center,"expected_hz":expected,"period":cross,"nacf":nacf,
                                      "period_error_cents":cents(cross["hz"],expected) if cross["hz"] else None,
                                      "nacf_error_cents":cents(nacf["f0_hz"],expected) if nacf["f0_hz"] else None})
            for index,(sample,hz,shifts) in enumerate(events[1:],1):
                stop=events[index+1][0] if index+1<len(events) else len(values)-rate//3
                response=observed_response(audio,rate,hz*2**(shifts[voice]/12),sample,timeline,offsets,stop)
                row["response"].append({"voice":voice,"request":sample,**response})
                application=next((r for r in controls if int(r["voice"])==voice and int(r["request"])==sample),None)
                row["api_response"].append({"voice":voice,"request":sample,"ms":(int(application["wall"])-sample)*1000/rate if application else None})
    row["musical_state"]=read_csv(case/"render-state.csv")
    row["musical_state_scope"]="Actual PR03 selector slot changes at receipt, logged separately; diagnostic shadow state is NOT substituted for source-matched native setter or correct audible output"
    if mode==1:
        pitch=read_csv(case/"render-pitch.csv"); initial_hz=events[0][1]
        correct=next((f for f in pitch if int(f["voiced"]) and float(f["hz"])>0 and abs(cents(float(f["hz"]),initial_hz))<=25),None)
        row["recognition"]={"cold_initial_ms":int(correct["available"])*1000/rate if correct else None,
                            "ceiling_ms":50 if initial_hz<150 else 30,"scope":"First correct voiced decision from source onset zero; single analytic trial, not P95 or continuous-transition qualification"}
    write_json(case/"analysis.json",row)
    return row


def compare(directory,a,b):
    if a["status"]!="rendered" or b["status"]!="rendered": return {"status":"native_failed"}
    hashes=all(x["input_hash"]==y["input_hash"] and x["control_hash"]==y["control_hash"] for x,y in zip(a["native"]["voices"],b["native"]["voices"]))
    channels=[]
    for voice in range(3):
        x,_=read_float(directory/a["case"]/("render-voice"+str(voice)+".f32")); y,_=read_float(directory/b["case"]/("render-voice"+str(voice)+".f32"))
        length=min(len(x),len(y)); maximum=max((abs(float(u)-v) for u,v in zip(x,y)),default=0)
        rms=math.sqrt(sum((float(u)-v)**2 for u,v in zip(x,y))/length) if length else None
        channels.append({"voice":voice,"same_length":len(x)==len(y),"max_abs":maximum,"rms":rms,"pass":len(x)==len(y) and maximum<=1e-6 and rms is not None and rms<=1e-7})
    return {"a":a["case"],"b":b["case"],"hashes_match":hashes,"channels":channels,"status":"pass" if hashes and all(r["pass"] for r in channels) else "fail"}


def baseline_crosscheck():
    report=json.loads((BASELINE/"report.json").read_text()); rows=[]; dependencies={name:sha256(BASELINE/name) for name in ("report.json","sources/48000-suite.json")}
    # Exactly one 48kHz oracle/native/mix/mixed case per pinned configuration,
    # two centered windows in each of the three steady regions, all three voices.
    regions=json.loads((BASELINE/"sources/48000-suite.json").read_text())["regions"][:3]
    for case in report["cases"]:
        if (case["rate"],case["reserve_profile"],case["treatment"],case["mode"],case["voicing"],case["impulse"])!=(48000,1,0,0,"mixed",False): continue
        for voice in range(3):
            path=BASELINE/case["case"]/("render-native"+str(voice+1)+".f32"); audio,_=read_float(path); dependencies[str(path.relative_to(BASELINE))]=sha256(path)
            for region in regions:
                for fraction in (.45,.55):
                    center=round(region["begin"]+(region["end"]-region["begin"])*fraction)
                    expected_source=82.4068892282175 if region["name"]=="low-vowel" else 1046.5022612023945 if region["name"]=="high-vowel" else 220
                    expected=expected_source*2**((-24,7,24)[voice]/12)
                    start=center+case["native"]["latency_samples"]-4096; segment=audio[start:start+8192]
                    require(center-4096>=region["begin"] and center+4096<region["end"],"Crosscheck support crosses boundary")
                    cross=period_pitch(segment,48000); nacf=estimate_output_pitch(segment,48000)
                    rows.append({"case":case["case"],"engine":case["engine"],"window":case["window"],"voice":voice,"region":region["name"],"center":center,
                                 "expected_hz":expected,"nacf":nacf,"period":cross,"nacf_error_cents":cents(nacf["f0_hz"],expected) if nacf["f0_hz"] else None,
                                 "period_error_cents":cents(cross["hz"],expected) if cross["hz"] else None})
    require(len(rows)==90,"Incomplete bounded baseline crosscheck")
    return {"observations":rows,"baseline_hashes":dependencies,"scope":"90 fully supported analytic steady windows, no vocal statistics; independent sine-like period observer can abstain"}


def replay_source(directory):
    # The exact fixed native calls of a retained PR05 failing case, not a new
    # random workload chosen to make repeatability pass.
    hashes={name:sha256(BASELINE/name) for name in ("case-0002/render-native.json","case-0002/render-telemetry.csv","sources/44100-suite.wav")}
    baseline=json.loads((BASELINE/"case-0002/render-native.json").read_text())
    _,values=read_wav_bytes((BASELINE/"sources/44100-suite.wav").read_bytes())
    values=array.array("f",values); values.extend([0.]*baseline["zero_tail"]); del values[len(values)//128*128:]
    controls=read_csv(BASELINE/"case-0002/render-telemetry.csv"); groups={}
    for row in controls:
        if int(row["kind"])!=0: continue
        begin=int(row["source"])+256
        if begin not in groups: groups[begin]=[float(row["hz"]) if int(row["voiced"]) else 0,[0.]*3]
        groups[begin][1][int(row["voice"])]=float(row["applied_shift"])
    events=[(sample,hz,shifts) for sample,(hz,shifts) in sorted(groups.items())]
    require(all(sha256(BASELINE/name)==digest for name,digest in hashes.items()),"Replay source changed during loading")
    return values,events,baseline["voices"],hashes


def decision(cases):
    groups={}
    for case in cases:
        if case["case"].startswith("replay-") or case.get("trace"): continue
        key=(case["backend"],case["window"])
        group=groups.setdefault(key,{"backend":key[0],"window":key[1],"blockers":[],"case_ids":[]})
        group["case_ids"].append(case["case"])
        blockers=group["blockers"]
        if case["status"]!="rendered": blockers.append("native_nonfinite_or_failed")
        if any(v["missing"] or v["max_ms"] is None or v["max_ms"]>15 for v in case.get("delivery",{}).values()): blockers.append("live_delivery")
        if any(v["ms"] is None or v["ms"]>5 for v in case.get("api_response",[])): blockers.append("strict_native_setter_timing")
        if any(v["period_error_cents"] is not None and v["nacf_error_cents"] is not None and abs(v["period_error_cents"])>25 and abs(v["nacf_error_cents"])>25 for v in case.get("steady",[])):
            blockers.append("independently_corroborated_steady_pitch")
        if case.get("allocation_calls",0)>0: blockers.append("callback_allocations")
        recognition=case.get("recognition")
        if recognition and (recognition["cold_initial_ms"] is None or recognition["cold_initial_ms"]>recognition["ceiling_ms"]): blockers.append("cold_recognition_screen")
        group["blockers"]=sorted(set(blockers))
    survivors=[list(key) for key,group in groups.items() if not group["blockers"]]
    return {"screen_survivors_not_product_qualification":survivors,"configurations":list(groups.values()),
            "recommendation":"no_go_for_product_integration_under_tested_scope" if not survivors else "pause_for_remaining_qualification",
            "scope":"Only measured blockers are used. No universal impossibility claim; mixing-only does not rescue the live brief. No further tuning in this batch."}


def research(build):
    directory=ROOT/"build/architecture-research"/stamp(); directory.mkdir(parents=True)
    provenance=snapshot(build,directory)
    report={"schema":"voxide.architecture-results.v1","status":"running","cases":[],"comparisons":[],"pending":["human references/listening including c","formant/vocal qualification","Logic/PDC/physical monitoring"],"scope":"Bounded falsification, not product acceptance"}
    def run(name,*args,**kwargs):
        row=native(build,directory,name,*args,**kwargs); report["cases"].append(row); return row
    try:
        report["calibration"]=calibrate()
        report["baseline_crosscheck"]=baseline_crosscheck()
        timing_survivors=[]
        for rate in (44100,48000):
            for backend in ("accelerate","builtin"):
                for window,hop in ((512,128),(256,32)):
                    for hz in (82.4068892282175,220.,1046.5022612023945):
                        values=tone(rate,hz,1.1); values.extend([0.]*(rate//3))
                        run(f"steady-{rate}-{backend}-{window}-{hz:.0f}",backend,rate,window,hop,values,[(0,hz,(-24,7,24))])
                    for phase in (0,hop//2,hop-1):
                        values=tone(rate,220,1.7); values.extend([0.]*(rate//3))
                        events=[(0,220,(-12,3,7)),(round(rate*.5)+phase,220,(-5,7,12)),(round(rate*1.1)+phase,220,(-12,-7,0))]
                        row=run(f"timing-{rate}-{backend}-{window}-{phase}",backend,rate,window,hop,values,events)
                        if phase==0 and window==512:
                            hold=(512+math.ceil(rate/2/82.4068892282175)+1)+2*round(rate*.0025)
                            run(f"held-{rate}-{backend}",backend,rate,window,hop,values,events,hold=hold)
                        if row["status"]=="rendered" and all(v["within_15ms"] for v in row["delivery"].values()) and all(v["ms"] is not None and v["ms"]<=5 for v in row["api_response"]):
                            timing_survivors.append((rate,backend,window,hop))
        report["oracle_timing_survivors"]=sorted(set(timing_survivors))
        # One tracker scheduling variant, only on the small Accelerate preset and
        # only if ALL event phases pass the oracle timing screen at both rates.
        tracker_allowed=all(timing_survivors.count((rate,"accelerate",256,32))==3 for rate in (44100,48000))
        if tracker_allowed:
            for rate in (44100,48000):
                for hz in (82.4068892282175,220,1046.5022612023945):
                    values=tone(rate,hz,1.3); values.extend([0.]*(rate//3))
                    run(f"trailing-{rate}-{hz:.0f}","accelerate",rate,256,32,values,[(0,hz,(-12,3,7)),(round(rate*.7),hz,(-5,7,12))],mode=1)
            report["tracker_schedule"]="one unchanged-tracker trailing-source schedule executed; no further tuning"
        else: report["tracker_schedule"]="skipped_oracle_timing_failed"
        values,events,expected,replay_hashes=replay_source(directory)
        report["replay_source_hashes"]=replay_hashes
        for backend in ("accelerate","builtin"):
            repeats=[run("replay-"+backend+"-"+str(i),backend,44100,512,128,values,events,mode=2,warm=int(i==2)) for i in range(3)]
            for row in repeats:
                require(all(a["input_hash"]==b["native_input_hash"] and a["control_hash"]==b["control_hash"] for a,b in zip(row["native"]["voices"],expected)),"Replay does not reproduce retained native calls")
            report["comparisons"].extend(compare(directory,repeats[0],r) for r in repeats[1:])
        for changing in (False,True):
            values=tone(48000,220,1.7); values.extend([0.]*16000)
            events=[(0,220,(-12,3,7))]
            if changing: events.extend([(24001,220,(-5,7,12)),(52863,220,(-12,-7,0))])
            cold=run("rb-cold-"+str(changing),"rubberband",48000,1,128,values,events)
            warm=run("rb-warm-"+str(changing),"rubberband",48000,1,128,values,events,warm=1)
            run("rb-stacks-"+str(changing),"rubberband",48000,1,128,values,events,trace=1)
            primed=run("rb-primed-reset-"+str(changing),"rubberband",48000,1,128,values,events,warm=2)
            report["comparisons"].append(compare(directory,cold,warm))
            report["comparisons"].append(compare(directory,cold,primed))
        verify(build,provenance)
        baseline_hashes=dict(report["baseline_crosscheck"]["baseline_hashes"],**replay_hashes)
        require(all(sha256(BASELINE/name)==digest for name,digest in baseline_hashes.items()),"Retained baseline artifacts changed during batch")
        report["source_build_unchanged"]=True; report["status"]="bounded_batch_complete_not_product_pass"
        report["decision"]=decision(report["cases"])
    except Exception as error:
        report["status"]="fail"; report["error"]=str(error); raise
    finally:
        write_json(directory/"report.json",report); print("Architecture evidence:",directory/"report.json",flush=True)
    return directory


def check(jobs=6):
    directory=ROOT/"build/architecture-checks"/stamp(); directory.mkdir(parents=True)
    files=source_fingerprint(); report={"status":"running","files":files,"steps":[]}
    def run(label,command,env=None):
        with (directory/(label+".log")).open("x") as log: result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=env)
        report["steps"].append({"label":label,"command":command,"return_code":result.returncode})
        require(result.returncode==0,str(directory/(label+".log")))
    try:
        source=directory/"source.f32"; source.write_bytes((tone(48000,220,.5)+array.array("f",[0.]*16000)).tobytes())
        events=directory/"events.txt"; events.write_text("0 220 -12 3 7\n8001 220 -5 7 12\n16063 220 -12 -7 0\n")
        for project,name in (("InteractionEvaluation","interaction"),("ArchitectureEvaluation","architecture")):
            for profile in ("release","debug","asan","tsan"):
                build=ROOT/"build"/(name+"-"+profile); label=name+"-"+profile
                run(label+"-configure",["cmake","-S",project,"-B",str(build),"-DCMAKE_BUILD_TYPE="+("Release" if profile=="release" else "Debug"),
                    "-DVOXIDE_OFFLINE=ON","-DVOXIDE_SANITIZER="+{"asan":"address","tsan":"thread"}.get(profile,""),"-DPython3_EXECUTABLE="+sys.executable])
                run(label+"-build",["cmake","--build",str(build),"--parallel",str(jobs)])
                env=dict(os.environ,ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",TSAN_OPTIONS="halt_on_error=1")
                run(label+"-test",["ctest","--test-dir",str(build),"--output-on-failure","--no-tests=error"],env)
                if name=="architecture":
                    for backend,window,hop in (("accelerate",256,32),("builtin",512,128),("rubberband",1,128)):
                        for mode in (0,1):
                            prefix=directory/(label+"-"+backend+"-"+str(mode))
                            run(prefix.name,[str(build/("architecture_"+backend)),"48000",str(window),str(hop),"0",str(events),str(prefix),"0","0",str(mode),str(source)],env)
        report["research"]=str((research(ROOT/"build/architecture-release")/"report.json").relative_to(ROOT))
        require(source_fingerprint()==files,"Source changed during final architecture qualification")
        report.update(status="pass",source_unchanged=True)
    except Exception as error:
        report.update(status="fail",error=str(error)); raise
    finally:
        write_json(directory/"report.json",report); print("Architecture validation:",directory/"report.json",flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--build",type=Path,default=ROOT/"build/architecture-release")
    parser.add_argument("--check",action="store_true",help="Offline four-profile contracts/render safety, then the single bounded Release batch")
    args=parser.parse_args()
    if args.check: check()
    else: research(args.build.resolve())


if __name__=="__main__": main()
