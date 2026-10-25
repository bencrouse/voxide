#!/usr/bin/env python3
"""One-use synthetic allocation diagnosis. No private/audio-input/playback route."""
import argparse
import csv
import math
from pathlib import Path
import shutil
import subprocess

from check import source_fingerprint
from engine_metrics import read_float
from evaluation_common import ROOT, load_json, require, sha256, write_json
from interaction_evaluation import stamp

PROTOCOL = ROOT/"docs/evidence/pr-06a/rubberband-allocation-diagnosis-001.json"
BUILD = ROOT/"build/rubberband-allocation-diagnosis-001"
IDENTITY_FILES = (
    "AllocationEvaluation/CMakeLists.txt", "AllocationEvaluation/Probe.cpp",
    "ArchitectureEvaluation/TraceAllocations.cpp", "ArchitectureEvaluation/TraceAllocations.h",
    "EngineEvaluation/EngineAdapter.cpp", "EngineEvaluation/EngineAdapter.h",
    "Source/Tests/AllocationAudit.h", "cmake/engine-dependencies.json",
)


def cases():
    return [(rate, workload, preparation) for rate in (44100, 48000)
            for workload in ("static", "changing") for preparation in ("fresh", "silent")]


def compiled_identity():
    import hashlib
    text = "".join(f"{name}|{sha256(ROOT/name)}\n" for name in sorted(IDENTITY_FILES))
    return hashlib.sha256(text.encode()).hexdigest()


def save_owned_json(path, value):
    """Atomic updates only for this run's exclusively claimed report/claim."""
    temporary = path.with_suffix(path.suffix+".next")
    write_json(temporary, value)
    temporary.replace(path)


def expected_controls(rate, workload):
    shifts = [0., 0., 0.]
    for begin in range(0, rate*18//5, 128):
        count = min(128, rate*18//5-begin)
        targets = [-12., 7., 12.]
        if workload == "changing":
            if begin >= 2*rate: targets = [-7., 12., -12.]
            elif begin >= rate: targets = [12., -12., 4.]
            targets = [t+.35*math.sin(2*math.pi*5*begin/rate) if abs(t) < 12 else t for t in targets]
        for voice, target in enumerate(targets):
            step = 2400.*count/rate
            shifts[voice] += max(-step, min(step, target-shifts[voice]))
            yield begin, count, voice, shifts[voice]


def validate_capture(directory, case, identity):
    rate, workload, preparation = case
    native = load_json(directory/"native.json")
    require((native["rate"], native["workload"], native["preparation"], native["identity"])
            == (*case, identity), "Unexpected native configuration/identity")
    total = rate*18//5
    require(native["frames"] == total and native["start_pad"] > 0 and native["start_trim"] > 0,
            "Invalid duration/start metadata")
    source, _ = read_float(directory/"source.f32")
    require(len(source) == total and all(math.isfinite(x) for x in source)
            and all(x == 0 for x in source[rate*3:]) and max(map(abs, source)) > .01,
            "Invalid synthetic source or zero tail")
    with (directory/"allocations.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    expected = [(stage, str(begin), str(voice)) for begin in range(0, total, 128)
                for voice in range(3) for stage in ("control", "process", "retrieve")]
    callback = [r for r in rows if r["stage"] in ("control", "process", "retrieve")]
    require([(r["stage"], r["source"], r["voice"]) for r in callback] == expected,
            "Missing/out-of-order callback allocation evidence")
    fixed = [("construct", "0", "-1")]
    if preparation == "silent": fixed += [("stopped_silence", "0", "-1"), ("stopped_reset", "0", "-1")]
    fixed += [("stopped_pad", "0", "-1")]+[("finish", str(total), str(v)) for v in range(3)]
    require([(r["stage"], r["source"], r["voice"]) for r in rows if r["stage"] not in ("control", "process", "retrieve")] == fixed,
            "Missing/extra stopped or finish evidence")
    require(all(int(r["calls"]) >= 0 for r in rows), "Invalid allocation count")
    require(sum(int(r["calls"]) for r in callback) == native["callback_allocations"]
            and sum(int(r["calls"]) for r in rows if r["stage"] == "finish") == native["finish_allocations"],
            "Allocation counters disagree")
    with (directory/"controls.csv").open() as stream:
        controls = list(csv.DictReader(stream))
    require(len(controls) == 3*((total+127)//128), "Missing control quanta")
    import struct
    value = 14695981039346656037
    for row, (begin, count, voice, expected_shift) in zip(controls, expected_controls(rate, workload)):
        shift, ratio = float(row["shift"]), float(row["ratio"])
        require((int(row["source"]), int(row["count"]), int(row["voice"]))
                == (begin, count, voice), "Unexpected control clock")
        require(math.isfinite(shift) and abs(shift) <= 12 and abs(shift-expected_shift) < 1e-12
                and abs(ratio-2**(shift/12)) < 1e-14,
                "Invalid shift or transpose ratio")
        value = ((value ^ struct.unpack("Q", struct.pack("d", ratio))[0])*1099511628211) & ((1<<64)-1)
    require(str(value) == native["control_hash"], "Independent control hash mismatch")
    value = 14695981039346656037
    for word in struct.iter_unpack("I", (directory/"source.f32").read_bytes()):
        value = ((value ^ word[0])*1099511628211) & ((1<<64)-1)
    require(str(value) == native["input_hash"], "Independent input hash mismatch")
    for voice, frames in enumerate(native["output_frames"]):
        audio, _ = read_float(directory/f"voice{voice}.f32")
        require(len(audio) == frames and frames >= total and all(math.isfinite(x) for x in audio),
                "Missing, truncated or nonfinite native output")
    require(len(native["output_frames"]) == 3, "Missing harmony")
    return native


def compare(fresh, silent):
    a, b = load_json(fresh/"native.json"), load_json(silent/"native.json")
    require(all(a[k] == b[k] for k in ("identity", "rate", "workload", "frames", "start_pad", "start_trim", "input_hash", "control_hash")),
            "Prepared input/control/metadata differ from fresh")
    require(sha256(fresh/"source.f32") == sha256(silent/"source.f32")
            and sha256(fresh/"controls.csv") == sha256(silent/"controls.csv"), "Prepared source/control bytes differ")
    voices = []
    for v in range(3):
        x, _ = read_float(fresh/f"voice{v}.f32"); y, _ = read_float(silent/f"voice{v}.f32")
        equal_length = len(x) == len(y) and len(x) > 0
        finite = all(math.isfinite(z) for audio in (x, y) for z in audio)
        errors = [float(p)-float(q) for p, q in zip(x, y)] if equal_length and finite else []
        maximum = max(map(abs, errors)) if errors else None
        rms = math.sqrt(sum(e*e for e in errors)/len(errors)) if errors else None
        voices.append({"voice": v, "fresh_frames": len(x), "silent_frames": len(y),
                       "max_abs": maximum, "rms": rms, "pass": bool(errors) and maximum <= 1e-6 and rms <= 1e-7})
    passed = all(v["pass"] for v in voices) and b["callback_allocations"] == b["finish_allocations"] == 0
    return {"voices": voices, "fresh_callback_allocations": a["callback_allocations"],
            "silent_callback_allocations": b["callback_allocations"], "silent_finish_allocations": b["finish_allocations"], "pass": passed}


def run():
    frozen = load_json(PROTOCOL)
    require(len(cases()) == frozen["native_capture_cap"] == 8, "Capture cap mismatch")
    claims = ROOT/"build/rubberband-allocation-diagnosis/claims"
    claims.mkdir(parents=True, exist_ok=True)
    claim = claims/(frozen["id"]+".json")
    # Consume before attestation/execution; never delete or reuse after failure.
    with claim.open("x") as stream: stream.write('{"status":"claimed"}\n')
    output = ROOT/"build/rubberband-allocation-diagnosis"/stamp(); output.mkdir()
    write_json(output/"protocol.json", frozen)
    before = source_fingerprint()
    expected = compiled_identity()
    binary = BUILD/"voxide_rubberband_allocation_probe"
    binary_hash = None
    report = {"schema": "voxide.rubberband-allocation-result.v1", "status": "running", "native_executions": 0,
              "protocol_sha256": sha256(PROTOCOL), "cases": [], "comparisons": [], "timing_claim": False,
              "private_audio_reads": 0, "product_wrapper_changed": False, "pitch_qualified": False}
    try:
        actual = subprocess.check_output([str(binary), "--identity"], text=True).strip()
        require(actual == expected, "Stale diagnosis binary")
        subprocess.run([str(binary), "--self-test"], check=True, capture_output=True, text=True)
        binary_hash = sha256(binary)
        deps = load_json(BUILD/"engines/_deps/engine-sources.json")
        from engine_dependencies import prepare
        for package in deps["packages"]:
            checked = prepare(package, ROOT/".cache/dependencies", BUILD/"engines/_deps", offline=True)
            require(checked["tree_sha256"] == package["tree_sha256"], "Edited dependency")
        write_json(output/"provenance.json", {"source_files_sha256": before, "binary_sha256": binary_hash,
            "compile_commands_sha256": sha256(BUILD/"compile_commands.json"), "identity": expected,
            "dependencies": deps, "trace_library_sha256": sha256(BUILD/"liballocation_diagnosis_trace.dylib")})
        shutil.copy2(binary, output/binary.name)
        shutil.copy2(BUILD/"liballocation_diagnosis_trace.dylib", output/"liballocation_diagnosis_trace.dylib")
        shutil.copy2(BUILD/"compile_commands.json", output/"compile_commands.json")
        for name in before:
            target = output/"source-snapshot"/name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/name, target)
        for case in cases():
            require(report["native_executions"] < 8, "Native capture cap exceeded")
            rate, workload, preparation = case
            directory = output/f"{rate}-{workload}-{preparation}"
            report["native_executions"] += 1
            result = subprocess.run([str(binary), str(rate), workload, preparation, str(directory)], capture_output=True, text=True)
            (output/(directory.name+".log")).write_text(result.stdout+result.stderr)
            require(result.returncode == 0, "Native diagnostic capture failed; no retries")
            native = validate_capture(directory, case, expected)
            report["cases"].append({"id": directory.name, "native": native})
            save_owned_json(output/"report.json", report)
        for rate in (44100, 48000):
            for workload in ("static", "changing"):
                report["comparisons"].append({"rate": rate, "workload": workload,
                    **compare(output/f"{rate}-{workload}-fresh", output/f"{rate}-{workload}-silent")})
        report["status"] = "diagnostic_hypothesis_survives_not_qualified" if all(r["pass"] for r in report["comparisons"]) else "preparation_rejected_stop"
    except Exception as error:
        report["status"] = "incomplete_stop_no_retry"; report["error"] = str(error)
        raise
    finally:
        report["source_unchanged"] = source_fingerprint() == before
        report["binary_unchanged"] = binary.is_file() and sha256(binary) == binary_hash
        if not (report["source_unchanged"] and report["binary_unchanged"]): report["status"] = "identity_changed_stop"
        save_owned_json(output/"report.json", report)
        write_json(output/"artifacts.json", {"files_sha256": {str(p.relative_to(output)): sha256(p)
                   for p in sorted(output.rglob("*")) if p.is_file() and p.name != "artifacts.json"}})
        save_owned_json(claim, {"status": "consumed", "run": str(output.relative_to(ROOT)), "report_sha256": sha256(output/"report.json")})
    print(str((output/"report.json").relative_to(ROOT)), report["status"])
    return 0 if report["status"] == "diagnostic_hypothesis_survives_not_qualified" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    raise SystemExit(run())
