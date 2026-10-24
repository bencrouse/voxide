#!/usr/bin/env python3
"""Synthetic-only studio CPU/lifecycle/repeat comparison. No private audio inputs."""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys

from evaluation_common import ROOT, load_json, require, sha256, write_json
from engine_metrics import callback_metrics, read_csv, read_float
from evaluation_metrics import percentile
from interaction_evaluation import identity, provenance, verify_provenance, stamp
from studio_validation import control_coverage, fixed_sum_checks, studio_clocks

PROTOCOL = ROOT/"docs/evidence/pr-06a/engineering-protocol.json"


def validate_duration(native, protocol):
    # The immutable v1 protocol fixes 5s primary + 0.6s zero tail. Do not trust
    # self-consistent file/native declarations as an independent duration oracle.
    require(protocol["id"] == "pr06a-engineering-001" and native["rate"] in (44100, 48000), "Unsupported engineering workload")
    rate = native["rate"]
    require((native["source_frames"], native["zero_tail"], native["frames"]) == (rate*5, rate*3//5, rate*28//5),
            "Engineering duration differs from frozen 5s primary/0.6s tail")


def compare(a_prefix, b_prefix, a, b):
    if not a["complete"] or not b["complete"]:
        return {"status": "incomplete_native_capture", "channels": []}
    hashes = len(a["voices"]) == len(b["voices"]) == 3 and all(x["input_hash"] == y["input_hash"] and x["control_hash"] == y["control_hash"] for x, y in zip(a["voices"], b["voices"]))
    rows = []
    for channel in range(10):
        x, _ = read_float(str(a_prefix)+f"-channel{channel}.f32")
        y, _ = read_float(str(b_prefix)+f"-channel{channel}.f32")
        count = min(len(x), len(y))
        maximum = max((abs(float(u)-v) for u, v in zip(x, y)), default=0)
        rms = math.sqrt(sum((float(u)-v)**2 for u, v in zip(x, y))/count) if count else None
        rows.append({"channel": channel, "frames_a": len(x), "frames_b": len(y), "max_abs": maximum, "rms": rms,
                     "pass": len(x) == len(y) and count > 0 and maximum <= 1e-6 and rms <= 1e-7})
    return {"status": "input_control_mismatch" if not hashes else "pass" if all(r["pass"] for r in rows) else "waveform_difference",
            "input_control_hashes_match": hashes, "channels": rows}


def analyse(prefix, native, capture, protocol):
    result = {"name": capture["name"], "native": capture}
    if not capture["complete"]:
        result.update(status="native_failed", error_path=str(prefix)+"-error.txt"); return result
    validate_duration(native, protocol)
    require(capture["processed"] == native["frames"], "Completed capture has wrong length")
    audio = [read_float(str(prefix)+f"-channel{c}.f32")[0] for c in range(10)]
    require(all(len(v) == native["frames"] for v in audio), "Truncated engineering capture")
    source, _ = read_float(str(prefix).rsplit("-", 1)[0]+"-source.f32")
    require(len(source) == native["frames"], "Synthetic source/capture length mismatch")
    require(all(x == 0 for x in source[native["source_frames"]:]), "Nonzero supplied engineering tail")
    nulls = []
    for c, delay in ((0, 0), (1, native["rate"]//10)):
        errors = [float(x)-(source[i-delay] if i >= delay else 0) for i, x in enumerate(audio[c])]
        nulls.append({"channel": c, "max_abs": max(map(abs, errors)), "rms": math.sqrt(sum(x*x for x in errors)/len(errors))})
    controls = read_csv(str(prefix)+"-controls.csv")
    clocks = studio_clocks(native["rate"], native["window"], native["hop"], native["engine"])
    control_checks = control_coverage(controls, rate=native["rate"], total=native["frames"], clocks=clocks, compact=True)
    for row in controls:
        require(abs(float(row["shift"])) <= 12.000001 and int(row["frame_available"]) <= int(row["wall"])+1, "Out-of-range or unavailable control")
        require(int(row["voiced"]) or not int(row["active"]), "Uncertain target was active")
    active = {voice: sum(int(r["active"]) for r in controls if int(r["voice"]) == voice) for voice in range(3)}
    require(all(active.values()), "Workload never exercised all three voices")
    require(all(max(map(abs, audio[c]), default=0) > 1e-6 for c in (5, 6, 7)), "Silent generated voices cannot pass engineering repeat checks")
    callbacks = read_csv(str(prefix)+"-callbacks.csv")
    cpu = callback_metrics(callbacks, native["rate"], True,
                           {"callback_occupancy_p999_max_exclusive": protocol["gates"]["occupancy_p999_max_exclusive"]}, native["frames"])
    # Keep startup, voiced body and final silence separate without removing any
    # observation from the complete-run deadlines/allocations gate.
    phases = {}
    for label, start, end in (("startup", 0, round(native["rate"]*.2)), ("body", round(native["rate"]*.2), native["source_frames"]),
                              ("supplied_zero_tail", native["source_frames"], native["frames"])):
        selected = [r for r in callbacks if start <= int(r["begin"]) < end]
        occupancy = [int(r["ns"])*native["rate"]/(1e9*int(r["frames"])) for r in selected]
        phases[label] = {"callbacks": len(selected), "occupancy_p999": percentile(occupancy, .999) if occupancy else None,
                         "occupancy_max": max(occupancy) if occupancy else None, "allocations": sum(int(r["allocations"]) for r in selected)}
    clean_delivery = len(capture["voices"]) == 3 and all(v["underflows"] == v["late_samples"] == 0 for v in capture["voices"])
    clean_delivery = clean_delivery and all(capture[k] == 0 for k in ("bad_events", "late_controls", "telemetry_dropped", "invalid_input", "missing_metadata", "fifo_overflow"))
    sums = fixed_sum_checks(audio[0], audio[1], audio[5:8], {"sum-direct": audio[8], "sum-aligned": audio[9]})
    result.update(status="measured", callback=cpu, phases=phases, lead_null=nulls, active_controls=active, control_coverage=control_checks, fixed_sum=sums,
                  gates={"delivery": "pass" if clean_delivery else "fail", "tail": "pass" if capture["finish_peak"] <= 1e-6 else "fail",
                         "lead_null": "pass" if all(r["max_abs"] <= 1e-6 and r["rms"] <= 1e-7 for r in nulls) else "fail",
                         "fixed_sum": "pass" if all(r["max_abs"] <= 1e-6 and r["rms"] <= 1e-7 for r in sums.values()) else "fail",
                         "callback_allocation": "pass" if cpu["allocation_calls"] == 0 else "fail",
                         "callback_budget_this_run": "pass" if cpu["occupancy_target_met_on_this_run_only"] else "fail"})
    return result


def summarize(cases, comparisons):
    groups = []
    for engine in ("signalsmith", "rubberband"):
        rows = [r for r in cases if r["engine"] == engine]
        captures = [c for r in rows for c in r.get("captures", [])]
        related = [c for c in comparisons if c["engine"] == engine]
        failures = [{"case": r["case"], "capture": c["name"], "gate": gate} for r in rows for c in r.get("captures", []) for gate, value in c.get("gates", {}).items() if value != "pass"]
        failures.extend({"case": r["case"], "gate": "native_failure"} for r in rows if r["status"] != "rendered")
        failures.extend({"comparison": c["kind"], "a": c["a"], "b": c["b"], "gate": c["result"]["status"]} for c in related if c["result"]["status"] != "pass")
        measured = [c for c in captures if c["status"] == "measured"]
        points = []
        for rate in (44100, 48000):
            for block in (128, 512):
                subset = [r for r in rows if r["rate"] == rate and r["block"] == block]
                names = {r["case"] for r in subset}
                relevant = [c for c in related if c["a"].split("/")[0] in names or c["b"].split("/")[0] in names]
                selected = [c for r in subset for c in r.get("captures", [])]
                passed = len(subset) == 2 and len(selected) == 6 and all(r["status"] == "rendered" for r in subset)
                passed = passed and all(c["status"] == "measured" and all(v == "pass" for v in c["gates"].values()) for c in selected)
                passed = passed and bool(relevant) and all(c["result"]["status"] == "pass" for c in relevant)
                points.append({"rate": rate, "block": block, "bounded_screen": "pass" if passed else "fail_or_incomplete",
                               "scope": "This sampled buffer/rate point only; failures at a smaller buffer do not by themselves disqualify a passing larger buffer"})
        groups.append({"engine": engine, "cases": len(rows), "captures": len(captures), "comparisons": len(related), "failures": failures,
                       "points": points,
                       "worst_callback_p999": max((c["callback"]["occupancy_p999"] for c in measured), default=None),
                       "worst_callback_max": max((c["callback"]["occupancy_max"] for c in measured), default=None),
                       "callback_allocations": sum(c["callback"]["allocation_calls"] for c in measured),
                       "overdue_callbacks": sum(c["callback"]["overdue_callbacks"] for c in measured),
                       "repeat_comparisons_pass": sum(c["result"]["status"] == "pass" for c in related),
                       "restart_rejections": sum(r.get("native", {}).get("restart_rejected", False) for r in rows),
                       "scope": "Bounded synthetic engineering results, not engine selection or host/actual-vocal qualification"})
    return groups


def research(build):
    protocol = load_json(PROTOCOL)
    require(protocol["id"] == "pr06a-engineering-001" and protocol["rates"] == [44100, 48000]
            and protocol["callback_frames"] == [128, 512] and protocol["fresh_processes_per_point"] == 2
            and protocol["candidates"] == [{"engine": "signalsmith", "window": 2048, "hop": 512}, {"engine": "rubberband", "window": 1, "hop": 128}], "Unexpected bounded engineering protocol")
    directory = ROOT/"build/studio-engineering"/stamp(); directory.mkdir(parents=True)
    report = {"schema": "voxide.studio-engineering.v1", "status": "running", "cases": [], "comparisons": [],
              "protocol_sha256": sha256(PROTOCOL), "environment": {"platform": platform.platform(), "python": sys.version,
              "cpu_count": os.cpu_count(), "load_average_at_start": os.getloadavg()},
              "scope": "Synthetic-only suitability study, not private-audio, listening, Logic or global realtime certification"}
    try:
        p = provenance(build, directory)
        report["provenance"] = "provenance.json"
        for candidate in protocol["candidates"]:
            binary = build/("voxide_"+candidate["engine"]+"_interaction")
            result = subprocess.run([str(binary), "--describe"], capture_output=True, timeout=30)
            require(result.returncode == 0 and not result.stderr, "Native build capability probe failed")
            description = json.loads(result.stdout)
            require(description["compiled_source_identity"] == identity() and description["profile"] == "Release" and not description["sanitizer"]
                    and description["audit_available"] is True and description.get("engineering_probe_v1") is True, "Stale/sanitized/unsupported engineering build")
            require(description["engine"] == {"signalsmith": "signalsmith", "rubberband": "rubberband-r3"}[candidate["engine"]], "Wrong native engine")
            for rate in protocol["rates"]:
                for block in protocol["callback_frames"]:
                    for repeat in range(protocol["fresh_processes_per_point"]):
                        name = f"{candidate['engine']}-{rate}-{block}-p{repeat}"
                        case = directory/name; case.mkdir()
                        command = [str(binary), "--engineering", str(rate), str(candidate["window"]), str(candidate["hop"]), str(block), str(case/"render")]
                        result = subprocess.run(command, capture_output=True, timeout=180)
                        (case/"stdout.txt").write_bytes(result.stdout); (case/"stderr.txt").write_bytes(result.stderr)
                        row = {"case": name, "engine": candidate["engine"], "rate": rate, "block": block, "repeat": repeat,
                               "command": command, "return_code": result.returncode, "status": "rendered" if not result.returncode else "native_failed"}
                        report["cases"].append(row)
                        write_json(case/"invocation.json", row)
                        native_path = case/"render-engineering.json"
                        if native_path.exists():
                            native = load_json(native_path); row["native"] = native
                            require(native["compiled_source_identity"] == identity() and native["rate"] == rate and native["block"] == block
                                    and native["window"] == candidate["window"] and native["hop"] == candidate["hop"] and native["profile"] == "Release"
                                    and not native["sanitizer"] and native["audit_available"] is True and native["shift_limit"] == 12
                                    and native["inactive_uncertain"] is True and native["voices"] == 3 and native["reserve_ms"] == 100,
                                    "Engineering source/settings mismatch")
                            validate_duration(native, protocol)
                            row["source_sha256"] = sha256(case/"render-source.f32")
                            require(not result.stderr, "Native stderr diagnostic must be investigated")
                            row["captures"] = [analyse(case/("render-"+c["name"]), native, c, protocol) for c in native["captures"]]
                            if any(c["status"] != "measured" for c in row["captures"]): row["status"] = "native_failed"
                        write_json(case/"analysis.json", row)
        indexed = {(c["engine"], c["rate"], c["block"], c["repeat"]): c for c in report["cases"]}
        def add(kind, a, a_name, b, b_name):
            a_prefix = directory/a["case"]/("render-"+a_name); b_prefix = directory/b["case"]/("render-"+b_name)
            if "native" not in a or "native" not in b: observation = {"status": "missing_native_evidence", "channels": []}
            else:
                ca = next(c for c in a["native"]["captures"] if c["name"] == a_name)
                cb = next(c for c in b["native"]["captures"] if c["name"] == b_name)
                observation = compare(a_prefix, b_prefix, ca, cb)
            report["comparisons"].append({"engine": a["engine"], "kind": kind, "a": a["case"]+"/"+a_name, "b": b["case"]+"/"+b_name, "result": observation})
        for c in report["cases"]:
            add("stopped_reconstruction", c, "cold", c, "reset")
            add("warm_process_fresh_graph", c, "cold", c, "fresh")
            add("reconstructed_vs_fresh", c, "reset", c, "fresh")
            if c["repeat"] == 0: add("independent_process", c, "cold", indexed[c["engine"], c["rate"], c["block"], 1], "cold")
            if c["repeat"] == 0 and c["block"] == 128: add("callback_partition", c, "cold", indexed[c["engine"], c["rate"], 512, 0], "cold")
        require(len(report["cases"]) == protocol["native_invocations"] == 16 and len(report["comparisons"]) == 60, "Incomplete bounded engineering set")
        verify_provenance(build, p)
        report.update(status="bounded_engineering_complete_not_product_pass", source_build_unchanged=True, summary=summarize(report["cases"], report["comparisons"]))
        # Bind all synthetic outputs, including failures; nothing is made playable.
        artifacts = {str(path.relative_to(directory)): sha256(path) for path in directory.rglob("*") if path.is_file()}
        write_json(directory/"artifacts.json", {"schema": "voxide.studio-engineering-artifacts.v1", "files_sha256": artifacts})
    except Exception as error:
        report.update(status="fail", error=str(error)); raise
    finally:
        write_json(directory/"report.json", report); print("Studio engineering evidence:", directory/"report.json", flush=True)
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, default=ROOT/"build/interaction-release")
    args = parser.parse_args(); research(args.build.resolve())


if __name__ == "__main__": main()
