#!/usr/bin/env python3
"""Evaluate the compiled causal tracker, never an offline pitch estimator as truth.

Frozen analytic assets are read-only. Optional private development audio produces
ungraded traces only; this command cannot open a holdout/corpus automatically.
"""
import argparse
import array
import bisect
import csv
import datetime
import io
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import uuid

from check import source_fingerprint
from evaluation_common import read_wav, read_wav_bytes, load_json, sha256, write_json, require
from evaluation_metrics import cents, percentile, wilson
from evaluation_corpus import select_sources

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "Source/Tests/Fixtures/pr02"


def validate_frames(frames, sample_count, timing):
    support, hop, first = (timing[key] for key in ("support_samples", "hop_samples", "first_available"))
    require(all(isinstance(x, int) and not isinstance(x, bool) and x > 0 for x in (support, hop, first)), "Invalid probe timing")
    require(first == math.ceil(support / hop) * hop, "Invalid first decision time")
    expected = range(first, sample_count + 1, hop)
    require(len(frames) == len(expected), "Missing/truncated/extra probe decisions")
    for frame, available in zip(frames, expected):
        require(frame["available"] == frame["end"] == available and frame["begin"] == available - support,
                "Invalid probe cadence or causal support")
        require(all(math.isfinite(frame[k]) for k in ("hz", "confidence", "rms")), "Non-finite estimate")
        require(frame["voiced"] in (0, 1) and 0 <= frame["confidence"] <= 1 and frame["rms"] >= 0
                and frame["hz"] >= 0 and (not frame["voiced"] or frame["hz"] > 0), "Invalid pitch/voicing decision")


def run_probe(binary, samples, rate, variant, timing):
    pcm = array.array("f", samples)
    require(pcm.itemsize == 4 and sys.byteorder == "little", "Probe requires little-endian float32 input")
    result = subprocess.run([str(binary), str(rate), variant], input=pcm.tobytes(), capture_output=True, check=True)
    raw = result.stdout.decode()
    frames = [{key: (int(value) if key in ("begin", "end", "available", "voiced", "block_end", "block_ns") else float(value))
               for key, value in row.items()} for row in csv.DictReader(io.StringIO(raw))]
    validate_frames(frames, len(samples), timing)
    return raw, frames


def at_or_before(frames, sample, hop_samples):
    # available is a consumed-sample count; grid sample i exists after i+1 samples.
    index = bisect.bisect_right([f["available"] for f in frames], sample + 1) - 1
    frame = frames[index] if index >= 0 else None
    return frame if frame is not None and sample + 1 - frame["available"] < hop_samples else None


def summarize(frames, reference, rate, hop_samples=None):
    hop_samples = max(1, round(rate * .005)) if hop_samples is None else hop_samples
    voiced = correct = missing = octave = false_voiced = unvoiced = uncertain = 0
    errors = []
    for row in reference:
        if row.get("uncertain", False):
            uncertain += 1
            continue
        estimate = at_or_before(frames, row["sample"], hop_samples)
        is_voiced = estimate is not None and estimate["voiced"] != 0
        if not row["voiced"]:
            unvoiced += 1
            false_voiced += is_voiced
        elif row["stable"]:
            voiced += 1
            if not is_voiced:
                missing += 1
                continue
            error = abs(cents(estimate["hz"], row["f0_hz"]))
            errors.append(error)
            correct += error <= 25
            octave_multiple = round(error / 1200)
            octave += octave_multiple >= 1 and abs(error - 1200 * octave_multiple) <= 25
    return {"stable_voiced_reference_frames": voiced, "within_25c_frames": correct,
            "stable_accuracy": correct / voiced if voiced else None,
            "stable_accuracy_wilson95_descriptive": wilson(correct, voiced),
            "missing_or_unvoiced_frames": missing, "octave_error_frames": octave,
            "absolute_cents_median": percentile(errors, .5) if errors else None,
            "absolute_cents_p95": percentile(errors, .95) if errors else None,
            "unvoiced_reference_frames": unvoiced, "false_voiced_frames": false_voiced,
            "uncertain_reference_frames_excluded": uncertain,
            "scope": "Source-grid available decisions, no backdating; missing estimates stay in denominator"}


def response(frames, events, hz_at, rate, hop_samples=None):
    """Time the correct 20 ms dwell COMPLETES, not when it starts."""
    hop_samples = max(1, round(rate * .005)) if hop_samples is None else hop_samples
    results = []
    for onset, end, label in events:
        start = None
        settled = None
        previous = None
        for frame in frames:
            t = frame["available"]
            # An exclusive-end decision at onset has consumed none of the event.
            if t <= onset or t > end:
                continue
            if previous is not None and t - previous != hop_samples:
                start = None
            previous = t
            truth = hz_at(min(end - 1, t - 1))
            good = frame["voiced"] and truth is not None and abs(cents(frame["hz"], truth)) <= 25
            if not good:
                start = None
            elif start is None:
                start = t
            elif t - start >= math.ceil(rate * .020):
                settled = (t - onset) * 1000 / rate
                break
        results.append({"onset_sample": onset, "end_sample": end, "kind": label,
                        "source_hz_at_onset": hz_at(onset),
                        "dwell_completed_ms": settled, "missing_response": settled is None})
    return results


def aggregate(records, policy):
    groups = []
    for variant in ("yin", "multi"):
        for register in (40, 48, 60, 72, 84):
            rows = [row for row in records if row["variant"] == variant and row.get("midi_register") == register]
            total = sum(row["metrics"]["stable_voiced_reference_frames"] for row in rows)
            good = sum(row["metrics"]["within_25c_frames"] for row in rows)
            timing = {}
            for kind in ("cold", "continuous", "rhythmic-bend"):
                events = [event for row in rows for event in row["responses"] if event["kind"] == kind]
                values = [event["dwell_completed_ms"] for event in events if not event["missing_response"]]
                p95 = percentile(values, .95) if values else None
                bands = {}
                for event in events:
                    hz = event["source_hz_at_onset"]
                    require(hz is not None and math.isfinite(hz) and hz > 0, "Response event lacks source-onset F0 truth")
                    band = "low" if hz < policy["timing_ms"]["recognition_boundary_hz"] else "high"
                    bands.setdefault(band, []).append(event)
                requirements = {}
                for band, observations in bands.items():
                    completed = [event["dwell_completed_ms"] for event in observations if not event["missing_response"]]
                    limit = policy["timing_ms"]["recognition_" + band + "_p95"]
                    observed = percentile(completed, .95) if completed else None
                    requirements[band] = {"events": len(observations), "missing": len(observations) - len(completed),
                        "completed_dwell_p95_ms": observed, "required_p95_ms": limit,
                        "meets_target_on_this_probe_only": observed is not None and observed <= limit and len(completed) == len(observations)}
                timing[kind] = {"events": len(events), "missing": len(events) - len(values),
                                "completed_dwell_p95_ms": p95,
                                "required_recognition_p95_ms": next(iter(requirements.values()))["required_p95_ms"] if len(requirements) == 1 else None,
                                "by_source_register": requirements,
                                "meets_target_on_this_probe_only": bool(requirements) and all(group["meets_target_on_this_probe_only"] for group in requirements.values())}
            groups.append({"variant": variant, "midi_register": register,
                           "stable_accuracy": good / total if total else None,
                           "stable_voiced_frames": total,
                           "octave_error_frames": sum(row["metrics"]["octave_error_frames"] for row in rows),
                           "false_voiced_frames_including_boundaries": sum(row["metrics"]["false_voiced_frames"] for row in rows),
                           "timing": timing})
    return groups


def analytic_cases(rate):
    """Deterministic development stress probes, separate from frozen PR02 assets."""
    for midi in (40, 48, 60, 72, 84):
        hz = 440 * 2 ** ((midi - 69) / 12)
        length = int(.6 * rate)
        change = int(.2 * rate)
        for kind in ("cold", "continuous", "missing-fundamental", "rhythmic-bend"):
            samples = []
            truth = []
            phase = 0
            for i in range(length):
                target = hz * (2 ** ((-3 if midi == 84 else 3) / 12) if kind == "continuous" and i >= change else 1)
                active = True
                if kind == "rhythmic-bend":
                    position = i % int(.15 * rate)
                    active = int(.015 * rate) <= position < int(.12 * rate)
                    elapsed = max(0, position / rate - .015)
                    vibrato = 30 * math.sin(2 * math.pi * 5 * elapsed)
                    bend = -180 * math.exp(-elapsed / .025) + vibrato
                    # Shape edge-register probes inside support; never flatten
                    # an excursion by clipping its expressive trajectory.
                    if midi == 40: bend = 180 * math.exp(-elapsed / .025) + 30 + vibrato
                    if midi == 84: bend -= 30
                    target *= 2 ** (bend / 1200)
                phase += 2 * math.pi * target / rate
                harmonics = (2, 3, 4) if kind == "missing-fundamental" else (1, 2, 3, 4)
                value = sum(.12 / harmonic * math.sin(harmonic * phase) for harmonic in harmonics) if active else 0
                samples.append(value)
                truth.append(target if active else None)
            if kind == "continuous":
                events = [(change, length, "continuous")]
            elif kind == "rhythmic-bend":
                events = [(int(.15 * rate) * n + int(.015 * rate), min(length, int(.15 * rate) * n + int(.12 * rate)), "rhythmic-bend") for n in range(4)]
            else:
                events = [(0, length, "cold")]
            grid = []
            hop = round(rate * .01)
            boundaries = [a for a, _, _ in events] + [b for _, b, _ in events]
            if kind == "continuous": boundaries.append(0)
            for i in range(0, length, hop):
                grid.append({"sample": i, "voiced": truth[i] is not None, "f0_hz": truth[i],
                             "stable": all(abs(i - boundary) >= .05 * rate for boundary in boundaries)})
            yield f"dev-{kind}-midi{midi}-{rate}", samples, grid, truth, events, midi
    # Deterministic non-periodic unvoiced control; no random-package dependency.
    state = 0x564f5849
    samples = []
    for _ in range(int(.6 * rate)):
        state = (1664525 * state + 1013904223) & 0xffffffff
        samples.append((state / 0xffffffff * 2 - 1) * .1)
    grid = [{"sample": i, "voiced": False, "f0_hz": None, "stable": False} for i in range(0, len(samples), round(rate * .01))]
    yield f"dev-noise-{rate}", samples, grid, [None] * len(samples), [], None


def permitted_development(corpus_path):
    snapshot = corpus_path.read_bytes()
    corpus = json.loads(snapshot)
    development_ids = select_sources(corpus_path, split="development")
    require(corpus_path.read_bytes() == snapshot, "Development manifest changed during validation")
    return {(corpus_path.parent / source["audio"]["path"]).resolve(): source["audio"]["sha256"]
            for source in corpus["sources"] if source["id"] in development_ids}


def approved_private_audio(path, expected_digest):
    # Hash and decode the SAME immutable byte snapshot, not separate path reads.
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == expected_digest, "Private source differs from registered digest")
    info, samples = read_wav_bytes(data)
    require(sha256(path) == expected_digest, "Private source changed during decoding")
    return info, samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "build/local-release/voxide_tracking_probe")
    parser.add_argument("--private-development", type=Path, action="append", default=[], help="Explicitly approved private WAV; trace only, never ground truth")
    parser.add_argument("--development-corpus", type=Path, help="Required with private inputs; existing permission/split/hash validator is enforced")
    args = parser.parse_args()
    binary = args.binary.resolve()
    permitted = {}
    if args.private_development:
        require(args.development_corpus is not None, "Private inputs require a registered development corpus")
        corpus_path = args.development_corpus.resolve()
        permitted = permitted_development(corpus_path)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    directory = ROOT / "build/tracking-checks" / stamp
    directory.mkdir(parents=True, exist_ok=False)
    files = source_fingerprint()
    report = {"schema": "voxide.causal-tracking-research.v2", "status": "running", "files": files,
              "analytic_development_generator": "pr03-analytic-v2-unclipped-bends",
              "binary": str(binary.relative_to(ROOT)), "binary_sha256": sha256(binary),
              "python": sys.version, "platform": platform.platform(),
              "numerical_contract_sha256": sha256(ROOT / "docs/evidence/pr-02/contract.json"),
              "musical_contract_sha256": sha256(ROOT / "docs/evidence/pr-03/musical-contract.json"),
              "protocol_approval": "pending; descriptive development research only",
              "product_qualification": "blocked: real-vocal references/listeners/live evidence incomplete",
              "timing_scope": "128-sample native probe, tracker+default selector only; excludes processor/host/I/O; not live monitoring acceptance",
              "metrics": [], "private_ungraded": []}
    private_results = []
    try:
        timings = {rate: json.loads(subprocess.check_output([str(binary), "--describe", str(rate)])) for rate in (44100, 48000)}
        report["probe_timing"] = timings
        (directory / "scale-catalog.json").write_bytes(subprocess.check_output([str(binary), "--scales"]))
        catalog = load_json(FIXTURES / "catalog.json")
        for variant in ("yin", "multi"):
            for entry in catalog["cases"]:
                for asset in entry["files"].values():
                    require(sha256(FIXTURES / asset["path"]) == asset["sha256"], "Frozen asset changed")
                info, samples = read_wav(FIXTURES / entry["files"]["audio"]["path"])
                reference = load_json(FIXTURES / entry["files"]["reference"]["path"])
                # Apply the frozen 50 ms boundary exclusion without changing assets.
                boundaries = [0, info["frames"]] + [landmark["sample"] for landmark in reference.get("landmarks", [])]
                grid = [dict(row, stable=row["stable"] and all(abs(row["sample"] - b) >= .05 * info["sample_rate"] for b in boundaries))
                        for row in reference["grid"]]
                # Output-range probes are NOT within E2-C6 source support; retain
                # raw outputs but do not misgrade their octaves as supported input.
                supported = not entry["case"].startswith("output-")
                raw, frames = run_probe(binary, samples, info["sample_rate"], variant, timings[info["sample_rate"]])
                (directory / f"{variant}-{entry['id']}.csv").write_text(raw)
                metrics = summarize(frames, grid, info["sample_rate"], timings[info["sample_rate"]]["hop_samples"]) if supported else None
                report["metrics"].append({"id": entry["id"], "variant": variant, "source": "frozen-analytic", "input_supported": supported, "metrics": metrics})
            for rate in (44100, 48000):
                for name, samples, grid, truth, events, midi in analytic_cases(rate):
                    raw, frames = run_probe(binary, samples, rate, variant, timings[rate])
                    (directory / f"{variant}-{name}.csv").write_text(raw)
                    metrics = summarize(frames, grid, rate, timings[rate]["hop_samples"])
                    responses = response(frames, events, lambda i: truth[i], rate, timings[rate]["hop_samples"])
                    callbacks = {f["block_end"]: f["block_ns"] for f in frames}
                    metrics["analysis_callback_ns_max"] = max(callbacks.values(), default=None)
                    report["metrics"].append({"id": name, "variant": variant, "source": "analytic-development", "input_supported": True,
                                              "midi_register": midi, "metrics": metrics, "responses": responses})
            for index, path in enumerate(args.private_development):
                path = path.resolve()
                private = ROOT / "evaluation"
                require(path.is_relative_to(private), "Private development inputs must stay under ignored evaluation/")
                require(path in permitted, "Private input is not a registered permitted development source; holdout access is not supported")
                before = permitted[path]
                info, samples = approved_private_audio(path, before)
                raw, frames = run_probe(binary, samples, info["sample_rate"], variant, timings[info["sample_rate"]])
                # Derived traces also remain private, not in the generic report directory.
                target = private / "pr-03" / stamp
                target.mkdir(parents=True, exist_ok=True)
                (target / f"{variant}-development-{index + 1}.csv").write_text(raw)
                require(sha256(path) == before, "Private source changed")
                private_results.append({"variant": variant, "input_sha256": before,
                    "trace": str((target / f"{variant}-development-{index + 1}.csv").relative_to(ROOT)), "frames": len(frames),
                    "accuracy_and_intended_notes": "not graded; no reliable human reference", "source_unchanged": True})
        report["per_register_development_summary"] = aggregate(report["metrics"], load_json(ROOT / "docs/evidence/pr-02/contract.json"))
        if private_results:
            target = ROOT / "evaluation/pr-03" / stamp
            write_json(target / "ungraded-report.json", {"schema": "voxide.private-causal-traces.v1", "sources": private_results,
                "scope": "Development traces only, not intended-note/pitch truth; no source modified or uploaded"})
            report["private_ungraded"] = {"trace_count": len(private_results), "evidence": str((target / "ungraded-report.json").relative_to(ROOT)),
                "accuracy": "ungraded; no reliable human reference"}
        report["source_unchanged"] = source_fingerprint() == files
        require(report["source_unchanged"], "Source changed during evaluation")
        require(sha256(binary) == report["binary_sha256"], "Probe binary changed during evaluation")
        report["status"] = "research_complete_not_product_pass"
    except Exception as error:
        report["status"] = "fail"
        report["error"] = str(error)
        raise
    finally:
        write_json(directory / "report.json", report)
        print("Tracking evidence:", directory / "report.json")


if __name__ == "__main__":
    main()
