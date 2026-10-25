#!/usr/bin/env python3
"""Approved synthetic-only PR06A verification. Never reads private audio or plays it."""
import argparse
import array
from concurrent.futures import ProcessPoolExecutor
import math
import os
from pathlib import Path
import random
import shutil
import sys

from check import source_fingerprint
from engine_metrics import estimate_output_pitch, read_float
from evaluation_common import ROOT, contained, load_json, require, sha256, write_json
from evaluation_metrics import cents
from interaction_evaluation import stamp

EXECUTION = ROOT/"docs/evidence/pr-06a/signalsmith-verification-execution.json"
PROPOSAL = ROOT/"docs/evidence/pr-06a/signalsmith-verification-proposal.json"
SCOPE = ROOT/"docs/evidence/pr-06a/studio-scope.json"
METER_HASHES = {
    "scripts/engine_metrics.py": "8d3d0af748e062dae9bbf16b80291aebfeaaefb686a2a2fd04d747ca0a4a1e9a",
    "scripts/evaluation_metrics.py": "d78000b57994e810cad04ca3c6f465afc96e776d75c23a5842a8b5d5e0af0b7a",
}


def execution_protocol():
    p = load_json(EXECUTION)
    require(p["schema"] == "voxide.studio-verification-execution.v1" and p["id"] == "pr06a-signalsmith-stage-a-001", "Unsupported verification protocol")
    require(sha256(PROPOSAL) == p["proposal_sha256"] and sha256(SCOPE) == p["scope_sha256"], "Verification approval/proposal changed")
    require(p["meter_sources_sha256"] == METER_HASHES and all(sha256(contained(ROOT, name)) == digest for name, digest in METER_HASHES.items()), "Frozen pitch instrument changed")
    require(p["rates"] == [44100, 48000] and p["stage_caps"] == {"a1_measurement_fixtures": 36, "a2_native_captures": 72, "a3_native_captures": 16, "total_native_captures": 88}, "Unapproved verification expansion")
    c = p["calibration"]
    require(c["output_midi"] == [28, 40, 45, 57, 69, 84, 96] and c["shapes"] == ["sine", "six-harmonic"]
            and (c["positive_fixtures"], c["negative_fixtures"], c["total_fixtures"]) == (28, 8, 36), "Calibration set changed")
    require((c["primary_seconds"], c["zero_tail_seconds"], c["observer_window_samples"], c["reference_hop_ms"], c["stable_boundary_exclusion_ms"], c["search_hz"])
            == (3, .6, 8192, 10, 50, [16, 5000]), "Frozen calibration measurement changed")
    require(c["negative_controls"] == ["one-semitone-wrong-target", "octave-wrong-target", "silence", "seeded-unvoiced-noise"]
            and c["amplitude"] == .04 and c["noise_seed"] == 1448040521, "Calibration generator changed")
    expected_gates = {"pitch_tolerance_cents": 25, "stable_accuracy_min": .99, "octave_error_fraction_max_exclusive": .001, "wrong_note_duration_ms_max": 50}
    scope = load_json(SCOPE)
    require(c["gates"] == expected_gates and all(scope["retained"][key] == value for key, value in expected_gates.items()), "Retained calibration gates changed")
    return p


def calibration_cases(protocol):
    c = protocol["calibration"]
    cases = []
    for rate in protocol["rates"]:
        for midi in c["output_midi"]:
            for shape in c["shapes"]:
                cases.append({"id": f"{rate}-midi{midi}-{shape}", "rate": rate, "midi": midi, "expected_midi": midi,
                              "shape": shape, "reference_voiced": True, "kind": "positive"})
        for name in c["negative_controls"]:
            cases.append({"id": f"{rate}-{name}", "rate": rate, "midi": 57,
                          "expected_midi": 58 if name == "one-semitone-wrong-target" else 69 if name == "octave-wrong-target" else None,
                          "shape": "six-harmonic" if name.endswith("wrong-target") else "silence" if name == "silence" else "noise",
                          "reference_voiced": name.endswith("wrong-target"), "kind": name})
    require(len(cases) == 36 and len({case["id"] for case in cases}) == 36, "Incomplete/duplicate calibration cases")
    return cases


def generate(case, calibration):
    rate = case["rate"]; primary = rate*calibration["primary_seconds"]
    rng = random.Random(calibration["noise_seed"])
    hz = 440*2**((case["midi"]-69)/12)
    shape = case["shape"]
    values = []
    for i in range(primary):
        if shape == "silence": value = 0.
        elif shape == "noise": value = rng.uniform(-.02, .02)
        else:
            harmonics = (1,) if shape == "sine" else range(1, 7)
            value = sum(calibration["amplitude"]/h*math.sin(2*math.pi*h*hz*i/rate) for h in harmonics if h*hz < rate/2)
        values.append(value)
    rms = math.sqrt(sum(x*x for x in values)/primary)
    gain = min(1., 10**(-24/20)/rms) if rms else 1.
    source = array.array("f", (x*gain for x in values))
    source.extend([0.]*round(rate*calibration["zero_tail_seconds"]))
    return source, {"primary_frames": primary, "zero_tail": len(source)-primary, "source_gain": gain, "unscaled_rms": rms,
                    "generator_hz": hz if shape in ("sine", "six-harmonic") else None}


def score(observations, case, calibration):
    eligible = [r for r in observations if r["eligible"]]
    require(eligible, "No eligible observer support; calibration cannot pass")
    count = len(eligible); tolerance = calibration["gates"]["pitch_tolerance_cents"]
    detections = sum(r["observed_hz"] is not None for r in eligible)
    if not case["reference_voiced"]:
        return {"accuracy_status": "not_applicable_unvoiced_reference", "eligible_pitch_frames": 0, "correct_pitch_frames": 0,
                "within_25c_fraction": None, "false_pitch_detections": detections, "calibration_pass": detections == 0}
    good = sum(r["error_cents"] is not None and abs(r["error_cents"]) <= tolerance for r in eligible)
    octave = sum(r["error_cents"] is not None and abs(abs(r["error_cents"])-1200) <= tolerance for r in eligible)
    missing = count-detections; run = longest = 0.; previous = None
    hop = round(case["rate"]*calibration["reference_hop_ms"]/1000)
    for row in observations:
        wrong = row["eligible"] and (row["error_cents"] is None or abs(row["error_cents"]) > tolerance)
        if wrong:
            run = run+hop if previous is not None and row["source_sample"]-previous == hop else hop
            longest = max(longest, run); previous = row["source_sample"]
        else: run = 0.; previous = None
    gates = calibration["gates"]
    ordinary = good/count >= gates["stable_accuracy_min"] and octave/count < gates["octave_error_fraction_max_exclusive"]
    ordinary = ordinary and longest*1000/case["rate"] <= gates["wrong_note_duration_ms_max"]
    wrong_detected = sum(r["error_cents"] is not None and abs(r["error_cents"]) > tolerance for r in eligible)/count
    negative = case["kind"] != "positive"
    return {"accuracy_status": "sampled_analytic_reference_only", "eligible_pitch_frames": count, "correct_pitch_frames": good,
            "within_25c_fraction": good/count, "missing_estimates": missing, "octave_error_fraction": octave/count,
            "longest_sampled_wrong_note_ms": longest*1000/case["rate"], "ordinary_accuracy_gate": "pass" if ordinary else "fail",
            "wrong_target_detected_fraction": wrong_detected if negative else None,
            "calibration_pass": (not ordinary and wrong_detected >= gates["stable_accuracy_min"]) if negative else ordinary}


def measure_job(job):
    # Worker input is only a newly generated, bound build artifact, never a corpus
    # path, arbitrary CLI recording or retained private preview.
    path = contained(ROOT, job["source"])
    require(path.is_relative_to(ROOT/"build/studio-verification"), "Only generated verification inputs")
    require(sha256(path) == job["source_sha256"], "Calibration input changed")
    source, _ = read_float(path)
    case, c, primary = job["case"], job["calibration"], job["metadata"]["primary_frames"]
    native_output = job.get("input_kind", "calibration") == "native-output"
    require(job.get("input_kind", "calibration") in ("calibration", "native-output"), "Unknown measurement input kind")
    offset = job.get("delay_samples", 0)
    require(type(offset) is int and offset == (case["rate"]//10 if native_output else 0), "Only exact declared native alignment; no fitted delay")
    require(len(source) == primary+round(case["rate"]*c["zero_tail_seconds"]), "Measurement duration mismatch")
    if not native_output:
        require(all(x == 0 for x in source[primary:]), "Calibration supplied tail is nonzero")
    window = c["observer_window_samples"]; hop = round(case["rate"]*c["reference_hop_ms"]/1000)
    boundary = round(case["rate"]*c["stable_boundary_exclusion_ms"]/1000)
    observations = []
    for center in range(0, primary, hop):
        begin, end = center-window//2, center+window//2
        reason = "stable_boundary" if not boundary <= center < primary-boundary else "observer_support" if begin < 0 or end > primary else None
        estimate = {"f0_hz": None, "confidence": None}
        if reason is None: estimate = estimate_output_pitch(source[begin+offset:end+offset], case["rate"], *c["search_hz"])
        expected = 440*2**((case["expected_midi"]-69)/12) if case["expected_midi"] is not None else None
        observed = estimate["f0_hz"]
        observations.append({"source_sample": center, "window_begin": begin+offset, "window_end": end+offset, "eligible": reason is None,
                             "exclusion": reason, "observed_hz": observed, "confidence": estimate["confidence"],
                             "error_cents": cents(observed, expected) if observed and expected else None})
    require(sha256(path) == job["source_sha256"], "Calibration input changed during measurement")
    return {"case": case, "source_sha256": job["source_sha256"], "metadata": job["metadata"], "observations": observations,
            "score": score(observations, case, c), "delay_samples": offset,
            "scope": "Sampled analytic-reference measurement only; not vocal/host or full-support qualification"}


def calibrate(workers):
    require(type(workers) is int and 1 <= workers <= 6, "Use 1..6 offline measurement workers")
    protocol = execution_protocol(); digest = sha256(EXECUTION)
    directory = contained(ROOT, "build/studio-verification/"+stamp())
    claim = contained(ROOT, "build/studio-verification/claims/"+protocol["id"]+"-a1.json")
    claim.parent.mkdir(parents=True, exist_ok=True)
    write_json(claim, {"schema": "voxide.studio-verification-claim.v1", "stage": "a1", "protocol_sha256": digest,
               "run": str(directory.relative_to(ROOT)), "scope": "One 36-fixture calibration; failure does not authorize a retry"})
    directory.mkdir(parents=True, exist_ok=False)
    report = {"schema": "voxide.studio-verification.v1", "status": "failed_no_native_execution", "protocol_sha256": digest,
              "stage": "a1", "workers": workers, "python": sys.version, "cases": [], "native_executions": 0,
              "a2": "not_executed", "a3": "not_executed", "formal_product_acceptance": "pending"}
    try:
        files = source_fingerprint()
        for name, expected in files.items():
            destination = directory/"source-snapshot"/name; destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, destination); require(sha256(destination) == expected, "Source changed during calibration archival")
        write_json(directory/"provenance.json", {"files_sha256": files, "protocol_sha256": digest, "scope": "No native binaries or private sources used"})
        jobs = []
        for case in calibration_cases(protocol):
            target = directory/case["id"]; target.mkdir()
            source, metadata = generate(case, protocol["calibration"])
            path = target/"source.f32"
            with path.open("xb") as stream: stream.write(source.tobytes())
            job = {"case": case, "metadata": metadata, "calibration": protocol["calibration"], "source": str(path.relative_to(ROOT)), "source_sha256": sha256(path)}
            write_json(target/"reference.json", job); jobs.append(job)
        # Offline analysis only: never run these workers alongside native callback
        # benchmarks, builds, sanitizers or host qualification.
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for result in pool.map(measure_job, jobs):
                write_json(directory/result["case"]["id"]/"measurement.json", result)
                report["cases"].append({"id": result["case"]["id"], "score": result["score"], "source_sha256": result["source_sha256"]})
        require(len(report["cases"]) == 36 and sha256(EXECUTION) == digest and source_fingerprint() == files, "Calibration set/source/protocol changed")
        passed = all(case["score"]["calibration_pass"] for case in report["cases"])
        report.update(status="a1_calibration_pass_native_stages_pending" if passed else "a1_calibration_failed_stop_before_native", source_unchanged=True,
                      failed_cases=[case["id"] for case in report["cases"] if not case["score"]["calibration_pass"]])
    except Exception as error:
        report["error"] = str(error); raise
    finally:
        write_json(directory/"report.json", report)
        artifacts = {str(path.relative_to(directory)): sha256(path) for path in directory.rglob("*") if path.is_file()}
        write_json(directory/"artifacts.json", {"schema": "voxide.studio-verification-artifacts.v1", "files_sha256": artifacts})
        print("Synthetic verification:", (directory/"report.json").relative_to(ROOT), report["status"], flush=True)
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["calibrate"])
    parser.add_argument("--workers", type=int, default=min(6, os.cpu_count() or 1))
    args = parser.parse_args()
    directory = calibrate(args.workers)
    return 0 if load_json(directory/"report.json")["status"] == "a1_calibration_pass_native_stages_pending" else 1


if __name__ == "__main__": sys.exit(main())
