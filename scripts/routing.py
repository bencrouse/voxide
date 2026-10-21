#!/usr/bin/env python3
"""Explicit local PR 01 fixtures/evidence. Never opens Logic, devices, or records PCM."""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import plistlib
import struct
import subprocess
import sys
import uuid
import wave

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def variable_length(value):
    result = [value & 0x7f]
    while value >> 7:
        value >>= 7
        result.insert(0, (value & 0x7f) | 0x80)
    return bytes(result)


def prepare(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    rate = 48000
    samples = []
    for i in range(rate * 8):
        # Two distinctive low-level phrases separated by silence; no microphone.
        seconds = i / rate
        amplitude = 0.0625 if 0.5 <= seconds < 3.0 or 4.0 <= seconds < 7.0 else 0.0
        frequency = 220 if seconds < 4.0 else 330
        # Short fade prevents start/end clicks. Signals are only routing probes.
        phase_start, phase_end = (0.5, 3.0) if seconds < 4 else (4.0, 7.0)
        fade = max(0.0, min(1.0, (seconds - phase_start) / 0.01, (phase_end - seconds) / 0.01))
        samples.append(round(32767 * amplitude * fade * math.sin(2 * math.pi * frequency * seconds)))
    audio = directory / "routing-probe.wav"
    with wave.open(str(audio), "wb") as stream:
        stream.setparams((1, 2, rate, len(samples), "NONE", "not compressed"))
        stream.writeframes(struct.pack("<" + "h" * len(samples), *samples))
    events = [(0, bytes.fromhex("ff510307a120"))]
    expected = []
    for tick, note in ((1, 60), (271, 64), (739, 67), (1253, 62), (2129, 65), (2899, 69)):
        events.extend([(tick, bytes([0x90, note, 80])), (tick + 133, bytes([0x80, note, 0]))])
        expected.extend([{"tick": tick, "status": 0x90, "note": note},
                         {"tick": tick + 133, "status": 0x80, "note": note}])
    events.extend([(3600, bytes([0xb0, 123, 0])), (3840, bytes.fromhex("ff2f00"))])
    events.sort(key=lambda event: event[0])
    track = bytearray()
    previous = 0
    for tick, payload in events:
        track.extend(variable_length(tick - previous))
        track.extend(payload)
        previous = tick
    midi = directory / "routing-probe.mid"
    midi.write_bytes(b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
                     + b"MTrk" + struct.pack(">I", len(track)) + track)
    manifest = {
        "schema": "voxide.routing-fixtures.v1", "sample_rate": rate, "duration_seconds": 8,
        "audio_duration_seconds": 8, "midi_duration_seconds": 4,
        "source": "generated controlled signal, NOT a vocal recording", "bpm": 120,
        "ppq": 480, "midi_events": sorted(expected, key=lambda event: event["tick"]),
        "files": {audio.name: digest(audio), midi.name: digest(midi)},
    }
    (directory / "fixtures.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def analyze(path, require_audio=False, require_midi=False, require_offsets=False,
            require_notes=False, require_released=False):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if len(rows) < 3 or rows[0].get("schema") != "voxide.routing.v1" or rows[-1].get("kind") != "end":
        raise ValueError("Incomplete or unsupported diagnostic capture")
    events = rows[1:-1]
    if not events or any(row.get("kind") not in ("audio", "midi") for row in events):
        raise ValueError("Missing/invalid diagnostic events")
    sequences = [row["sequence"] for row in events]
    if any(b != a + 1 for a, b in zip(sequences, sequences[1:])):
        raise ValueError("Diagnostic sequence gap or out-of-order records")
    if rows[-1].get("dropped_during_capture") != 0:
        raise ValueError("Capture overflowed; repeat the test")
    if rows[-1].get("last_sequence") != sequences[-1]:
        raise ValueError("Capture footer does not match its last event")
    if rows[-1].get("dropped_records_total", -1) != rows[0].get("dropped_before_capture", 0):
        raise ValueError("Inconsistent capture drop counters")
    audio = [row for row in events if row["kind"] == "audio"]
    midi = [row for row in events if row["kind"] == "midi"]
    if not audio:
        raise ValueError("No rendered audio blocks")
    blocks = {row["block"]: row for row in audio}
    if len(blocks) != len(audio):
        raise ValueError("Duplicate audio-block identity")
    note_messages = []
    active_notes = set()
    note_pairs = 0
    for row in midi:
        block = blocks.get(row["block"])
        if block is None or not 0 <= row["offset"] < block["frames"]:
            raise ValueError("MIDI record has no matching block or invalid sample offset")
        if (row["frame"], row["epoch"]) != (block["frame"], block["epoch"]):
            raise ValueError("MIDI/audio timestamps disagree")
        if row.get("midi_truncated_blocks") != block.get("midi_truncated_blocks"):
            raise ValueError("MIDI/audio truncation counters disagree")
        message = bytes.fromhex(row["prefix"])
        if not message or len(message) != min(3, row["midi_size"]):
            raise ValueError("Invalid MIDI prefix/size")
        if (row["midi_size"] == 3 and len(message) == 3
                and message[0] & 0xf0 in (0x80, 0x90) and max(message[1:]) < 128):
            note_messages.append(row)
            key = (message[0] & 0x0f, message[1])
            if message[0] & 0xf0 == 0x90 and message[2] != 0:
                active_notes.add(key)
            elif key in active_notes:
                active_notes.remove(key)
                note_pairs += 1
    if (any(not row.get("held_known") for row in audio)
            or len({row.get("midi_truncated_blocks") for row in audio}) != 1):
        raise ValueError("MIDI scan was truncated; held-key diagnosis is incomplete")
    if any(row.get("non_finite_observations", 0) != 0 for row in audio):
        raise ValueError("Non-finite signal observed")
    for row in audio:
        for field in ("main_peak", "side_peak", "left_peak", "right_peak"):
            value = row.get(field)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("Missing or invalid signal summary")
    if require_audio and not any(row["left_peak"] > 0 for row in audio):
        raise ValueError("Required nonzero audio was not observed")
    if require_midi and not midi:
        raise ValueError("Required MIDI was not observed")
    if require_notes and not note_pairs:
        raise ValueError("Required matching MIDI note-on/off was not observed")
    if require_released and audio[-1]["held_keys"] != 0:
        raise ValueError("Held keys remain at capture end")
    offset_messages = note_messages if require_notes else midi
    if require_offsets and not any(row["offset"] > 0 for row in offset_messages):
        raise ValueError("Required within-block MIDI offset was not observed")
    exact = all(row["source_hash"] == row["left_hash"] == row["right_hash"] for row in audio)
    return {
        "schema": "voxide.routing-analysis.v1", "file_sha256": digest(path),
        "status": "valid_capture" if exact else "dry_route_mismatch",
        "instance": rows[0]["instance"], "version": rows[0]["version"], "build": rows[0]["build"],
        "audio_blocks": len(audio), "midi_records": len(midi), "exact_selected_dry_stereo": exact,
        "nonzero_audio_blocks": sum(row["left_peak"] > 0 for row in audio),
        "nonzero_midi_offsets": sum(row["offset"] > 0 for row in midi),
        "note_pairs": note_pairs,
        "incomplete_tail_records": rows[-1].get("incomplete_tail_records", 0),
        "last_held_keys": audio[-1]["held_keys"], "sources": sorted({row["source"] for row in audio}),
        "midi_prefixes": [row["prefix"] for row in midi],
        "scope": "Plug-in route only; not proof of audible lead count, Logic routing, monitoring latency, or external MIDI hardware",
    }


def check_native(profile, output=None):
    # Reuse the same source identity policy as full checks. No installs/UI/devices.
    from check import source_fingerprint
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = Path(output) if output else ROOT / "build/routing-checks" / (stamp + "-" + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False)
    preset = "local-" + profile
    build = ROOT / "build" / preset
    result = {"schema": "voxide.routing-check.v1", "status": "running", "profile": profile,
              "files": source_fingerprint(), "steps": [], "scope": "No Logic, audio devices, or installs"}
    report = directory / "report.json"
    commands = [
        ["cmake", "--preset", preset, "-DVOXIDE_OFFLINE=ON", "-DPython3_EXECUTABLE=" + sys.executable],
        ["cmake", "--build", str(build), "--parallel", "6", "--target", "voxide_processor_tests", "voxide_au_render_tests"],
        ["ctest", "--test-dir", str(build), "-R", "^(processor|au_render|tooling)$", "--output-on-failure", "--no-tests=error"],
    ]
    try:
        for index, command in enumerate(commands):
            log_path = directory / f"step-{index}.log"
            print("+", " ".join(command), flush=True)
            step = {"command": command, "log": log_path.name}
            result["steps"].append(step)
            report.write_text(json.dumps(result, indent=2) + "\n")
            with log_path.open("w") as stream:
                process = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
            step["exit_code"] = process.returncode
            if process.returncode:
                print(log_path.read_text())
                raise RuntimeError("Native routing check failed")
        native = json.loads((build / "au-routing-report.json").read_text())
        if native.get("status") != "pass" or native.get("routing_cases") != 96 or native.get("rendered_blocks") != 384:
            raise RuntimeError("Native AU report is incomplete")
        component = build / "voxide_artefacts" / profile.capitalize() / "AU/voxide.component"
        info = plistlib.loads((component / "Contents/Info.plist").read_bytes())
        if native["component_version"] != info["AudioComponents"][0]["version"]:
            raise RuntimeError("Native AU report version mismatch")
        result["native_au"] = native
        result["component_binary_sha256"] = digest(component / "Contents/MacOS/voxide")
        result["source_unchanged"] = source_fingerprint() == result["files"]
        if not result["source_unchanged"]:
            raise RuntimeError("Sources changed during routing check")
        result["status"] = "pass"
    except Exception as error:
        result["status"] = "fail"
        result["error"] = str(error)
        raise
    finally:
        report.write_text(json.dumps(result, indent=2) + "\n")
        print("Routing evidence:", report)
    return result


def environment(binary):
    result = json.loads(subprocess.check_output([str(Path(binary).resolve())], text=True))
    logic = Path("/Applications/Logic Pro.app/Contents/Info.plist")
    info = plistlib.loads(logic.read_bytes())
    result["logic_version"] = info.get("CFBundleShortVersionString")
    result["logic_build"] = info.get("CFBundleVersion")
    result["macos"] = subprocess.check_output(["sw_vers", "-productVersion"], text=True).strip()
    result["midi_live_test"] = "Musical Typing proposed; no external controller supplied"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    create = sub.add_parser("prepare")
    create.add_argument("--directory", type=Path)
    inspect = sub.add_parser("analyze")
    inspect.add_argument("log", type=Path)
    inspect.add_argument("--require-audio", action="store_true")
    inspect.add_argument("--require-midi", action="store_true")
    inspect.add_argument("--require-offsets", action="store_true")
    inspect.add_argument("--require-notes", action="store_true", help="Require a matching note-on/off pair")
    inspect.add_argument("--require-released", action="store_true", help="Require zero final held keys")
    native = sub.add_parser("check")
    native.add_argument("--profile", choices=["debug", "release"], default="debug")
    native.add_argument("--output-directory", type=Path)
    probe = sub.add_parser("environment")
    probe.add_argument("--binary", type=Path, default=ROOT / "build/local-release/voxide_environment")
    probe.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        directory = args.directory or ROOT / "evaluation/pr-01" / (stamp + "-" + uuid.uuid4().hex[:8])
        prepare(directory)
        print(directory)
    elif args.action == "analyze":
        result = analyze(args.log, args.require_audio, args.require_midi, args.require_offsets,
                         args.require_notes, args.require_released)
        print(json.dumps(result, indent=2))
        if not result["exact_selected_dry_stereo"]:
            raise SystemExit(1)
    elif args.action == "check":
        check_native(args.profile, args.output_directory)
    else:
        if args.output.exists():
            raise SystemExit("Refusing to overwrite existing environment evidence")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(environment(args.binary), indent=2) + "\n")
        print(args.output)


if __name__ == "__main__":
    main()
