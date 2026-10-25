#!/usr/bin/env python3
"""Bounded, approved synthetic PR06A native checks. No private source or playback route."""
import argparse
import array
from concurrent.futures import ProcessPoolExecutor
import json
import math
from pathlib import Path
import struct
import subprocess

from engine_metrics import callback_metrics, read_csv, read_float
from evaluation_common import ROOT, contained, load_json, require, sha256, write_json
from interaction_evaluation import CHANNELS, identity, provenance, verify_provenance, stamp
from studio_validation import control_coverage, fixed_sum_checks, listening_timeline, studio_clocks
from studio_verification import EXECUTION, execution_protocol, generate, measure_job

VOICINGS = {
    "octaves": ((0, 0, 0), (-1, 0, 1)),
    "upper": ((2, 4, 0), (0, 0, 1)),
    "lower": ((-2, -4, 0), (0, 0, -1)),
}
MASK64 = (1 << 64)-1


def fnv(words):
    value = 14695981039346656037
    for word in words: value = ((value ^ word)*1099511628211) & MASK64
    return str(value)


def intervals(midi, voicing):
    # Independent analytic C-major expectation, not selector output or tracker F0.
    notes = (0, 2, 4, 5, 7, 9, 11)
    anchor = min(range(-21, 85), key=lambda d: (abs(12*(d//7)+notes[d % 7]-midi), d))
    def at(degree): return 12*(degree//7)+notes[degree % 7]
    degrees, octaves = VOICINGS[voicing]
    return [at(anchor+d)-at(anchor)+12*o for d, o in zip(degrees, octaves)]


def steady_cases():
    return [{"id": f"{rate}-midi{midi}-{shape}-{voicing}-{mode}", "rate": rate, "midi": midi, "shape": shape,
             "voicing": voicing, "mode": mode, "intervals": intervals(midi, voicing)}
            for rate in (44100, 48000) for midi in (40, 57, 84) for shape in ("sine", "six-harmonic")
            for voicing in VOICINGS for mode in ("prescribed", "tracked-scale")]


def prerequisite():
    protocol = execution_protocol()
    claim = contained(ROOT, "build/studio-verification/claims/"+protocol["id"]+"-a1.json")
    run = contained(ROOT, load_json(claim)["run"])
    require(run.is_relative_to(ROOT/"build/studio-verification"), "Calibration outside synthetic evidence root")
    report = load_json(run/"report.json")
    require(report["status"] == "a1_calibration_pass_native_stages_pending" and report["source_unchanged"]
            and report["protocol_sha256"] == sha256(EXECUTION) and len(report["cases"]) == 36
            and all(c["score"]["calibration_pass"] for c in report["cases"]), "A1 must pass before native execution")
    for name, digest in load_json(run/"artifacts.json")["files_sha256"].items():
        require(sha256(contained(run, name)) == digest, "Calibration artifact changed")
    old = load_json(run/"provenance.json")["files_sha256"]
    require(sha256(ROOT/"scripts/studio_verification.py") == old["scripts/studio_verification.py"], "Calibrated measurement driver changed")
    return protocol, run


def event_text(case):
    if case["mode"] == "tracked-scale":
        degrees, octaves = VOICINGS[case["voicing"]]
        return "0 0 H 0 0 2741 "+" ".join(map(str, (*degrees, *octaves)))+"\n"
    hz = 440*2**((case["midi"]-69)/12)
    targets = [case["midi"]+shift for shift in case["intervals"]]
    return f"0 0 P {hz:.17g} 1 1 0 0\n0 0 T "+" ".join(map(str, targets))+" 7\n"


def oracle_timeline(native, rows, case):
    """Oracle-only SS2048 transport contract; never used to authorize a preview."""
    rate, total = case["rate"], native["output_frames"]
    clocks = studio_clocks(rate, 2048, 512, "signalsmith"); clocks["analysis"] = 0
    require(native["analysis_delay_samples"] == 0, "Oracle unexpectedly used a tracker reserve")
    required = set("kind epoch wall source voice requested available frame_begin frame_end frame_available hz confidence voiced active target_midi requested_shift applied_shift weight first_output count request_kind".split())
    require(rows and all(required <= row.keys() for row in rows), "Missing oracle telemetry columns")
    require(all(int(r["kind"]) in (0, 1, 2) and int(r["epoch"]) == 0 and 0 <= int(r["wall"]) <= total for r in rows), "Invalid oracle telemetry")
    require(all(int(a["wall"]) <= int(b["wall"]) for a, b in zip(rows, rows[1:])), "Unordered oracle telemetry")
    for row in rows:
        require(all(math.isfinite(float(row[key])) for key in ("hz", "confidence", "target_midi", "requested_shift", "applied_shift", "weight")), "Nonfinite oracle telemetry")
    requests = [r for r in rows if int(r["kind"]) == 2]
    require([(int(r["request_kind"]), int(r["requested"]), int(r["wall"]), int(r["available"])) for r in requests]
            == [(0, 0, 0, 0), (1, 0, 0, 0)], "Oracle requests differ from causal P/T-at-zero events")
    controls = [r for r in rows if int(r["kind"]) == 0]
    checks = control_coverage(controls, rate=rate, total=total, clocks=clocks)
    hz = 440*2**((case["midi"]-69)/12)
    for row in controls:
        source = int(row["source"]); voice = int(row["voice"])
        require(all(int(row[k]) == 0 for k in ("frame_begin", "frame_end", "frame_available", "requested", "available")), "Oracle frame/request was backdated or fabricated")
        require(int(row["request_kind"]) == (1 if source >= 0 else 0), "Wrong oracle request application")
        if source >= 0:
            require(int(row["voiced"]) == int(row["active"]) == 1 and float(row["confidence"]) == 1
                    and abs(float(row["hz"])-hz) < 1e-9 and abs(float(row["target_midi"])-(case["midi"]+case["intervals"][voice])) < 1e-9,
                    "Oracle did not apply independently prescribed F0/targets")
    quanta = total//512
    for voice in range(3):
        packets = [r for r in rows if int(r["kind"]) == 1 and int(r["voice"]) == voice]
        require(len(packets) == quanta+1, "Incomplete oracle output stream")
        for index, row in enumerate(packets):
            wall, count = ((index+1)*512-1, 512) if index < quanta else (total, 1024)
            require((int(row["wall"]), int(row["count"]), int(row["first_output"]), int(row["available"]))
                    == (wall, count, index*512-2048, min(total, (wall//128+1)*128)), "Noncausal/incomplete oracle output packet")
            first = max(0, int(row["first_output"]))
            if int(row["first_output"])+count > first and first < total-native["latency_samples"]:
                require(wall <= first+native["latency_samples"], "Oracle output missed delivery deadline")
        require(native["voices"][voice]["native_frames"] == quanta*512+1024, "Oracle native-frame counter mismatch")
    require(sum(int(r["kind"]) == 1 for r in rows) == 3*(quanta+1), "Unknown oracle output voice")
    return controls, checks


def safety(case, native, outputs, source, rows):
    rate = case["rate"]; primary = rate*3; total = rate*18//5; delay = rate//10
    require((native["engine"], native["sample_rate"], native["window"], native["hop"], native["mode"], native["treatment"], native["reserve_profile"])
            == ("signalsmith", rate, 2048, 512, 0 if case["mode"] == "prescribed" else 2, 0, 1), "Unexpected native configuration")
    require(native["shift_limit"] == 12 and native["inactive_uncertain"] is True and native["source_frames"] == primary
            and native["zero_tail"] == rate*3//5 and native["output_frames"] == total and native["latency_samples"] == delay, "Native guards/duration/delay mismatch")
    require(set(outputs) == set(CHANNELS) and all(len(x) == total for x in outputs.values()), "Missing native channel frames")
    require(all(math.isfinite(x) for audio in outputs.values() for x in audio), "Nonfinite native channel")
    require(len(source) == total and all(x == 0 for x in source[primary:]), "Generated input duration/tail mismatch")
    require(len(native["voices"]) == 3 and all(v["underflows"] == v["late_samples"] == 0 for v in native["voices"]), "Native delivery failure")
    require(all(native[key] == 0 for key in ("missing_metadata", "fifo_overflow", "bad_events", "late_controls", "telemetry_dropped", "invalid_input"))
            and native["unrendered_finish_peak"] <= 1e-6, "Native controls/finish failure")
    nulls = {}
    for name, offset in (("lead-direct", 0), ("lead-aligned", delay)):
        errors = [float(value)-(source[i-offset] if i >= offset else 0) for i, value in enumerate(outputs[name])]
        nulls[name] = {"max_abs": max(map(abs, errors)), "rms": math.sqrt(sum(x*x for x in errors)/total)}
        require(nulls[name]["max_abs"] <= 1e-6 and nulls[name]["rms"] <= 1e-7, "Native lead null failed")
    sums = fixed_sum_checks(outputs["lead-direct"], outputs["lead-aligned"], [outputs["voice"+str(v+1)] for v in range(3)], outputs)
    require(all(r["max_abs"] <= 1e-6 and r["rms"] <= 1e-7 for r in sums.values()), "Native fixed sum failed")
    require(max(abs(x) for audio in outputs.values() for x in audio) < 1, "Native full-scale over; no normalization/repair")
    require(all(max(map(abs, outputs["voice"+str(v+1)])) > 1e-6 for v in range(3)), "Silent native harmony")
    controls, timeline = oracle_timeline(native, rows, case) if case["mode"] == "prescribed" else listening_timeline(native, rows, {"engine": "signalsmith", "window": 2048, "hop": 512})
    clocks = studio_clocks(rate, 2048, 512, "signalsmith")
    analysis = 0 if case["mode"] == "prescribed" else clocks["analysis"]
    fed = (total-analysis)//512*512
    words = array.array("I"); words.frombytes(source.tobytes()[:fed*4]); expected_input = fnv(words)
    for voice in range(3):
        applied = [r for r in controls if int(r["voice"]) == voice]
        control_words = [struct.unpack("<Q", struct.pack("<d", value))[0] for r in applied
                         for value in (float(r["applied_shift"]), float(r["hz"]) if int(r["voiced"]) else 0.)]
        require(native["voices"][voice]["native_input_hash"] == expected_input
                and native["voices"][voice]["control_hash"] == fnv(control_words), "Native input/control hash does not match serialized evidence")
    return {"lead_null": nulls, "fixed_sum": sums, "timeline": timeline, "input_hash": expected_input}, controls


def control_diagnostics(case, controls):
    result = []
    for voice, interval in enumerate(case["intervals"]):
        rows = [r for r in controls if int(r["voice"]) == voice and case["rate"]*.05 <= int(r["source"]) < case["rate"]*2.95
                and int(r["frame_end"]) <= case["rate"]*3]
        require(rows, "Missing stable analytic control observations")
        source_good = active = 0; selector = requested = applied = absolute_target = 0.
        for row in rows:
            hz = float(row["hz"])
            source_midi = 69+12*math.log2(hz/440) if hz > 0 else None
            valid = int(row["voiced"]) == 1 and source_midi is not None
            source_good += bool(valid and abs(source_midi-case["midi"])*100 <= 25)
            active += int(row["active"])
            if valid:
                selector = max(selector, abs(float(row["target_midi"])-source_midi-interval))
                absolute_target = max(absolute_target, abs(float(row["target_midi"])-case["midi"]-interval)*100)
                if int(row["active"]):
                    requested = max(requested, abs(float(row["requested_shift"])-interval))
                    applied = max(applied, abs(float(row["applied_shift"])-interval))
        passed = source_good/len(rows) >= .99 and active/len(rows) >= .99 and max(selector, requested, applied) <= 1e-6
        result.append({"voice": voice, "analytic_control_frames": len(rows), "source_within_25c_fraction": source_good/len(rows),
                       "active_fraction": active/len(rows), "selector_interval_max_error_semitones": selector,
                       "requested_shift_max_error_semitones": requested, "applied_shift_max_error_semitones": applied,
                       "absolute_target_max_error_cents": absolute_target, "pass": passed})
    return {"voices": result, "pass": all(row["pass"] for row in result),
            "scope": "Known constant synthetic source/scale truth, not self-scoring tracker output or a vocal reference"}


def steady(build, workers):
    require(type(workers) is int and 1 <= workers <= 6, "Use 1..6 measurement workers")
    cases = steady_cases()
    require(len(cases) == 72 and len({case["id"] for case in cases}) == 72, "Native capture cap/count mismatch before execution")
    protocol, calibration = prerequisite()
    build = contained(ROOT, str(Path(build).absolute().relative_to(ROOT)))
    require(build.is_relative_to(ROOT/"build"), "Only existing isolated build directories")
    directory = contained(ROOT, "build/studio-verification/"+stamp())
    claim = contained(ROOT, "build/studio-verification/claims/"+protocol["id"]+"-a2.json")
    claim.parent.mkdir(parents=True, exist_ok=True)
    write_json(claim, {"schema": "voxide.studio-verification-claim.v1", "stage": "a2", "protocol_sha256": sha256(EXECUTION), "run": str(directory.relative_to(ROOT)), "native_capture_cap": 72})
    directory.mkdir(parents=True, exist_ok=False)
    report = {"schema": "voxide.studio-verification.v1", "stage": "a2", "status": "a2_failed_stop_before_a3", "cases": [],
              "calibration": str(calibration.relative_to(ROOT)), "calibration_report_sha256": sha256(calibration/"report.json"),
              "protocol_sha256": sha256(EXECUTION), "native_executions": 0, "a3": "not_executed", "formal_product_acceptance": "pending"}
    try:
        p = provenance(build, directory)
        binary = build/"voxide_signalsmith_interaction"
        description = subprocess.run([str(binary), "--describe"], capture_output=True, timeout=30)
        require(description.returncode == 0 and not description.stderr, "Cannot attest native evaluator")
        capabilities = json.loads(description.stdout)
        require(capabilities["compiled_source_identity"] == identity() and capabilities["engine"] == "signalsmith"
                and capabilities["profile"] == "Release" and not capabilities["sanitizer"] and capabilities["audit_available"] is True,
                "Wrong/stale/sanitized evaluator")
        commands = load_json(build/"compile_commands.json")
        selected = [row["command"] for row in commands if "voxide_signalsmith_interaction.dir" in row["command"]]
        require(selected and all("SIGNALSMITH_USE_ACCELERATE=1" in command for command in selected), "Unapproved Signalsmith backend")
        cached = {}; jobs = []
        for case in cases:
            key = (case["rate"], case["midi"], case["shape"])
            if key not in cached:
                source, metadata = generate(case, protocol["calibration"])
                path = directory/(f"input-{case['rate']}-{case['midi']}-{case['shape']}.f32")
                with path.open("xb") as stream: stream.write(source.tobytes())
                cached[key] = source, metadata, path
            source, metadata, path = cached[key]
            target = directory/case["id"]; target.mkdir()
            events = target/"events.txt"
            with events.open("x") as stream: stream.write(event_text(case))
            command = [str(binary), str(case["rate"]), "2048", "512", "0" if case["mode"] == "prescribed" else "2", "0", "1", str(events), str(target/"render"), "128", str(case["rate"]*3//5), "12", "1"]
            write_json(target/"settings.json", {"case": case, "source_sha256": sha256(path), "source_metadata": metadata, "lead_gain": 1, "harmony_gain_each": 1/3, "command": command})
            require(report["native_executions"] < 72, "Native capture cap exceeded")
            row = {"case": case, "status": "native_running"}; report["cases"].append(row); report["native_executions"] += 1
            result = subprocess.run(command, input=source[:metadata["primary_frames"]].tobytes(), capture_output=True, timeout=120)
            (target/"stdout.txt").write_bytes(result.stdout); (target/"stderr.txt").write_bytes(result.stderr)
            row["return_code"] = result.returncode
            require(result.returncode == 0 and not result.stderr, "Native execution failed; no retry")
            native = load_json(target/"render-native.json")
            require(native["compiled_source_identity"] == identity() and native["profile"] == "Release" and not native["sanitizer"] and native["audit_available"], "Native result identity mismatch")
            outputs = {name: read_float(target/("render-"+name+".f32"))[0] for name in CHANNELS}
            checks, controls = safety(case, native, outputs, source, read_csv(target/"render-telemetry.csv"))
            callback = callback_metrics(read_csv(target/"render-callbacks.csv"), case["rate"], True, {"callback_occupancy_p999_max_exclusive": .5}, len(source))
            require(callback["allocation_calls"] == 0 and callback["occupancy_target_met_on_this_run_only"], "Native callback gate failed; no retry")
            row.update(status="engineering_checks_passed_pitch_pending", checks=checks, callback=callback, voices=[], control_diagnostics=control_diagnostics(case, controls))
            write_json(target/"controls.json", {"scope": "Complete raw controls; analytic expected targets are independent", "rows": controls})
            for voice, shift in enumerate(case["intervals"]):
                job = {"case": {**case, "id": case["id"]+f"-voice{voice+1}", "kind": "positive", "reference_voiced": True, "expected_midi": case["midi"]+shift},
                       "metadata": metadata, "calibration": protocol["calibration"], "input_kind": "native-output", "delay_samples": case["rate"]//10,
                       "source": str((target/("render-voice"+str(voice+1)+".f32")).relative_to(ROOT)), "source_sha256": sha256(target/("render-voice"+str(voice+1)+".f32"))}
                write_json(target/(f"voice{voice+1}-reference.json"), job); jobs.append(job)
        require(report["native_executions"] == len(cases) == 72, "Native capture cap/count mismatch")
        # All native callback measurements finish before parallel offline FFT work.
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for index, measurement in enumerate(pool.map(measure_job, jobs)):
                row = report["cases"][index//3]; target = directory/row["case"]["id"]
                write_json(target/(f"voice{index%3+1}-measurement.json"), measurement)
                row["voices"].append(measurement["score"])
        verify_provenance(build, p)
        require(sha256(EXECUTION) == report["protocol_sha256"], "Verification protocol changed")
        failed = []
        for row in report["cases"]:
            passed = len(row["voices"]) == 3 and all(v["ordinary_accuracy_gate"] == "pass" for v in row["voices"]) and row["control_diagnostics"]["pass"]
            row["status"] = "sampled_steady_checks_passed" if passed else "sampled_steady_pitch_failed"
            if not passed: failed.append(row["case"]["id"])
        report.update(status="a2_sampled_steady_pass_a3_pending" if not failed else "a2_pitch_failed_stop_before_a3", failed_cases=failed, source_build_unchanged=True)
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        write_json(directory/"report.json", report)
        write_json(directory/"artifacts.json", {"schema": "voxide.studio-verification-artifacts.v1", "files_sha256": {str(path.relative_to(directory)): sha256(path) for path in directory.rglob("*") if path.is_file()}})
        print("Synthetic steady verification:", (directory/"report.json").relative_to(ROOT), report["status"], flush=True)
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["steady"])
    parser.add_argument("--build", type=Path, default=ROOT/"build/interaction-release")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    directory = steady(args.build, args.workers)
    return 0 if load_json(directory/"report.json")["status"] == "a2_sampled_steady_pass_a3_pending" else 1


if __name__ == "__main__": raise SystemExit(main())
