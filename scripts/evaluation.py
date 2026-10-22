#!/usr/bin/env python3
"""PR 02 offline evaluation foundation. No AU/device/Logic operation or recording."""
import argparse
import datetime
from pathlib import Path
import platform
import subprocess
import sys
import uuid

from evaluation_common import (CONTRACT, FIXTURES, ROOT, finite, identifier, integer, load_json,
                               partition_controls, read_pcm, read_wav, require, sha256,
                               pcm_sha256, validate_controls, wav_identity, write_json, write_pcm)
from evaluation_contract import load_contract
from evaluation_corpus import (compare_annotations, seal_corpus, select_sources,
                               validate_annotation, validate_corpus)
from evaluation_fixtures import generate, resonator_probe, validate
from evaluation_metrics import (cents, compare_delayed, estimate_pitch, estimate_resonances,
                                measure_unity_delay, percentile, score_pitch, score_response,
                                score_control_response)


def validate_contract(path=CONTRACT):
    return load_contract(path)


def initialise_corpus(directory, contract_path=CONTRACT):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / "corpus.json", {"schema": "voxide.corpus.v1", "id": "private-vocals-001",
                                           "split_approved": False, "reviewers": [], "sources": []})
    (directory / "README.txt").write_text(
        "Private intake only. Do not upload recordings or consent documents.\n"
        "Place only recordings you permit for local Voxide evaluation here.\n"
        "Nothing is imported, annotated, split, or rights-approved automatically.\n"
        "See docs/EVALUATION.md for metadata and two-annotator instructions.\n"
        "corpus.json is an empty draft, not evidence of six singers or a holdout.\n")
    return validate_corpus(directory / "corpus.json", contract_path)


def render_control(source_path, controls_path, directory, delay, blocks, contract_path=CONTRACT):
    policy = load_contract(contract_path)
    source_hash, controls_hash = sha256(source_path), sha256(controls_path)
    info, samples = read_wav(source_path)
    require(integer(delay, 0, int(info["sample_rate"] * policy["timing_ms"]["processing_mix_ceiling"] / 1000)),
            "Control delay outside contract mixing ceiling")
    controls = load_json(controls_path)
    pcm_info, raw = read_pcm(source_path)
    require(pcm_info == info, "Source WAV changed during render")
    source_pcm = pcm_sha256(info, raw)
    events = validate_controls(controls, info, source_pcm)
    scheduled = partition_controls(events, len(samples), blocks)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    output = directory / "lead.wav"
    output_info = dict(info, frames=info["frames"] + delay)
    write_pcm(output, output_info, bytes(delay * (info["bits"] // 8)) + raw)
    _, decoded = read_wav(output)
    # Preserve input bit depth/PCM words; do not re-quantize a unity reference.
    # Compare decoded output, never only pre-encoding floating-point buffers.
    comparison = compare_delayed(samples, decoded, delay, policy)
    require(sha256(source_path) == source_hash and sha256(controls_path) == controls_hash,
            "Render inputs changed while being read")
    report = {"schema": "voxide.control-render.v1", "scope": "Offline lead copy/control scheduling; no harmonies or AU processing",
              "source_sha256": source_hash, "controls_sha256": controls_hash,
              "source_pcm_sha256": source_pcm, "contract_sha256": policy["_sha256"],
              "output_sha256": sha256(output), "sample_rate": info["sample_rate"],
              "input_frames": len(samples), "output_frames": len(decoded), "bits": info["bits"], "delay_samples": delay,
              "blocks": blocks, "events": scheduled, "lead_null": comparison,
              "harmony_rendered": False}
    write_json(directory / "render.json", report)
    return report


def score_observations(reference_path, observed_path, contract_path=CONTRACT):
    contract = load_contract(contract_path)
    reference, observed = load_json(reference_path), load_json(observed_path)
    info = {"sample_rate": reference["sample_rate"], "frames": reference["frames"]}
    validate_annotation(reference, reference["source_id"], info, policy=contract)
    require(observed.get("schema") == "voxide.pitch-observations.v2"
            and observed.get("reference_sha256") == sha256(reference_path)
            and observed.get("source_id") == reference["source_id"]
            and observed.get("source_pcm_sha256") == reference["source_pcm_sha256"]
            and observed.get("sample_rate") == info["sample_rate"]
            and observed.get("frames") == info["frames"], "Observation identity/timebase mismatch")
    require(isinstance(observed.get("producer"), dict) and identifier(observed["producer"].get("id"))
            and isinstance(observed["producer"].get("revision"), str) and observed["producer"]["revision"],
            "Missing observation producer identity/revision")
    grid = observed.get("grid")
    require(isinstance(grid, list) and grid, "Missing observation grid")
    for frame in grid:
        hz = frame.get("f0_hz")
        require(integer(frame.get("sample"), 0, info["frames"] - 1)
                and (hz is None or (finite(hz) and 0 < hz < info["sample_rate"] / 2)),
                "Invalid observed pitch/timestamp")
    result = score_pitch(reference["grid"], grid, contract["quality"]["pitch_tolerance_cents"])
    quality = contract["quality"]
    if result["status"] == "measured":
        result["threshold_status"] = "pass" if (
            result["accuracy"] >= quality["stable_accuracy_min"]
            and result["octave_error_fraction"] < quality["octave_error_fraction_max_exclusive"]) else "fail"
    else:
        result["threshold_status"] = "pending"
    return dict(result, schema="voxide.pitch-score.v1", source_id=reference["source_id"],
                reference_sha256=sha256(reference_path), observations_sha256=sha256(observed_path),
                contract_sha256=contract["_sha256"], scope="Only supplied frames; not corpus or product acceptance")


def annotation_template(audio, source_id, annotator_id, output, contract_path=CONTRACT):
    policy = load_contract(contract_path)
    require(identifier(source_id) and identifier(annotator_id), "Invalid source/annotator ID")
    info, source_pcm = wav_identity(audio)
    template = {"schema": "voxide.annotation.v2", "source_id": source_id, "source_pcm_sha256": source_pcm,
                "annotator_id": annotator_id, "origin": "human", "review_status": "draft",
                "sample_rate": info["sample_rate"], "frames": info["frames"],
                "grid": [{"sample": sample, "voiced": False, "f0_hz": None, "stable": False, "uncertain": True}
                         for sample in range(0, info["frames"], round(policy["measurement"]["frame_hop_ms"] * info["sample_rate"] / 1000))],
                "landmarks": []}
    write_json(output, template)
    return {"status": "pending", "path": str(output), "source_sha256": sha256(audio), "contract_sha256": policy["_sha256"],
            "scope": "Unreviewed template; every frame uncertain, not human annotation evidence"}


def calibrate():
    contract = validate_contract()
    catalog = validate(FIXTURES)
    reports = []
    for entry in catalog["cases"]:
        if entry["case"] not in ("sine-low", "sine-mid", "sine-high", "output-low", "output-high", "missing-fundamental", "vowel-resonances"):
            continue
        info, samples = read_wav(FIXTURES / entry["files"]["audio"]["path"])
        reference = load_json(FIXTURES / entry["files"]["reference"]["path"])
        if entry["case"] == "vowel-resonances":
            observed = estimate_resonances(samples, info["sample_rate"])
            errors = [abs(actual / expected - 1) for actual, expected in zip(observed["resonances_hz"], reference["resonances_hz"])]
            median_limit, p95_limit = (contract["quality"][key] for key in ("formant_median_fraction_max", "formant_p95_fraction_max"))
            require(percentile(errors, 0.5) <= median_limit and percentile(errors, 0.95) <= p95_limit, "Synthetic resonance calibration failed")
            faulty = resonator_probe(info["sample_rate"], info["sample_rate"], (747.5, 1265, 2817.5))
            changed = estimate_resonances(faulty, info["sample_rate"])
            fault_errors = [abs(actual / expected - 1) for actual, expected in zip(changed["resonances_hz"], reference["resonances_hz"])]
            require(percentile(fault_errors, 0.95) > p95_limit, "Wrong-resonance negative control not beyond contract limit")
            reports.append({"id": entry["id"], "measurement": observed, "fractional_errors": errors,
                            "wrong_resonance_p95": percentile(fault_errors, 0.95)})
        else:
            observed = estimate_pitch(samples, info["sample_rate"])
            error = abs(cents(observed["f0_hz"], reference["grid"][0]["f0_hz"]))
            require(error <= contract["quality"]["pitch_tolerance_cents"], "Synthetic F0 calibration failed")
            reports.append({"id": entry["id"], "measurement": observed, "absolute_cents": error})
    # Independent known faults: exact sample shifts, not self-generated candidate expectations.
    probe = [0.0] * 2048
    probe[19], probe[631], probe[1493] = 0.5, -0.125, 0.25
    delayed = [0.0] * 137 + probe
    delay = measure_unity_delay(probe, delayed, 256)
    require(delay["delay_samples"] == 137, "Delay measurement failed")
    require(compare_delayed(probe, delayed, 137, contract)["status"] == "pass", "Unity null failed")
    off_by_one = ([0.0] * 138 + probe)[:len(delayed)]
    require(compare_delayed(probe, off_by_one, 137, contract)["status"] == "fail", "Off-by-one control not detected")
    return {"schema": "voxide.calibration.v1", "status": "pass", "measurements": reports,
            "contract_sha256": contract["_sha256"],
            "known_delay_samples": delay["delay_samples"], "off_by_one_detected": True,
            "scope": "Synthetic instrument calibration only; no product/Logic/vocal qualification"}


def score_applications(reference_path, applications_path, contract_path=CONTRACT):
    policy = load_contract(contract_path)
    reference, applications = load_json(reference_path), load_json(applications_path)
    expected = validate_controls(reference)
    require(applications.get("schema") == "voxide.control-applications.v2"
            and applications.get("reference_sha256") == sha256(reference_path)
            and all(type(applications.get(key)) is type(reference[key]) and applications[key] == reference[key]
                    for key in ("source_id", "source_pcm_sha256", "sample_rate", "frames"))
            and integer(applications.get("control_interval_samples"), 1), "Control application source/timebase mismatch")
    result = score_control_response(expected, applications["events"], reference["sample_rate"],
                                    applications["control_interval_samples"], policy)
    result.update(reference_sha256=sha256(reference_path), applications_sha256=sha256(applications_path),
                  sample_rate=reference["sample_rate"], source_pcm_sha256=reference["source_pcm_sha256"])
    return result


def score_decisions(reference_path, decisions_path, contract_path=CONTRACT):
    policy = load_contract(contract_path)
    reference, decisions = load_json(reference_path), load_json(decisions_path)
    require(reference.get("schema") == "voxide.response-reference.v1"
            and decisions.get("schema") == "voxide.decisions.v1"
            and decisions.get("reference_sha256") == sha256(reference_path)
            and identifier(reference.get("source_id")) and reference["source_id"] == decisions.get("source_id")
            and integer(reference.get("sample_rate"), 1) and type(decisions.get("sample_rate")) is int
            and reference["sample_rate"] == decisions["sample_rate"]
            and reference["sample_rate"] in (44100, 48000), "Response identity/timebase mismatch")
    result = score_response(reference["events"], decisions["grid"], reference["sample_rate"], policy)
    result.update(reference_sha256=sha256(reference_path), decisions_sha256=sha256(decisions_path))
    return result


def check(directory=None):
    from check import source_fingerprint
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = Path(directory) if directory else ROOT / "build/evaluation-checks" / (stamp + "-" + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False)
    report = {"schema": "voxide.evaluation-check.v1", "status": "running", "scope": "PR02 engineering only",
              "files": source_fingerprint(), "contract_sha256": sha256(CONTRACT),
              "fixture_catalog_sha256": sha256(FIXTURES / "catalog.json"),
              "environment": {"architecture": platform.machine(), "python": sys.version},
              "acceptance_status": "pending", "acceptance_blockers": ["permitted vocal corpus not supplied",
                  "two human annotations and adjudication not completed", "independent listener availability/results not supplied",
                  "split/listening/musical-policy approval pending"], "steps": []}
    try:
        command = [sys.executable, "-m", "unittest", "discover", "-s", "scripts/tests", "-p", "test_evaluation*.py", "-v"]
        print("+", " ".join(command), flush=True)
        with (directory / "tests.log").open("x") as output:
            result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
        report["steps"].append({"command": command, "exit_code": result.returncode, "log": "tests.log"})
        require(result.returncode == 0, "Evaluation regression tests failed; see " + str(directory / "tests.log"))
        report["calibration"] = calibrate()
        report["source_unchanged"] = source_fingerprint() == report["files"]
        require(report["source_unchanged"], "Source changed during evaluation check")
        report["status"] = "pass"
    except Exception as error:
        report["status"] = "fail"
        report["error"] = str(error)
        raise
    finally:
        write_json(directory / "report.json", report)
        print("Evaluation evidence:", directory / "report.json", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT,
                        help="Explicit contract revision for scoring/QA (before the subcommand)")
    commands = parser.add_subparsers(dest="command", required=True)
    fixtures = commands.add_parser("fixtures", help="Explicit generation into a NEW directory only")
    fixtures.add_argument("--directory", type=Path, required=True)
    commands.add_parser("validate-fixtures")
    run = commands.add_parser("check")
    run.add_argument("--output-directory", type=Path)
    init = commands.add_parser("corpus-init")
    init.add_argument("--directory", type=Path, required=True)
    corpus = commands.add_parser("corpus-validate")
    corpus.add_argument("manifest", type=Path)
    annotation = commands.add_parser("annotations-compare")
    annotation.add_argument("first", type=Path)
    annotation.add_argument("second", type=Path)
    template = commands.add_parser("annotation-template")
    template.add_argument("--audio", type=Path, required=True)
    template.add_argument("--source-id", required=True)
    template.add_argument("--annotator-id", required=True)
    template.add_argument("--output", type=Path, required=True)
    seal = commands.add_parser("corpus-seal")
    seal.add_argument("manifest", type=Path)
    seal.add_argument("--settings", type=Path, required=True)
    seal.add_argument("--output", type=Path, required=True)
    select = commands.add_parser("corpus-select")
    select.add_argument("manifest", type=Path)
    select.add_argument("--split", choices=["development", "holdout"], default="development")
    select.add_argument("--allow-holdout", action="store_true")
    select.add_argument("--seal", type=Path)
    select.add_argument("--settings", type=Path)
    render = commands.add_parser("render-control")
    render.add_argument("--source", type=Path, required=True)
    render.add_argument("--controls", type=Path, required=True)
    render.add_argument("--directory", type=Path, required=True)
    render.add_argument("--delay-samples", type=int, default=0)
    render.add_argument("--blocks", default="32,64,128,257,512,1024")
    pitch = commands.add_parser("score-pitch")
    pitch.add_argument("--reference", type=Path, required=True)
    pitch.add_argument("--observations", type=Path, required=True)
    response = commands.add_parser("score-response")
    response.add_argument("--reference", type=Path, required=True)
    response.add_argument("--decisions", type=Path, required=True)
    control = commands.add_parser("score-controls")
    control.add_argument("--reference", type=Path, required=True)
    control.add_argument("--applications", type=Path, required=True)
    for name in ("compare-lead", "measure-delay"):
        comparison = commands.add_parser(name)
        comparison.add_argument("--source", type=Path, required=True)
        comparison.add_argument("--output", type=Path, required=True)
        comparison.add_argument("--delay-samples" if name == "compare-lead" else "--maximum-samples",
                                type=int, required=True)
    measurement = commands.add_parser("measure")
    measurement.add_argument("--audio", type=Path, required=True)
    measurement.add_argument("--kind", choices=["pitch", "resonances"], required=True)
    measurement.add_argument("--start", type=int, default=0)
    measurement.add_argument("--frames", type=int, default=12000)
    args = parser.parse_args()
    if args.command == "fixtures":
        result = {"directory": str(args.directory), "cases": len(generate(args.directory)["cases"])}
    elif args.command == "validate-fixtures":
        result = {"status": "pass", "cases": len(validate(FIXTURES)["cases"])}
    elif args.command == "check":
        require(args.contract == CONTRACT, "Engineering check uses the repository contract")
        check(args.output_directory)
        return
    elif args.command == "corpus-init":
        result = initialise_corpus(args.directory, args.contract)
    elif args.command == "corpus-validate":
        result = validate_corpus(args.manifest, args.contract)
    elif args.command == "annotations-compare":
        first, second = load_json(args.first), load_json(args.second)
        policy = load_contract(args.contract)
        for item in (first, second):
            validate_annotation(item, item["source_id"], {"sample_rate": item["sample_rate"], "frames": item["frames"]}, policy=policy)
        result = compare_annotations(first, second, policy)
    elif args.command == "annotation-template":
        result = annotation_template(args.audio, args.source_id, args.annotator_id, args.output, args.contract)
    elif args.command == "corpus-seal":
        seal_corpus(args.manifest, args.settings, args.output, args.contract)
        result = {"status": "sealed", "path": str(args.output)}
    elif args.command == "corpus-select":
        result = {"sources": select_sources(args.manifest, args.split, args.seal, args.settings, args.allow_holdout, args.contract)}
    elif args.command == "render-control":
        result = render_control(args.source, args.controls, args.directory, args.delay_samples,
                                [int(value) for value in args.blocks.split(",")], args.contract)
    elif args.command == "score-pitch":
        result = score_observations(args.reference, args.observations, args.contract)
    elif args.command == "score-response":
        result = score_decisions(args.reference, args.decisions, args.contract)
    elif args.command == "score-controls":
        result = score_applications(args.reference, args.applications, args.contract)
    elif args.command in ("compare-lead", "measure-delay"):
        policy = load_contract(args.contract)
        source_info, source = read_wav(args.source)
        output_info, output = read_wav(args.output)
        require(source_info["sample_rate"] == output_info["sample_rate"], "Comparison sample rates differ")
        result = (compare_delayed(source, output, args.delay_samples, policy) if args.command == "compare-lead"
                  else measure_unity_delay(source, output, args.maximum_samples))
        result.update(source_sha256=sha256(args.source), output_sha256=sha256(args.output),
                      contract_sha256=policy["_sha256"],
                      sample_rate=source_info["sample_rate"])
    else:
        policy = load_contract(args.contract)
        info, samples = read_wav(args.audio)
        require(integer(args.start) and integer(args.frames, 16) and args.start + args.frames <= len(samples),
                "Measurement window outside WAV")
        window = samples[args.start:args.start + args.frames]
        result = (estimate_pitch if args.kind == "pitch" else estimate_resonances)(window, info["sample_rate"])
        result.update(source_sha256=sha256(args.audio), start_sample=args.start, frames=args.frames,
                      contract_sha256=policy["_sha256"])
    import json
    print(json.dumps(result, indent=2, allow_nan=False))
    if (result.get("status") in ("pending", "needs_review", "fail")
            or result.get("threshold_status") in ("fail", "pending")
            or any(group["status"] == "fail" for group in result.get("groups", []))):
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(str(error))
