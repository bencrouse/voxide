#!/usr/bin/env python3
"""PR04 isolated native engine qualification/research. No plug-in linkage, installs or devices."""
import argparse
import array
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import uuid
import shutil
from functools import lru_cache

from check import source_fingerprint
from evaluation_common import (ROOT, FIXTURES, CONTRACT, load_json, write_json, read_wav,
                               read_wav_bytes, write_wav, sha256, require, contained, pcm_sha256,
                               read_pcm_stream)
from evaluation_contract import load_contract
from evaluation_corpus import select_sources, validate_annotation, compare_annotations
from evaluation_fixtures import validate as validate_fixtures
from evaluation_metrics import percentile
from engine_metrics import (read_float, write_float_wav, read_csv, validate_timeline, available_at,
                            callback_metrics, pitch_measurements, impulse_delay, envelope_delay,
                            ratio_settling, formant_measurements, human_reference_pitch, availability_metrics, reference_pitch_measurements)

SHIFTS = (-24, -12, -7, -3, 0, 3, 7, 12, 24)
CONFIGS = [("signalsmith", 512, 128), ("signalsmith", 1024, 256), ("signalsmith", 2048, 512),
           ("rubberband", 1, 128), ("rubberband", 2, 128)]


@lru_cache(maxsize=1)
def compiled_source_identity():
    names = sorted(["EngineEvaluation/CMakeLists.txt", "EngineEvaluation/EngineAdapter.cpp", "EngineEvaluation/EngineAdapter.h",
                    "EngineEvaluation/NativeEvaluator.cpp", "Source/Tests/AllocationAudit.cpp", "Source/Tests/AllocationAudit.h", "cmake/engine-dependencies.json"])
    return hashlib.sha256("".join(name + "|" + sha256(ROOT / name) + "\n" for name in names).encode()).hexdigest()


def verified_dependencies(build):
    from engine_dependencies import prepare
    packages = load_json(ROOT / "cmake/engine-dependencies.json")["packages"]
    return {"schema":"voxide.engine-sources.v1", "packages":[prepare(package,ROOT/".cache/dependencies",build/"_deps",offline=True) for package in packages]}


def capture_provenance(build, directory):
    """Archive the entire fingerprinted state, including dirty tracked helpers.

    The same evidence is mandatory for public analytic and private development
    renders. Private callers keep this snapshot under ignored evaluation/.
    """
    files = source_fingerprint()
    binaries = {name: build / ("voxide_" + name + "_eval") for name in ("signalsmith", "rubberband")}
    provenance = {
        "files": files, "binaries": {name: sha256(binary) for name, binary in binaries.items()},
        "allocation_audit_library_sha256": sha256(build / "libengine_allocation_audit.dylib"),
        "dependencies": verified_dependencies(build), "cmake_cache_sha256": sha256(build / "CMakeCache.txt"),
        "compiled_source_identity": compiled_source_identity(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "compiler": subprocess.check_output(["clang", "--version"], text=True).strip(),
        "sdk": subprocess.check_output(["xcrun", "--show-sdk-version"], text=True).strip(),
        "platform": platform.platform(), "contract_sha256": sha256(CONTRACT),
        "protocol_sha256": sha256(ROOT / "docs/evidence/pr-04/protocol.json"),
        "source_snapshot": "source-snapshot", "binary_snapshot": "binaries",
    }
    for name, digest in files.items():
        target = directory / "source-snapshot" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
        require(sha256(target) == digest, "Source changed while archiving snapshot")
    binary_snapshot = directory / "binaries"
    binary_snapshot.mkdir()
    for binary in [*binaries.values(), build / "libengine_allocation_audit.dylib"]:
        shutil.copyfile(binary, binary_snapshot / binary.name)
    for metadata in ("CMakeCache.txt", "compile_commands.json"):
        shutil.copyfile(build / metadata, binary_snapshot / metadata)
    verify_provenance(provenance, build)
    require(all(sha256(binary_snapshot / binary.name) == provenance["binaries"][name]
                for name, binary in binaries.items()), "Evaluator changed while archiving snapshot")
    require(sha256(binary_snapshot / "libengine_allocation_audit.dylib") == provenance["allocation_audit_library_sha256"]
            and sha256(binary_snapshot / "CMakeCache.txt") == provenance["cmake_cache_sha256"],
            "Build runtime/configuration changed while archiving snapshot")
    write_json(directory / "provenance.json", provenance)
    return provenance


def verify_provenance(provenance, build):
    require(source_fingerprint() == provenance["files"], "Source changed during engine evaluation")
    require(all(sha256(build / ("voxide_" + name + "_eval")) == digest
                for name, digest in provenance["binaries"].items()), "Evaluator binary changed during engine evaluation")
    require(sha256(build / "libengine_allocation_audit.dylib") == provenance["allocation_audit_library_sha256"],
            "Allocation audit runtime changed during engine evaluation")
    require(sha256(build / "CMakeCache.txt") == provenance["cmake_cache_sha256"]
            and verified_dependencies(build) == provenance["dependencies"],
            "Evaluator build configuration/dependency content changed during engine evaluation")


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def harmonics(rate, seconds, hz, step=False):
    count = round(rate * seconds)
    values = []
    for i in range(count):
        gain = min(1, i / max(1, round(rate * .003)), (count - 1 - i) / max(1, round(rate * .003)))
        if step and i < count // 2: gain *= .1
        phase = 2 * math.pi * hz * i / rate
        harmonic_count = max(1, min(6, int(rate * .45 / hz)))
        values.append(gain * sum(.10 / harmonic * math.sin(harmonic * phase) for harmonic in range(1, harmonic_count + 1)))
    return values


def controls_for(shifts, hz, sample=0):
    return {"sample": sample, "ratios": [2 ** (shift / 12) for shift in shifts], "source_hz": hz}


def calibrate_instruments(quick=False):
    from evaluation_metrics import estimate_resonances, measure_unity_delay
    results = []
    for rate in ((48000,) if quick else (44100, 48000)):
        for source_hz in (82.4068892282175, 220.0, 1046.5022612023945):
            for shift in ((-24, 0, 24) if quick else SHIFTS):
                target = source_hz * 2 ** (shift / 12)
                perfect = harmonics(rate, 1, target)
                metric = pitch_measurements(perfect, 0, len(perfect), target, rate)
                results.append({"instrument": "pitch", "rate": rate, "target_hz": target,
                                "status": "pass" if metric["eligible_frames"] > 0 and metric["within_25c_fraction"] == 1 else "fail", "measurement": metric})
        info, resonator = read_wav(FIXTURES / ("vowel-resonances-" + str(rate) + ".wav"))
        measured = estimate_resonances(resonator, rate)["resonances_hz"]
        errors = [abs(actual - expected) / expected for actual, expected in zip(measured, (650,1100,2450))]
        results.append({"instrument": "resonances", "rate": rate, "status": "pass" if max(errors) < .05 else "fail", "fraction_errors": errors})
        impulse = [0.0] * (rate // 10); impulse[rate // 100] = .25
        for delay in (1, round(rate * .01)):
            measured = measure_unity_delay(impulse, [0.0] * delay + impulse, rate)["delay_samples"]
            results.append({"instrument": "unity_delay", "rate": rate, "expected_samples": delay, "measured_samples": measured,
                            "status": "pass" if measured == delay else "fail"})
    return {"scope": "Known perfect analytic controls only; no candidate output or human truth used to calibrate the instrument", "results": results,
            "status": "pass" if all(row["status"] == "pass" for row in results) else "fail"}


def sources(directory, rate):
    output = {}
    for name, hz in (("tone-low", 82.4068892282175), ("tone-mid", 220.0), ("tone-high", 1046.5022612023945)):
        values = harmonics(rate, 1, hz)
        path = directory / (name + "-" + str(rate) + ".wav")
        write_wav(path, rate, values)
        output[name] = {"path": path, "hz": hz, "kind": "steady", "origin": "pr04-analytic-v1"}
    for name, duration, kind in (("dynamic", 1.8, "dynamic"), ("envelope-step", .8, "envelope")):
        path = directory / (name + "-" + str(rate) + ".wav")
        write_wav(path, rate, harmonics(rate, duration, 220, step=kind == "envelope"))
        output[name] = {"path": path, "hz": 220, "kind": kind, "origin": "pr04-analytic-v1"}
    values = [0.0] * (rate // 4); values[rate // 16] = .25
    path = directory / ("impulse-" + str(rate) + ".wav"); write_wav(path, rate, values)
    output["impulse"] = {"path": path, "hz": 0, "kind": "impulse", "origin": "pr04-analytic-v1"}
    for entry in load_json(FIXTURES / "catalog.json")["cases"]:
        if entry["sample_rate"] != rate or entry["case"].startswith("output-"): continue
        reference_bytes = (FIXTURES / entry["files"]["reference"]["path"]).read_bytes()
        require(hashlib.sha256(reference_bytes).hexdigest() == entry["files"]["reference"]["sha256"], "Frozen reference changed before use")
        reference = json.loads(reference_bytes)
        voiced = [row["f0_hz"] for row in reference["grid"] if row["voiced"] and not row["uncertain"]]
        name = "frozen-" + entry["case"]
        output[name] = {"path": FIXTURES / entry["files"]["audio"]["path"],
                        "hz": voiced[0] if voiced else 0,
                        "kind": "formants" if entry["case"] == "vowel-resonances" else "stress",
                        "origin": "frozen-pr02", "resonances": reference["resonances_hz"], "reference_grid":reference["grid"]}
    for value in output.values(): value["sha256"] = sha256(value["path"])
    return output


def trials(quick=False):
    for rate in ((48000,) if quick else (44100, 48000)):
        configs = CONFIGS[::4] if quick else CONFIGS
        for engine, window, hop in configs:
            for source in ("tone-low", "tone-mid", "tone-high"):
                for shift in ((0, 24) if quick else SHIFTS):
                    for voices in (1, 3):
                        yield rate, engine, window, hop, source, voices, [shift] * 3, False
            for shift in ((12,) if quick else SHIFTS):
                for voices in (1, 3):
                    yield rate, engine, window, hop, "frozen-vowel-resonances", voices, [shift] * 3, False
            for voices in (1, 3):
                yield rate, engine, window, hop, "dynamic", voices, [0] * 3, True
                yield rate, engine, window, hop, "impulse", voices, [0] * 3, False
                for shift in ((12,) if quick else (-24, 0, 24)):
                    yield rate, engine, window, hop, "envelope-step", voices, [shift] * 3, False
            if not quick:
                for source in ("sine-low", "sine-mid", "sine-high", "missing-fundamental", "pitch-step", "glide", "vibrato", "noise-bursts", "silence", "level-step", "bleed"):
                    yield rate, engine, window, hop, "frozen-" + source, 3, [-12, 0, 12], False


def run_native(binary, config, values, rate, voices, events, directory, blocks="128"):
    directory.mkdir(parents=True, exist_ok=False)
    control_path = directory / "oracle.txt"
    with control_path.open("x") as stream:
        for event in events:
            stream.write(str(event["sample"]) + " " + " ".join(format(x, ".17g") for x in (*event["ratios"], event["source_hz"])) + "\n")
    prefix = directory / "render"
    args = [str(binary), str(rate), str(config[0]), str(config[1]), str(voices), str(control_path), str(prefix), blocks]
    pcm = array.array("f", values)
    require(sys.byteorder == "little" and pcm.itemsize == 4, "Requires native little-endian float32")
    result = subprocess.run(args, input=pcm.tobytes(), capture_output=True)
    (directory / "native-stdout.txt").write_bytes(result.stdout)
    (directory / "native-stderr.txt").write_bytes(result.stderr)
    write_json(directory / "invocation.json", {"command": args, "return_code": result.returncode,
               "input_float32_sha256": hashlib.sha256(pcm.tobytes()).hexdigest(), "frames": len(values)})
    if result.returncode:
        return None
    native = load_json(str(prefix) + "-native.json")
    require(native["source_frames"] == len(values) and native["sample_rate"] == rate and native["voices"] == voices
            and native["profile"] == "Release" and native["sanitizer"] == "" and native["audit_available"],
            "Native render/build identity mismatch; only unsanitized, audited Release evidence is accepted")
    require(native["compiled_source_identity"] == compiled_source_identity(), "Stale evaluator binary: rebuild against the current sources")
    require(native.get("configured_window") == config[0] and native.get("configured_hop") == config[1]
            and native.get("engine") == ("signalsmith" if config[0] >= 512 else "rubberband-r3"), "Unexpected native engine/configuration")
    timelines = validate_timeline(native, read_csv(str(prefix) + "-availability.csv"), read_csv(str(prefix) + "-controls.csv"), events)
    samples = []
    for voice in range(voices):
        audio, payload = read_float(str(prefix) + "-voice" + str(voice + 1) + ".f32")
        require(len(audio) == native["instances"][voice]["output_frames"], "Missing/truncated native stem")
        write_float_wav(directory / ("voice" + str(voice + 1) + ".wav"), rate, payload)
        samples.append(audio)
    return native, timelines, samples


def analyze_render(native, timelines, outputs, source, values, rate, events, quality):
    callbacks = read_csv(source["case_directory"] / "render-callbacks.csv")
    measures = {"callback": callback_metrics(callbacks, rate, native["audit_available"], quality,
                native["source_frames"]+native["zero_tail_supplied"]), "voices": []}
    for voice, audio in enumerate(outputs):
        info = native["instances"][voice]; offset = info["nominal_output_offset"]
        peak = max((abs(x) for x in audio), default=0)
        active = [i for i, x in enumerate(audio) if abs(x) > 1e-7]
        item = {"voice": voice, "output_frames": len(audio), "peak": peak, "over_unity_peak": peak >= 1,
                "last_nonzero_output_sample": active[-1] if active else None,
                "source_plus_nominal_delay_frames": len(values) + offset,
                "post_source_tail_peak": max((abs(x) for x in audio[len(values) + offset:]), default=0),
                "cold_output_first_nonzero": active[0] if active else None,
                "cold_nonzero_available_at": available_at(timelines[voice], active[0]) if active else None}
        item["nominal_grid_availability"] = availability_metrics(timelines[voice],offset,len(values),rate)
        source_rms = math.sqrt(sum(float(x)**2 for x in values) / len(values))
        begin = offset + round(rate*.05); end = min(len(audio),offset+len(values)-round(rate*.05))
        aligned_rms = math.sqrt(sum(float(x)**2 for x in audio[begin:end]) / (end-begin)) if end > begin else None
        item["artifact_proxies"] = {"maximum_adjacent_sample_step": max((abs(float(b)-a) for a,b in zip(audio,audio[1:])),default=0),
            "aligned_output_rms": aligned_rms,"source_rms":source_rms,
            "rms_ratio_to_source": aligned_rms / source_rms if aligned_rms is not None and source_rms > 0 else None,
            "scope":"Raw peak/step/energy/tail proxies only; not listening ratings, click detection or a perceptual acceptance gate"}
        if source["kind"] == "steady":
            item["pitch"] = pitch_measurements(audio, offset, len(values), source["hz"] * events[0]["ratios"][voice], rate)
        elif source["kind"] == "impulse":
            try: item["unity_delay"] = impulse_delay(values, audio, timelines[voice], offset, rate)
            except ValueError as error: item["unity_delay"] = {"status": "failed", "reason": str(error)}
        elif source["kind"] == "envelope":
            item["envelope_delay"] = envelope_delay(audio, timelines[voice], len(values), offset, rate)
        elif source["kind"] == "dynamic":
            item["ratio_settling"] = ratio_settling(audio, timelines[voice], events, voice, offset, rate)
        elif source["kind"] == "formants":
            try: item["formants"] = formant_measurements(audio, offset, len(values), rate, source["resonances"])
            except ValueError as error: item["formants"] = {"status": "failed", "reason": str(error)}
        elif source["kind"] == "stress":
            item["source_grid_pitch"] = reference_pitch_measurements(audio,source["reference_grid"],events[0]["ratios"][voice],
                offset,len(values),rate,window=4096,provenance="Frozen analytic source-grid truth, not a human vocal reference")
        measures["voices"].append(item)
    measures["reset"] = {key: native[key] for key in ("reset_allocations", "reset_vs_fresh_max_abs", "reset_vs_fresh_rms", "reset_silence_peak", "reset_overlap")}
    return measures


def private_sources(corpus_path, directory, binaries, policy, build=None):
    """Development only; require actual, completed, agreeing human references."""
    from io import BytesIO
    snapshot = corpus_path.read_bytes(); data = json.loads(snapshot)
    selected = select_sources(corpus_path, split="development")
    require(corpus_path.read_bytes() == snapshot, "Private manifest changed during validation")
    directory.mkdir(parents=True, exist_ok=False)
    provenance = capture_provenance(build, directory) if build is not None else None
    records = []
    for index, source in enumerate(source for source in data["sources"] if source["id"] in selected):
        record = {"index": index + 1, "source_id": source["id"], "source_sha256": source["audio"]["sha256"],
                  "status": "pending_human_references"}
        annotations = source.get("annotations", [])
        if len(annotations) != 2:
            records.append(record); continue
        path = contained(corpus_path.parent, source["audio"]["path"])
        encoded = path.read_bytes()
        require(hashlib.sha256(encoded).hexdigest() == source["audio"]["sha256"], "Unregistered private audio bytes")
        info, values = read_wav_bytes(encoded)
        pcm_info, pcm = read_pcm_stream(BytesIO(encoded)); pcm_digest = pcm_sha256(pcm_info, pcm)
        references = []
        for item in annotations:
            content = contained(corpus_path.parent, item["path"]).read_bytes()
            require(hashlib.sha256(content).hexdigest() == item["sha256"], "Unregistered private annotation bytes")
            references.append(validate_annotation(json.loads(content), source["id"], info, pcm_digest, policy))
        if any(ref["origin"] != "human" or ref.get("review_status") != "completed" for ref in references) or compare_annotations(*references, policy=policy)["status"] != "agreement":
            records.append(record); continue
        grid = []
        for a, b in zip(references[0]["grid"], references[1]["grid"]):
            certain = a["voiced"] and b["voiced"] and not a["uncertain"] and not b["uncertain"]
            grid.append({"sample": a["sample"], "hz": math.sqrt(a["f0_hz"] * b["f0_hz"]) if certain else 0,
                         "stable": certain and a["stable"] and b["stable"],
                         "voiced": a["voiced"] and b["voiced"], "uncertain": a["uncertain"] or b["uncertain"]})
        record["certain_voiced_reference_frames"] = sum(row["hz"] > 0 for row in grid)
        record["stable_voiced_reference_frames"] = sum(row["hz"] > 0 and row["stable"] for row in grid)
        if not record["certain_voiced_reference_frames"]:
            record["reason"] = "Completed annotations contain no certain voiced F0; no pitch truth fabricated"
            records.append(record); continue
        rendered = []
        for engine, window, hop in CONFIGS:
            for shift in SHIFTS:
                events = [controls_for([shift] * 3, row["hz"], row["sample"]) for row in grid]
                case = directory / (f"source{index + 1}-{engine}-{window}-{shift:+d}")
                result = run_native(binaries[engine], (window, hop), values, info["sample_rate"], 3, events, case)
                if result:
                    native, _, outputs = result
                    frame_reference = [dict(row, f0_hz=row["hz"] if row["voiced"] else None) for row in grid]
                    metrics = [human_reference_pitch(output, frame_reference, events[0]["ratios"][voice],
                               native["instances"][voice]["nominal_output_offset"], len(values), info["sample_rate"])
                               for voice, output in enumerate(outputs)]
                    write_json(case / "reviewed-reference-pitch.json", {"voices": metrics, "product_qualification": "pending"})
                rendered.append({"directory": case.name, "status": "rendered" if result else "native_failed"})
        require(sha256(path) == source["audio"]["sha256"], "Private source changed during evaluation")
        record.update(status="reference_ready", renders=rendered,
                      successful_renders=sum(row["status"] == "rendered" for row in rendered),
                      annotation_sha256=[item["sha256"] for item in annotations],
                      scope="Completed agreeing references supply engine formant prior; no real-vocal formant truth, listening or product pass implied")
        records.append(record)
    if provenance is not None:
        verify_provenance(provenance, build)
    write_json(directory / "private-report.json", {"schema": "voxide.private-engine-development.v1", "sources": records,
               "corpus_manifest_sha256": hashlib.sha256(snapshot).hexdigest(),
               "provenance": "provenance.json" if provenance is not None else None,
               "source_build_unchanged": True if provenance is not None else None})
    return {"sources": len(records), "reference_ready_sources": sum(row["status"] == "reference_ready" for row in records),
            "evidence": str((directory / "private-report.json").relative_to(ROOT)), "scope": "Development only; no holdout or fabricated human annotations"}


def research(build, quick=False, corpus=None):
    directory = ROOT / "build/engine-research" / stamp(); directory.mkdir(parents=True, exist_ok=False)
    source_directory = directory / "sources"; source_directory.mkdir()
    policy = load_contract()
    binaries = {name: build / ("voxide_" + name + "_eval") for name in ("signalsmith", "rubberband")}
    provenance = capture_provenance(build, directory)
    report = dict(provenance, **{"schema": "voxide.engine-research.v1", "status": "running", "quick_incomplete_coverage": quick,
        "cases": [],
        "scope": "Isolated oracle controls, not product/tracker/human/listening/live Logic qualification",
        "remaining_human_gates": "Actual completed references and listeners required; expressive clip c retained, not flattened or excluded",
        "generator": "pr04-analytic-v1", "private_development": None})
    report["pitch_instrument"] = "offline-nacf-interpolated-peaks-v1"
    try:
        protocol = load_json(ROOT/"docs/evidence/pr-04/protocol.json")
        require(protocol["shifts_semitones"] == list(SHIFTS) and protocol["full_matrix_cases"] == sum(1 for _ in trials()), "Declared oracle protocol/matrix mismatch")
        validate_fixtures(FIXTURES)
        report["instrument_calibration"] = calibrate_instruments(quick)
        require(report["instrument_calibration"]["status"] == "pass", "Independent instruments failed known-truth calibration; candidate grading refused")
        inputs = {rate: sources(source_directory, rate) for rate in ((48000,) if quick else (44100, 48000))}
        for number, (rate, engine, window, hop, name, voices, shifts, dynamic) in enumerate(trials(quick)):
            source = inputs[rate][name]
            require(sha256(source["path"]) == source["sha256"], "Source changed before render")
            encoded = source["path"].read_bytes()
            require(hashlib.sha256(encoded).hexdigest() == source["sha256"], "Source snapshot differs from declared PCM input")
            info, values = read_wav_bytes(encoded)
            if dynamic:
                events = [controls_for([shift, -shift, SHIFTS[(index + 3) % len(SHIFTS)]], source["hz"], round(index * rate / 5)) for index, shift in enumerate(SHIFTS)]
            elif "reference_grid" in source:
                events = []
                for frame in source["reference_grid"]:
                    hz = frame["f0_hz"] if frame["voiced"] and not frame["uncertain"] else 0
                    if not events or events[-1]["source_hz"] != hz:
                        events.append(controls_for(shifts,hz,frame["sample"]))
            else: events = [controls_for(shifts, source["hz"])]
            case = directory / f"case-{number:04d}-{engine}-{window}-{rate}-{name}-v{voices}"
            result = run_native(binaries[engine], (window, hop), values, rate, voices, events, case)
            record = {"case": case.name, "engine": engine, "window": window, "hop": hop, "rate": rate, "source": name,
                      "source_origin":source["origin"],"source_path":str(source["path"].relative_to(ROOT)),
                      "voices": voices, "shifts": shifts, "dynamic": dynamic, "source_sha256": source["sha256"],
                      "render_status": "rendered" if result else "native_failed"}
            if result:
                native, timeline, audio = result
                record["measurements"] = analyze_render(native, timeline, audio, dict(source, case_directory=case), values, rate, events, policy["quality"])
                record["native_report_sha256"] = sha256(case / "render-native.json")
                if dynamic:
                    repeated = run_native(binaries[engine], (window, hop), values, rate, voices, events, case / "fresh-repeat", blocks="32,64,128,257,512,1024")
                    differences = []
                    if repeated:
                        repeated_native, _, repeated_audio = repeated
                        for voice, (a, b) in enumerate(zip(audio, repeated_audio)):
                            same_length = len(a) == len(b)
                            maximum = max((abs(float(x) - y) for x, y in zip(a, b)), default=0) if same_length else None
                            rms = math.sqrt(sum((float(x) - y) ** 2 for x, y in zip(a, b)) / len(a)) if same_length and a else None
                            same_input = native["instances"][voice]["native_input_hash"] == repeated_native["instances"][voice]["native_input_hash"]
                            require(same_input, "Host partition changed fixed-quantum native inputs")
                            differences.append({"voice": voice, "same_length": same_length, "same_native_input": same_input, "max_abs": maximum, "rms": rms,
                                "within_frozen_tolerance": same_length and maximum <= policy["deterministic_tolerance"]["max_abs"] and rms <= policy["deterministic_tolerance"]["rms"]})
                    record["fresh_repeat"] = {"status": "compared" if repeated else "native_failed", "voices": differences,
                                               "scope": "Fresh native process and mixed host partitions; raw repeats retained"}
            report["cases"].append(record)
            require(sha256(source["path"]) == source["sha256"], "Source changed during render")
            if number % 25 == 0: print("Engine research cases:", number + 1, flush=True)
        if corpus:
            private = ROOT / "evaluation/pr-04" / directory.name
            report["private_development"] = private_sources(corpus, private, binaries, policy, build=build)
        verify_provenance(provenance, build)
        report["source_unchanged"] = True
        require(len(report["cases"]) == sum(1 for _ in trials(quick)), "Incomplete declared engine matrix")
        report["native_failed_cases"] = sum(row["render_status"] != "rendered" for row in report["cases"])
        report["configuration_summary"] = summarize_configurations(report["cases"], policy)
        report["engine_selection"] = "No product engine selected; pending human/host/architecture gates and retained candidate failures"
        report["status"] = "research_complete_not_product_pass"
    except Exception as error:
        report["status"] = "fail"; report["error"] = str(error); raise
    finally:
        write_json(directory / "report.json", report)
        print("Engine research evidence:", directory / "report.json", flush=True)
    return directory / "report.json"


def summarize_configurations(cases, policy):
    groups = {}
    for case in cases:
        key = (case["engine"],case["window"],case["rate"],case["voices"])
        group = groups.setdefault(key,{"engine":key[0],"window":key[1],"rate":key[2],"voices":key[3],
            "attempted_cases":0,"native_failed_cases":[],"pitch_failed_cases":[],"formant_failed_cases":[],
            "allocating_callback_cases":[],"overdue_callback_cases":[],"repeat_failed_cases":[],"reset_failed_cases":[],
            "occupancy_target_missed_cases":[],"unity_query_mismatch_cases":[],
            "source_grid_pitch_failed_cases":[],"source_grid_pitch_observations":[],
            "unresolved_ratio_observations":[],"ratio_settling_observations":[],"unresolved_envelope_observations":[],
            "unity_delays_ms":[],"envelope_delays_ms":[],"callback_ns_max":0,"callback_occupancy_p999_max":0})
        group["attempted_cases"] += 1
        if case["render_status"] != "rendered": group["native_failed_cases"].append(case["case"]); continue
        measurement = case["measurements"]; callback = measurement["callback"]
        group["callback_ns_max"] = max(group["callback_ns_max"],callback["ns_max"])
        group["callback_occupancy_p999_max"] = max(group["callback_occupancy_p999_max"],callback["occupancy_p999"])
        if callback["allocation_calls"]: group["allocating_callback_cases"].append(case["case"])
        if callback["overdue_callbacks"]: group["overdue_callback_cases"].append(case["case"])
        if not callback["occupancy_target_met_on_this_run_only"]: group["occupancy_target_missed_cases"].append(case["case"])
        repeat = case.get("fresh_repeat")
        if repeat and (repeat["status"] != "compared" or any(not row["within_frozen_tolerance"] for row in repeat["voices"])):
            group["repeat_failed_cases"].append(case["case"])
        reset = measurement["reset"]
        if (reset["reset_vs_fresh_max_abs"] is None or reset["reset_vs_fresh_rms"] is None
            or reset["reset_vs_fresh_max_abs"] > policy["deterministic_tolerance"]["max_abs"]
            or reset["reset_vs_fresh_rms"] > policy["deterministic_tolerance"]["rms"] or reset["reset_silence_peak"] > 1e-6):
            group["reset_failed_cases"].append(case["case"])
        pitch_failed = formant_failed = False
        for voice in measurement["voices"]:
            pitch = voice.get("pitch")
            if pitch and (pitch["within_25c_fraction"] is None or pitch["within_25c_fraction"] < policy["quality"]["stable_accuracy_min"]): pitch_failed = True
            grid = voice.get("source_grid_pitch")
            if grid:
                stable = grid["groups"]["stable"]
                group["source_grid_pitch_observations"].append({"case":case["case"],"voice":voice["voice"],
                    "stable":stable,"expressive_unstable":grid["groups"]["expressive_unstable"],"excluded":grid["excluded"],
                    "scope":"Descriptive analytic stress probe; stress-pitch guarantee remains pending"})
                if stable["frames"] and (stable["within_25c_fraction"] is None or stable["within_25c_fraction"] < policy["quality"]["stable_accuracy_min"]):
                    pitch_failed = True
                    if case["case"] not in group["source_grid_pitch_failed_cases"]: group["source_grid_pitch_failed_cases"].append(case["case"])
            for event in voice.get("ratio_settling",{}).get("events",[]):
                observation = dict(event,case=case["case"],voice=voice["voice"],
                    status="measured" if event["settled"] and event["settled"].get("available_source_sample") is not None else "unresolved",
                    scope="Observer-inclusive, not intrinsic engine latency or a product timing verdict")
                group["ratio_settling_observations"].append(observation)
                if observation["status"] == "unresolved": group["unresolved_ratio_observations"].append(observation)
            envelope = voice.get("envelope_delay")
            if envelope and (envelope["status"] != "measured" or envelope.get("causal_threshold_delay_ms") is None):
                group["unresolved_envelope_observations"].append(dict(envelope,case=case["case"],voice=voice["voice"],
                    scope="Unresolved envelope observation; not by itself an intrinsic engine-latency failure"))
            formants = voice.get("formants")
            if formants and (formants["status"] != "measured" or formants["median_fraction_error"] > policy["quality"]["formant_median_fraction_max"]
                             or formants["p95_fraction_error"] > policy["quality"]["formant_p95_fraction_max"]): formant_failed = True
            if "unity_delay" in voice and voice["unity_delay"].get("causal_peak_delay_ms") is not None:
                group["unity_delays_ms"].append(voice["unity_delay"]["causal_peak_delay_ms"])
            if "unity_delay" in voice and (voice["unity_delay"].get("status") == "failed" or voice["unity_delay"].get("query_error_samples") != 0):
                if case["case"] not in group["unity_query_mismatch_cases"]: group["unity_query_mismatch_cases"].append(case["case"])
            if "envelope_delay" in voice and voice["envelope_delay"].get("causal_threshold_delay_ms") is not None:
                group["envelope_delays_ms"].append(voice["envelope_delay"]["causal_threshold_delay_ms"])
        if pitch_failed: group["pitch_failed_cases"].append(case["case"])
        if formant_failed: group["formant_failed_cases"].append(case["case"])
    for group in groups.values():
        group["scope"] = "Descriptive analytic configuration evidence, not singer/listener acceptance. All failed case IDs retained; no averaging them away."
        group["retained_for_research"] = True
    return list(groups.values())


def check(args):
    directory = ROOT / "build/engine-checks" / stamp(); directory.mkdir(parents=True, exist_ok=False)
    files = source_fingerprint()
    report = {"schema": "voxide.engine-check.v1", "status": "running", "files": files, "steps": [],
              "platform": platform.platform(), "profiles": [], "scope": "Native isolated evaluators only; no install/devices/Logic or architecture acceptance"}
    report["research_coverage"] = "not_run" if args.no_research else "quick_incomplete" if args.quick else "full_930_case_matrix"
    def run(label, command, env=None):
        step = {"label": label, "command": command, "log": label + ".log"}
        report["steps"].append(step)
        with (directory / step["log"]).open("x") as output:
            result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, cwd=ROOT, env=env)
        step["exit_code"] = result.returncode
        if result.returncode: raise RuntimeError((directory / step["log"]).read_text())
    try:
        profiles = ("debug", "release", "asan", "tsan") if args.full else ("release",)
        for profile in profiles:
            build = ROOT / "build" / ("engine-" + profile)
            report["profiles"].append(profile)
            sanitizer = {"asan": "address", "tsan": "thread"}.get(profile, "")
            run(profile + "-configure", ["cmake", "-S", "EngineEvaluation", "-B", str(build),
                "-DCMAKE_BUILD_TYPE=" + ("Release" if profile == "release" else "Debug"), "-DVOXIDE_SANITIZER=" + sanitizer,
                "-DVOXIDE_OFFLINE=" + ("ON" if args.offline else "OFF"), "-DPython3_EXECUTABLE=" + sys.executable])
            run(profile + "-build", ["cmake", "--build", str(build), "--parallel", str(args.jobs)])
            env = dict(os.environ)
            if profile == "asan": env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1"
            if profile == "tsan": env["TSAN_OPTIONS"] = "halt_on_error=1"
            previous_reports = set((build / "test-output").glob("*/report.json"))
            run(profile + "-test", ["ctest", "--test-dir", str(build), "--output-on-failure", "--no-tests=error"], env)
            new_reports = sorted(set((build / "test-output").glob("*/report.json")) - previous_reports)
            require(len(new_reports) == 2, "Missing isolated adapter/engine-gate reports")
            report.setdefault("adapter_and_native_gates", {})[profile] = [dict(load_json(path), evidence=str(path.relative_to(ROOT))) for path in new_reports]
            report.setdefault("binaries", {})[profile] = {name: sha256(build / ("voxide_" + name + "_eval")) for name in ("signalsmith", "rubberband")}
            report.setdefault("dependencies", {})[profile] = load_json(build / "_deps/engine-sources.json")
        if not args.no_research:
            report["research"] = str(research(ROOT / "build/engine-release", quick=args.quick, corpus=args.development_corpus).relative_to(ROOT))
        require(source_fingerprint() == files, "Source changed during engine checks")
        report["source_unchanged"] = True; report["status"] = "pass"
    except Exception as error:
        report["status"] = "fail"; report["error"] = str(error); raise
    finally:
        write_json(directory / "report.json", report); print("Engine check evidence:", directory / "report.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "research", "private"))
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--no-research", action="store_true", help="Native tests only; not complete PR04 qualification")
    parser.add_argument("--quick", action="store_true", help="Explicit incomplete smoke matrix, never full coverage")
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--development-corpus", type=Path, help="Explicit private corpus, development selection only; completed human references required for renders")
    args = parser.parse_args()
    require(args.jobs > 0, "Positive job count required")
    if args.development_corpus:
        args.development_corpus = args.development_corpus.resolve()
        require(args.development_corpus.is_relative_to(ROOT / "evaluation"), "Private corpus must remain under ignored evaluation/")
    if args.command == "check": check(args)
    elif args.command == "research": research(ROOT / "build/engine-release", quick=args.quick, corpus=args.development_corpus)
    else:
        require(args.development_corpus is not None, "Private development requires an explicit registered corpus")
        build = ROOT / "build/engine-release"
        binaries = {name:build/("voxide_"+name+"_eval") for name in ("signalsmith","rubberband")}
        result = private_sources(args.development_corpus,ROOT/"evaluation/pr-04"/stamp(),binaries,load_contract(),build=build)
        print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
