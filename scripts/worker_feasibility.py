#!/usr/bin/env python3
"""One-use, synthetic-only worker architecture screen. Never runs hosts/private audio."""
import argparse
import hashlib
import math
from pathlib import Path
import platform
import shutil
import struct
import subprocess

from check import source_fingerprint
from engine_dependencies import prepare
from engine_metrics import callback_metrics, read_csv, read_float
from evaluation_common import ROOT, load_json, require, sha256, write_json
from interaction_evaluation import stamp
from rubberband_allocation_diagnosis import save_owned_json
from studio_validation import control_coverage, fixed_sum_checks, studio_clocks

PROTOCOL = ROOT/"docs/evidence/pr-06a/worker-feasibility-001.json"
BUILD = ROOT/"build/worker-feasibility-release-001"
FILES = (
    "WorkerEvaluation/CMakeLists.txt", "WorkerEvaluation/WorkerEngine.h", "WorkerEvaluation/WorkerEngine.cpp",
    "WorkerEvaluation/Tests.cpp", "WorkerEvaluation/Probe.cpp", "InteractionEvaluation/InteractionProcessor.cpp",
    "InteractionEvaluation/InteractionProcessor.h", "EngineEvaluation/EngineAdapter.cpp", "EngineEvaluation/EngineAdapter.h",
    "Source/DSP/PitchTracker.cpp", "Source/DSP/PitchTracker.h", "Source/DSP/HarmonySelector.cpp", "Source/DSP/HarmonySelector.h",
    "Source/Tests/AllocationAudit.cpp", "Source/Tests/AllocationAudit.h", "cmake/engine-dependencies.json",
)


def identity():
    text = "".join(f"{name}|{sha256(ROOT/name)}\n" for name in sorted(FILES))
    return hashlib.sha256(text.encode()).hexdigest()


def jobs():
    return [(rate, block, "suite", 3) for rate in (44100, 48000) for block in (128, 512)]+[
        (rate, 128, "fault", 1) for rate in (44100, 48000)]


def fnv(words):
    result = 14695981039346656037
    for word in words: result = ((result ^ word)*1099511628211) & ((1<<64)-1)
    return str(result)


def compare(a, b):
    x, y = load_json(a/"native.json"), load_json(b/"native.json")
    hashes = all(x["voices"][v][k] == y["voices"][v][k] for v in range(3) for k in ("input_hash", "control_hash", "native_frames"))
    controls = lambda p: [r for r in read_csv(p/"telemetry.csv") if r["kind"] == "0"]
    control_equal = controls(a) == controls(b)
    channels = []
    for channel in range(10):
        u, _ = read_float(a/f"channel{channel}.f32"); v, _ = read_float(b/f"channel{channel}.f32")
        errors = [float(p)-q for p, q in zip(u, v)]
        maximum = max(map(abs, errors), default=0)
        rms = math.sqrt(sum(e*e for e in errors)/len(errors)) if errors else None
        passed = len(u) == len(v) and bool(errors) and maximum <= 1e-6 and rms <= 1e-7
        channels.append({"channel": channel, "frames_a": len(u), "frames_b": len(v), "max_abs": maximum, "rms": rms, "pass": passed})
    return {"hashes_match": hashes, "controls_match": control_equal, "channels": channels,
            "pass": hashes and control_equal and all(r["pass"] for r in channels)}


def validate(directory, rate, block, mode, expected_identity):
    native = load_json(directory/"native.json"); total = rate*28//5
    require((native["identity"], native["rate"], native["block"], native["mode"])
            == (expected_identity, rate, block, mode), "Wrong native identity/configuration")
    require(native["profile"] == "Release" and native["sanitizer"] == "" and native["audit_available"] is True,
            "Allocation/performance evidence requires unsanitized Release")
    require(native["complete"] and native["frames"] == total and not native["error"]
            and native["latency_samples"] == rate//10, "Incomplete/wrong-duration or >100ms capture")
    clocks = studio_clocks(rate, 1, 128, "rubberband")
    require(native["analysis_samples"] == clocks["analysis"], "Tracker reserve changed")
    source, _ = read_float(directory.parent/"source.f32")
    audio = [read_float(directory/f"channel{c}.f32")[0] for c in range(10)]
    require(len(source) == total and all(len(a) == total for a in audio)
            and all(v == 0 for v in source[rate*5:]), "Truncated audio or nonzero supplied tail")
    require(max(abs(v) for a in audio for v in a) < 1, "Full-scale over; no repair")
    nulls = []
    for channel, delay in ((0, 0), (1, rate//10)):
        errors = [float(v)-(source[i-delay] if i >= delay else 0) for i, v in enumerate(audio[channel])]
        nulls.append({"channel": channel, "max_abs": max(map(abs, errors)), "rms": math.sqrt(sum(e*e for e in errors)/total)})
    sums = fixed_sum_checks(audio[0], audio[1], audio[5:8], {"sum-direct": audio[8], "sum-aligned": audio[9]})
    rows = read_csv(directory/"telemetry.csv")
    require(rows and all(int(r["kind"]) in (0, 1, 2) and int(r["epoch"]) == 0 for r in rows), "Unknown telemetry kind/epoch")
    require(all(int(a["wall"]) <= int(b["wall"]) for a, b in zip(rows, rows[1:])), "Unordered telemetry")
    controls = [r for r in rows if r["kind"] == "0"]
    coverage = control_coverage(controls, rate=rate, total=total, clocks=clocks)
    requests = [r for r in rows if r["kind"] == "2"]
    expected_events = [0, round(rate*1.6), round(rate*2.8), rate*4]
    require([int(r["requested"]) for r in requests] == expected_events
            and all(int(r["wall"]) == int(r["available"]) == int(r["requested"]) and int(r["request_kind"]) == 3 for r in requests),
            "Harmony requests differ from frozen source-time scene")
    require(len(native["voices"]) == 3, "Missing voice")
    fed = (total-clocks["analysis"])//128*128
    input_hash = fnv(word[0] for word in struct.iter_unpack("I", source[:fed].tobytes()))
    packet_deadline_misses = 0
    for voice in range(3):
        stream = [r for r in controls if int(r["voice"]) == voice]
        words = []
        for row in stream:
            values = (float(row["applied_shift"]), float(row["hz"]) if int(row["voiced"]) else 0.)
            words.extend(struct.unpack("Q", struct.pack("d", value))[0] for value in values)
        require(native["voices"][voice]["input_hash"] == input_hash
                and native["voices"][voice]["control_hash"] == fnv(words), "Independent input/control hashes disagree")
        require(any(int(r["active"]) for r in stream), "Voice was never processing pitched controls")
        position = 0
        for row in (r for r in rows if r["kind"] == "1" and int(r["voice"]) == voice):
            count, first, wall, available = (int(row[k]) for k in ("count", "first_output", "wall", "available"))
            require(first == position and 0 <= count <= 1024 and 0 <= wall <= available <= total, "Invalid/missing native output packet")
            if count and first < total-rate//10 and wall > first+rate//10: packet_deadline_misses += 1
            position += count
        require(position == native["voices"][voice]["native_frames"] and position >= total-rate//10,
                "Missing native frame/tail evidence")
    callbacks = read_csv(directory/"callbacks.csv")
    cpu = callback_metrics(callbacks, rate, True, {"callback_occupancy_p999_max_exclusive": .5}, total)
    require([int(r["frames"]) for r in callbacks] == [min(block, total-i) for i in range(0, total, block)],
            "Callback partition changed")
    scheduled_overdue = sum(int(r["finish_ns"]) > int(r["deadline_ns"]) for r in callbacks) if mode in ("paced", "fault") else 0
    delivery = all(v["underflows"] == v["late_samples"] == 0 for v in native["voices"]) and not native["failed_closed"] and packet_deadline_misses == 0
    require(all(native[k] == 0 for k in ("bad_events", "late_controls", "telemetry_dropped", "invalid_input", "missing_metadata", "fifo_overflow")),
            "Control/metadata/queue error")
    workers = native["workers"]
    require(len(workers) == (0 if mode == "reference" else 3), "Missing worker metrics")
    worker_healthy = all(not w["failed"] and w["audit_detected"] and w["commands"] == fed//128+10
                         and w["native_frames"] == native["voices"][i]["native_frames"]+1280 for i, w in enumerate(workers))
    require(mode == "reference" or sum(w["body_allocations"] for w in workers) > 0, "Worker allocations unexpectedly hidden")
    if mode == "fault":
        first = native["first_failure"]
        negative = native["failed_closed"] and 0 <= first < rate and any(v["underflows"] > 0 for v in native["voices"])
        negative = negative and all(v == 0 for channel in range(2, 8) for v in audio[channel][first:])
        allocation_gate = cpu["allocation_calls"] == 0
    else:
        negative = True
        allocation_gate = cpu["allocation_calls"] > 0 if mode == "reference" else cpu["allocation_calls"] == 0
        require(all(max(map(abs, audio[c])) > 1e-6 for c in (5, 6, 7)), "Silent harmony cannot pass")
    gates = {
        "lead": all(r["max_abs"] <= 1e-6 and r["rms"] <= 1e-7 for r in nulls),
        "fixed_sums": all(r["max_abs"] <= 1e-6 and r["rms"] <= 1e-7 for r in sums.values()),
        "allocation": allocation_gate, "worker_integrity": worker_healthy, "tail": native["finish_peak"] <= 1e-6,
        "delivery": True if mode == "fault" else delivery,
        "callback_budget": cpu["occupancy_target_met_on_this_run_only"] and scheduled_overdue == 0,
        "negative_exposes_stall": negative,
    }
    return {"mode": mode, "native": native, "callback": cpu, "scheduled_overdue_callbacks": scheduled_overdue,
            "maximum_schedule_lateness_ns": max(int(r["late_ns"]) for r in callbacks), "lead_null": nulls,
            "fixed_sums": sums, "coverage": coverage, "packet_deadline_misses": packet_deadline_misses,
            "gates": gates, "pass": all(gates.values())}


def run():
    protocol = load_json(PROTOCOL)
    tasks = jobs()
    require(len(tasks) == protocol["captures"]["process_cap"] == 6
            and sum(row[3] for row in tasks) == protocol["captures"]["total_cap"] == 14, "Frozen capture/process cap mismatch")
    root = ROOT/"build/worker-feasibility"; claims = root/"claims"; claims.mkdir(parents=True, exist_ok=True)
    claim = claims/(protocol["id"]+".json")
    with claim.open("x") as stream: stream.write('{"status":"claimed"}\n')
    directory = root/stamp(); directory.mkdir()
    write_json(directory/"protocol.json", protocol)
    before = source_fingerprint(); binary = BUILD/"voxide_worker_probe"; expected = identity()
    binary_hash = None; library_hash = None
    library = BUILD/"interaction/engines/libengine_allocation_audit.dylib"
    report = {"schema": "voxide.worker-feasibility-result.v1", "status": "running", "protocol_sha256": sha256(PROTOCOL),
              "reserved_captures": 0, "process_executions": 0, "cases": [], "comparisons": [],
              "private_audio_reads": 0, "product_integration": False, "pitch_qualified": False,
              "environment": {"platform": platform.platform()}}
    try:
        actual = subprocess.check_output([str(binary), "--identity"], text=True).strip()
        require(actual == expected, "Stale worker prototype binary")
        binary_hash = sha256(binary); library_hash = sha256(library)
        dependencies = load_json(BUILD/"interaction/engines/_deps/engine-sources.json")
        for package in dependencies["packages"]:
            checked = prepare(package, ROOT/".cache/dependencies", BUILD/"interaction/engines/_deps", offline=True)
            require(checked["tree_sha256"] == package["tree_sha256"], "Edited dependency")
        write_json(directory/"provenance.json", {"files_sha256": before, "identity": expected, "binary_sha256": binary_hash,
            "audit_library_sha256": library_hash, "dependencies": dependencies, "compile_commands_sha256": sha256(BUILD/"compile_commands.json")})
        shutil.copy2(binary, directory/binary.name); shutil.copy2(library, directory/library.name)
        shutil.copy2(BUILD/"compile_commands.json", directory/"compile_commands.json")
        for name in before:
            target = directory/"source-snapshot"/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT/name, target)
        for rate, block, kind, count in tasks:
            require(report["reserved_captures"]+count <= 14 and report["process_executions"] < 6, "Native cap exceeded")
            path = directory/f"{rate}-{block}-{kind}"
            report["reserved_captures"] += count; report["process_executions"] += 1
            command = [str(binary), "--"+kind, str(rate), str(block), str(path)]
            result = subprocess.run(command, capture_output=True, timeout=120)
            (directory/(path.name+".stdout.txt")).write_bytes(result.stdout)
            (directory/(path.name+".stderr.txt")).write_bytes(result.stderr)
            require(result.returncode == 0 and not result.stderr, "Native prototype failed or emitted diagnostics; no retry")
            report["cases"].append({"id": path.name, "rate": rate, "block": block, "kind": kind})
            save_owned_json(directory/"report.json", report)
        # All native/paced measurements finish before any output analysis.
        for row in report["cases"]:
            path = directory/row["id"]
            modes = ("reference", "paced", "offline") if row["kind"] == "suite" else ("fault",)
            row["captures"] = [validate(path/mode, row["rate"], row["block"], mode, expected) for mode in modes]
            if row["kind"] == "suite":
                for mode in ("paced", "offline"):
                    report["comparisons"].append({"case": row["id"], "mode": mode, **compare(path/"reference", path/mode)})
        for rate in (44100, 48000):
            for mode in ("reference", "paced", "offline"):
                a = directory/f"{rate}-128-suite"/mode; b = directory/f"{rate}-512-suite"/mode
                report["comparisons"].append({"case": str(rate), "mode": mode, "kind": "callback_partition", **compare(a, b)})
        captures = [c for row in report["cases"] for c in row["captures"]]
        require(len(captures) == 14 and len(report["comparisons"]) == 14, "Incomplete fixed experiment")
        report["status"] = "sampled_worker_screen_pass_not_product_acceptance" if all(c["pass"] for c in captures) and all(c["pass"] for c in report["comparisons"]) else "worker_screen_failed_stop"
    except Exception as error:
        report["status"] = "incomplete_stop_no_retry"; report["error"] = str(error)
        raise
    finally:
        report["source_unchanged"] = source_fingerprint() == before
        report["binary_unchanged"] = binary.is_file() and sha256(binary) == binary_hash
        report["audit_library_unchanged"] = library.is_file() and sha256(library) == library_hash
        if not all(report[k] for k in ("source_unchanged", "binary_unchanged", "audit_library_unchanged")):
            report["status"] = "identity_changed_stop"
        save_owned_json(directory/"report.json", report)
        write_json(directory/"artifacts.json", {"files_sha256": {str(p.relative_to(directory)): sha256(p)
            for p in sorted(directory.rglob("*")) if p.is_file() and p.name != "artifacts.json"}})
        save_owned_json(claim, {"status": "consumed", "run": str(directory.relative_to(ROOT)), "report_sha256": sha256(directory/"report.json")})
    print(str((directory/"report.json").relative_to(ROOT)), report["status"])
    return 0 if report["status"] == "sampled_worker_screen_pass_not_product_acceptance" else 1


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    raise SystemExit(run())
