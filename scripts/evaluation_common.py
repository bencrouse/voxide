"""PR 02 local-only evidence primitives. Standard library; no devices or downloads."""
import hashlib
import json
import math
from pathlib import Path
import re
import wave

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/evidence/pr-02/contract.json"
FIXTURES = ROOT / "Source/Tests/Fixtures/pr02"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, minimum=0, maximum=None):
    return type(value) is int and value >= minimum and (maximum is None or value <= maximum)


def finite(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value) is not None


def digest_string(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result
    def floating_point(value):
        result = float(value)
        require(math.isfinite(result), "Non-finite JSON number: " + value)
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique, parse_float=floating_point,
                      parse_constant=lambda value: require(False, "Non-finite JSON: " + value))


def write_json(path, value):
    # Evidence is append-only by path, including broken symlinks. Never overwrite.
    with Path(path).open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def contained(root, name):
    require(isinstance(name, str) and name and not Path(name).is_absolute(), "Expected relative evidence path")
    require(".." not in Path(name).parts, "Parent traversal in evidence path")
    path = Path(root) / name
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Symlink evidence path refused")
    require(path.resolve().is_relative_to(Path(root).resolve()), "Evidence escapes its root")
    return path


def read_pcm(path):
    with wave.open(str(path), "rb") as stream:
        rate, channels, width, frames = (stream.getframerate(), stream.getnchannels(),
                                          stream.getsampwidth(), stream.getnframes())
        require(rate in (44100, 48000) and channels == 1 and width in (2, 3, 4),
                "Expected mono PCM16/24/32 WAV at 44.1 or 48 kHz")
        require(stream.getcomptype() == "NONE" and frames > 0, "Empty/compressed WAV refused")
        raw = stream.readframes(frames)
    require(len(raw) == frames * width, "Truncated WAV payload")
    return {"sample_rate": rate, "channels": channels, "bits": width * 8, "frames": frames}, raw


def wav_info(path):
    return read_pcm(path)[0]


def pcm_sha256(info, raw):
    """Bind the PCM words and timebase, ignoring irrelevant RIFF/container chunks."""
    description = {key: info[key] for key in ("sample_rate", "channels", "bits", "frames")}
    prefix = json.dumps(description, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(b"voxide.pcm.v1\0" + prefix + b"\0" + raw).hexdigest()


def wav_identity(path):
    info, raw = read_pcm(path)
    return info, pcm_sha256(info, raw)


def read_wav(path):
    info, raw = read_pcm(path)
    width = info["bits"] // 8
    scale = float(1 << (8 * width - 1))
    samples = [int.from_bytes(raw[i:i + width], "little", signed=True) / scale
               for i in range(0, len(raw), width)]
    return info, samples


def write_wav(path, rate, samples):
    require(rate in (44100, 48000) and samples, "Invalid WAV rate/empty samples")
    raw = encode_pcm24(samples)
    write_pcm(path, {"sample_rate": rate, "channels": 1, "bits": 24, "frames": len(samples)}, raw)


def encode_pcm24(samples):
    require(samples and all(finite(x) and -1 <= x < 1 for x in samples), "Non-finite/clipped WAV samples")
    return b"".join(int(round(x * 8388607)).to_bytes(3, "little", signed=True) for x in samples)


def write_pcm(path, info, raw):
    require(info["sample_rate"] in (44100, 48000) and info["channels"] == 1
            and info["bits"] in (16, 24, 32) and info["frames"] > 0
            and len(raw) == info["frames"] * (info["bits"] // 8), "Invalid PCM payload")
    # Own the new destination exclusively before wave writes its header.
    with Path(path).open("xb") as destination:
        with wave.open(destination, "wb") as stream:
            stream.setparams((1, info["bits"] // 8, info["sample_rate"], info["frames"], "NONE", "not compressed"))
            stream.writeframes(raw)


def midi_hz(note):
    return 440.0 * 2 ** ((note - 69) / 12)


def validate_controls(data, info=None, expected_pcm_sha256=None):
    require(data.get("schema") == "voxide.controls.v2", "Unsupported controls schema")
    require(identifier(data.get("source_id")) and digest_string(data.get("source_pcm_sha256"))
            and integer(data.get("sample_rate"), 1) and data["sample_rate"] in (44100, 48000)
            and integer(data.get("frames"), 1), "Missing control source identity/timebase")
    frames = data["frames"]
    if info is not None:
        require(data["sample_rate"] == info["sample_rate"] and frames == info["frames"], "Control source timebase mismatch")
    if expected_pcm_sha256 is not None:
        require(data["source_pcm_sha256"] == expected_pcm_sha256, "Control source PCM mismatch")
    events = data.get("events")
    require(isinstance(events, list), "Missing control events")
    seen, previous = set(), -1
    for event in events:
        require(identifier(event.get("id")) and event["id"] not in seen, "Duplicate/invalid event ID")
        seen.add(event["id"])
        require(integer(event.get("sample"), 0, frames - 1) and event["sample"] >= previous,
                "Unsorted/out-of-range control timestamp")
        previous = event["sample"]
        require(event.get("kind") in ("note_on", "note_off"), "Unsupported event kind")
        require(integer(event.get("note"), 0, 127) and integer(event.get("channel"), 1, 16)
                and integer(event.get("velocity"), 0, 127), "Invalid MIDI value")
    return events


def partition_controls(events, frames, blocks):
    require(blocks and all(integer(n, 1) for n in blocks), "Invalid block partition")
    result, cursor, event_index, block_index = [], 0, 0, 0
    while cursor < frames:
        count = min(blocks[block_index % len(blocks)], frames - cursor)
        while event_index < len(events) and events[event_index]["sample"] < cursor + count:
            event = events[event_index]
            require(event["sample"] >= cursor, "Unsorted control stream")
            result.append(dict(event, block_start=cursor, offset=event["sample"] - cursor))
            event_index += 1
        cursor += count
        block_index += 1
    require(event_index == len(events), "Control event outside render")
    return result
