"""Independent offline calibration tools, not a production tracker or vocal oracle."""
import cmath
import math

from evaluation_common import finite, identifier, integer, require
from evaluation_contract import load_contract


def percentile(values, fraction):
    require(values and 0 <= fraction <= 1, "Percentile requires data and a probability")
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def wilson(successes, count):
    if count == 0:
        return None
    z = 1.959963984540054
    p = successes / count
    denominator = 1 + z * z / count
    center = (p + z * z / (2 * count)) / denominator
    radius = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / denominator
    return [center - radius, center + radius]


def fft(values, inverse=False):
    n = len(values)
    require(n > 0 and n & (n - 1) == 0, "FFT size must be a power of two")
    result = list(map(complex, values))
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            result[i], result[j] = result[j], result[i]
    size = 2
    while size <= n:
        root = cmath.exp((2j if inverse else -2j) * math.pi / size)
        for start in range(0, n, size):
            factor = 1 + 0j
            for offset in range(size // 2):
                a = result[start + offset]
                b = factor * result[start + offset + size // 2]
                result[start + offset] = a + b
                result[start + offset + size // 2] = a - b
                factor *= root
        size *= 2
    return [x / n for x in result] if inverse else result


def power_of_two(n):
    return 1 << (n - 1).bit_length()


def cents(actual, expected):
    require(finite(actual) and finite(expected) and actual > 0 and expected > 0, "Invalid pitch")
    # Subtract logarithms so valid tiny positive values cannot underflow the ratio
    # to zero (or overflow it) before the error can be reported.
    return 1200 * (math.log2(actual) - math.log2(expected))


def estimate_pitch(samples, rate, minimum=20, maximum=4200):
    """Normalized autocorrelation, earliest near-best local peak, parabolic lag fit.

    Offline only: the whole supplied window is available. Silence/noise return
    uncertain estimates, never a fabricated zero-Hz voiced reference.
    """
    require(len(samples) >= 16 and 0 < minimum < maximum < rate / 2, "Invalid pitch window/range")
    mean = sum(samples) / len(samples)
    signal = [x - mean for x in samples]
    energies = [0.0]
    for value in signal:
        require(finite(value), "Non-finite signal")
        energies.append(energies[-1] + value * value)
    if energies[-1] / len(signal) < 1e-12:
        return {"f0_hz": None, "confidence": 0.0, "uncertain": True}
    size = power_of_two(2 * len(signal))
    spectrum = fft(signal + [0.0] * (size - len(signal)))
    correlation = fft([x * x.conjugate() for x in spectrum], inverse=True)
    low, high = max(2, int(rate / maximum)), min(len(signal) // 2, math.ceil(rate / minimum))
    require(high > low + 2, "Pitch window too short")
    scores = {}
    for lag in range(low - 1, high + 2):
        denominator = math.sqrt(energies[-lag - 1] * (energies[-1] - energies[lag]))
        scores[lag] = correlation[lag].real / denominator if denominator > 0 else 0.0
    peaks = [lag for lag in range(low, high + 1)
             if scores[lag] > scores[lag - 1] and scores[lag] >= scores[lag + 1]]
    best = max((scores[lag] for lag in peaks), default=0.0)
    if best < 0.7:
        return {"f0_hz": None, "confidence": max(0.0, best), "uncertain": True}
    lag = next(lag for lag in peaks if scores[lag] >= max(0.7, best * 0.95))
    a, b, c = scores[lag - 1], scores[lag], scores[lag + 1]
    adjustment = 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c else 0.0
    return {"f0_hz": rate / (lag + adjustment), "confidence": min(1.0, b), "uncertain": False}


def estimate_resonances(samples, rate):
    """Welch/Hann spectrum in fixed, truth-independent bands; synthetic use only."""
    size = 4096
    require(len(samples) >= size, "Resonance measurement needs at least 4096 samples")
    power = [0.0] * (size // 2 + 1)
    windows = 0
    for start in range(0, len(samples) - size + 1, size // 2):
        window = [samples[start + i] * (0.5 - 0.5 * math.cos(2 * math.pi * i / (size - 1)))
                  for i in range(size)]
        spectrum = fft(window)
        for i in range(len(power)):
            power[i] += abs(spectrum[i]) ** 2
        windows += 1
    require(max(power) > 1e-18, "No resonance energy")
    smoothed = [sum(power[max(0, i - 2):i + 3]) / len(power[max(0, i - 2):i + 3])
                for i in range(len(power))]
    result = []
    for lower, upper in ((300, 900), (900, 1700), (1800, 3300)):
        bins = range(math.ceil(lower * size / rate), math.floor(upper * size / rate) + 1)
        peak = max(bins, key=lambda i: smoothed[i])
        a, b, c = [math.log(max(smoothed[i], 1e-30)) for i in (peak - 1, peak, peak + 1)]
        offset = 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c else 0
        result.append((peak + max(-0.5, min(0.5, offset))) * rate / size)
    return {"resonances_hz": result, "windows": windows, "bin_hz": rate / size,
            "scope": "Synthetic broadband resonances only, not real-vocal formant ground truth"}


def compare_delayed(source, output, delay, policy=None):
    policy = load_contract() if policy is None else policy
    max_abs, rms = (policy["deterministic_tolerance"][key] for key in ("max_abs", "rms"))
    require(type(delay) is int and delay >= 0, "Delay must be a nonnegative sample count")
    require(source and len(output) == len(source) + delay, "Lead length/tail mismatch")
    require(all(finite(x) for x in (*source, *output)), "Non-finite null-test samples")
    expected = [0.0] * delay + list(source)
    errors = [actual - reference for actual, reference in zip(output, expected)]
    peak = max(abs(x) for x in errors)
    error_rms = math.sqrt(sum(x * x for x in errors) / len(errors))
    return {"status": "pass" if peak <= max_abs and error_rms <= rms else "fail",
            "contract_sha256": policy["_sha256"], "limits": policy["deterministic_tolerance"],
            "delay_samples": delay, "samples": len(errors), "max_abs": peak, "rms": error_rms}


def measure_unity_delay(source, output, maximum):
    require(source and output and type(maximum) is int and maximum >= 0, "Invalid delay input")
    require(all(finite(x) for x in (*source, *output)), "Non-finite delay signal")
    size = power_of_two(len(source) + len(output) - 1)
    a = fft(list(reversed(source)) + [0.0] * (size - len(source)))
    b = fft(list(output) + [0.0] * (size - len(output)))
    convolution = fft([x * y for x, y in zip(a, b)], inverse=True)
    scores = [convolution[len(source) - 1 + lag].real
              for lag in range(min(maximum, len(output) - 1) + 1)]
    best = max(scores)
    require(best > 1e-12, "No positive correlation for delay measurement")
    require(sum(score >= best * 0.999999 for score in scores) == 1, "Ambiguous unity delay")
    delay = scores.index(best)
    return {"delay_samples": delay, "scope": "Unity/known probe only, not shifted-audio latency"}


def score_pitch(reference, observed, tolerance=None):
    tolerance = load_contract()["quality"]["pitch_tolerance_cents"] if tolerance is None else tolerance
    require(len(reference) == len(observed) and reference, "Mismatched/empty pitch grid")
    good, octave, denominator, excluded, unvoiced, false_voiced, missed = 0, 0, 0, 0, 0, 0, 0
    errors = []
    for expected, actual in zip(reference, observed):
        require(expected["sample"] == actual["sample"], "Pitch timestamps differ")
        if expected["uncertain"] or not expected["stable"]:
            excluded += 1
            continue
        if not expected["voiced"]:
            unvoiced += 1
            false_voiced += actual["f0_hz"] is not None
            continue
        denominator += 1
        if actual["f0_hz"] is None:
            missed += 1
            continue
        error = abs(cents(actual["f0_hz"], expected["f0_hz"]))
        errors.append(error)
        good += error <= tolerance
        nearest_octave = round(error / 1200)
        octave += nearest_octave >= 1 and abs(error - nearest_octave * 1200) <= tolerance
    return {"status": "measured" if denominator else "pending", "stable_voiced_frames": denominator,
            "within_tolerance": good, "accuracy": good / denominator if denominator else None,
            "accuracy_wilson95": wilson(good, denominator), "octave_errors": octave,
            "octave_error_fraction": octave / denominator if denominator else None,
            "missing_voiced_estimates": missed, "excluded_reference_frames": excluded,
            "unvoiced_frames": unvoiced, "false_voiced_frames": false_voiced,
            "absolute_cents_p95": percentile(errors, 0.95) if errors else None}


def settling_sample(frames, target_hz, start, dwell, hop, tolerance=None):
    """Return confirmation time, not the earlier start of a retrospectively good run."""
    tolerance = load_contract()["quality"]["pitch_tolerance_cents"] if tolerance is None else tolerance
    began, previous = None, None
    for frame in frames:
        sample = frame["sample"]
        if sample < start:
            continue
        if previous is not None:
            require(sample > previous, "Unordered response timestamps")
        correct = frame["f0_hz"] is not None and abs(cents(frame["f0_hz"], target_hz)) <= tolerance
        if not correct or (previous is not None and sample - previous > hop):
            began = None
        if correct:
            began = sample if began is None else began
            if sample - began >= dwell:
                return sample
        previous = sample
    return None


def score_control_response(expected, applied, rate, interval_samples, policy=None):
    policy = load_contract() if policy is None else policy
    target_ms = policy["timing_ms"]["midi_target"]
    require(expected and len(expected) == len(applied) and integer(interval_samples, 1)
            and integer(rate, 1) and rate in (44100, 48000), "Missing/invalid control observations")
    require(len({event["id"] for event in expected}) == len(expected), "Duplicate expected control ID")
    latencies, previous = [], -1
    for event, actual in zip(expected, applied):
        require(event["id"] == actual.get("id"), "Missing/reordered/unexpected control application")
        require(type(actual.get("sample")) is int and actual["sample"] >= event["sample"],
                "Control applied before its timestamp/invalid application time")
        require(actual["sample"] >= previous, "Control application timestamps reordered")
        previous = actual["sample"]
        latencies.append(actual["sample"] - event["sample"])
    return {"schema": "voxide.control-response.v1", "events": len(latencies),
            "sample_rate": rate,
            "contract_sha256": policy["_sha256"], "target_ms": target_ms,
            "status": "pass" if max(latencies) <= interval_samples and max(latencies) * 1000 / rate <= target_ms else "fail",
            "latency_samples": latencies, "maximum_ms": max(latencies) * 1000 / rate,
            "p95_ms": percentile(latencies, 0.95) * 1000 / rate,
            "scope": "Input event to applied state; not MIDI device or audible harmony latency"}


def score_response(events, decisions, rate, policy=None):
    policy = load_contract() if policy is None else policy
    dwell_ms, hop_ms = (policy["measurement"][key] for key in ("settling_dwell_ms", "frame_hop_ms"))
    tolerance = policy["quality"]["pitch_tolerance_cents"]
    timing = policy["timing_ms"]
    require(events and decisions and integer(rate, 1) and rate in (44100, 48000) and dwell_ms > 0 and hop_ms > 0,
            "Response measurement needs valid events/decisions/timebase")
    previous = -1
    for frame in decisions:
        require(type(frame.get("sample")) is int and frame["sample"] > previous, "Invalid decision arrival time")
        previous = frame["sample"]
        hz = frame.get("f0_hz")
        require(hz is None or (finite(hz) and 0 < hz < rate / 2), "Invalid decision F0")
    ids, results = set(), []
    for index, event in enumerate(events):
        require(event.get("kind") in ("cold_onset", "transition") and type(event.get("sample")) is int
                and identifier(event.get("id")) and event["sample"] >= 0
                and finite(event.get("target_hz")) and 0 < event["target_hz"] < rate / 2,
                "Invalid response reference event")
        require(event.get("id") not in ids, "Duplicate response event")
        ids.add(event["id"])
        if index:
            require(event["sample"] > events[index - 1]["sample"], "Unsorted response events")
        stop = events[index + 1]["sample"] if index + 1 < len(events) else math.inf
        window = [frame for frame in decisions if event["sample"] <= frame["sample"] < stop]
        sample = settling_sample(window, event["target_hz"], event["sample"],
                                 round(dwell_ms * rate / 1000), round(hop_ms * rate / 1000), tolerance)
        results.append({"id": event["id"], "kind": event["kind"],
                        "register": "low" if event["target_hz"] < timing["recognition_boundary_hz"] else "high",
                        "confirmed_sample": sample,
                        "latency_ms": (sample - event["sample"]) * 1000 / rate if sample is not None else None})
    groups = []
    for kind in ("cold_onset", "transition"):
        for register, limit in (("low", timing["recognition_low_p95"]), ("high", timing["recognition_high_p95"])):
            selected = [r for r in results if r["kind"] == kind and r["register"] == register]
            observed = [r["latency_ms"] for r in selected if r["latency_ms"] is not None]
            p95 = percentile(observed, 0.95) if observed else None
            status = ("pending" if not selected else "pass" if len(observed) == len(selected)
                      and p95 <= limit else "fail")
            groups.append({"kind": kind, "register": register, "events": len(selected),
                           "missing_decisions": len(selected) - len(observed), "p95_ms": p95,
                           "limit_ms": limit, "status": status})
    overall = ("fail" if any(g["status"] == "fail" for g in groups) else "pending"
               if any(g["status"] == "pending" for g in groups) else "pass")
    return {"schema": "voxide.recognition-response.v1", "status": overall, "events": results, "groups": groups,
            "sample_rate": rate,
            "contract_sha256": policy["_sha256"], "dwell_ms": dwell_ms, "hop_ms": hop_ms,
            "pitch_tolerance_cents": tolerance, "register_boundary_hz": timing["recognition_boundary_hz"],
            "scope": "Decision arrival in the source clock; cold/continuous and register groups separate; not audio/monitoring delay"}
