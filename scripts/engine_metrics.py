"""Independent analytic engine measurements. Not a tracker or a vocal/listening oracle."""
import array
import bisect
import csv
import hashlib
import math
from pathlib import Path
import struct

from evaluation_common import require
from evaluation_metrics import cents, estimate_resonances, percentile, measure_unity_delay, fft, power_of_two


def estimate_output_pitch(samples, rate, minimum=16, maximum=5000):
    """Offline normalized autocorrelation; interpolate BEFORE ranking short periods.

    Integer-lag peak heights understate high-F0 fundamentals and can prefer a
    doubled period. Local band-limited interpolation avoids that without searching
    around, or otherwise receiving, the expected answer. Frozen PR02 tools unchanged.
    """
    require(len(samples) >= 32 and 0 < minimum < maximum < rate/2, "Invalid output pitch instrument input")
    mean = sum(samples)/len(samples)
    signal = [float(x)-mean for x in samples]
    energies = [0.0]
    for value in signal:
        require(math.isfinite(value),"Nonfinite pitch instrument input")
        energies.append(energies[-1]+value*value)
    if energies[-1]/len(signal) < 1e-12:
        return {"f0_hz":None,"confidence":0.0}
    size = power_of_two(2*len(signal))
    spectrum = fft(signal+[0.0]*(size-len(signal)))
    correlation = fft([x*x.conjugate() for x in spectrum],inverse=True)
    low = max(2,int(rate/maximum)); high = min(len(signal)//2,math.ceil(rate/minimum))
    require(high > low+1,"Output pitch instrument support too short")
    scores = [1.0]
    for lag in range(1,min(len(signal)-1,high+9)+1):
        denominator = math.sqrt(energies[-lag-1]*(energies[-1]-energies[lag]))
        scores.append(correlation[lag].real/denominator if denominator > 0 else 0)
    def sinc(x): return math.sin(math.pi*x)/(math.pi*x) if abs(x)>1e-12 else 1.0
    def interpolated(position):
        total = weight = 0.0
        for at in range(max(0,math.floor(position)-7),min(len(scores),math.floor(position)+9)):
            delta = position-at
            if abs(delta)>=8: continue
            w = sinc(delta)*sinc(delta/8)
            total += scores[at]*w; weight += w
        return total/weight if weight else 0.0
    candidates = []
    for lag in range(low,high+1):
        if scores[lag] <= scores[lag-1] or scores[lag] < scores[lag+1]: continue
        a,b,c = scores[lag-1:lag+2]
        denominator = a-2*b+c
        delta = max(-.5,min(.5,.5*(a-c)/denominator)) if denominator else 0
        position = lag+delta; strength = b-.25*(a-c)*delta
        if lag < 64:
            offsets = [lag+i/16 for i in range(-12,13)]
            values = [interpolated(x) for x in offsets]
            best = max(range(len(values)),key=values.__getitem__)
            position = offsets[best]; strength = values[best]
            if 0 < best < len(values)-1:
                left,middle,right = values[best-1:best+2]
                denominator = left-2*middle+right
                if denominator < 0:
                    correction = max(-.5,min(.5,.5*(left-right)/denominator))
                    position += correction/16
                    strength = middle-.25*(left-right)*correction
        candidates.append((position,max(0,min(1,strength))))
    best = max((strength for _,strength in candidates),default=0)
    if best < .7: return {"f0_hz":None,"confidence":best}
    position,strength = next((position,strength) for position,strength in candidates if strength >= max(.7,best*.95))
    return {"f0_hz":rate/position,"confidence":strength}


def read_float(path):
    data = Path(path).read_bytes()
    require(len(data) % 4 == 0, "Truncated float32 stem")
    values = array.array("f")
    values.frombytes(data)
    require(values.itemsize == 4 and all(math.isfinite(x) for x in values), "Invalid float32 stem")
    return values, data


def write_float_wav(path, rate, data):
    require(len(data) % 4 == 0 and len(data) < 2**32 - 48, "Invalid float WAV length")
    # IEEE float, mono, unchanged payload. No clipping, gain fitting or normalization.
    header = b"RIFF" + struct.pack("<I", len(data) + 48) + b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 3, 1, rate, rate * 4, 4, 32)
    header += b"fact" + struct.pack("<II",4,len(data)//4) + b"data" + struct.pack("<I", len(data))
    with Path(path).open("xb") as stream: stream.write(header + data)
    return hashlib.sha256(data).hexdigest()


def read_csv(path):
    with Path(path).open() as stream: return list(csv.DictReader(stream))


def validate_timeline(native, chunks, controls, expected):
    voices = native["voices"]
    total = native["source_frames"] + native["zero_tail_supplied"]
    result = []
    for voice in range(voices):
        timeline = [{key: int(value) for key, value in row.items()} for row in chunks if int(row["voice"]) == voice]
        end = 0; previous = -1
        for row in timeline:
            require(row["output_begin"] == end and row["count"] > 0, "Output FIFO lost/repeated samples")
            require(previous <= row["available_source_samples"] <= row["callback_available_source_samples"] <= total,
                    "Invalid engine availability clock")
            end += row["count"]; previous = row["available_source_samples"]
        require(end == native["instances"][voice]["output_frames"], "Availability does not cover output tail")
        applied = [row for row in controls if int(row["voice"]) == voice]
        require(len(applied) == len(expected), "Missing/repeated prescribed controls")
        for row, event in zip(applied, expected):
            require(int(row["requested_source_sample"]) == event["sample"] and float(row["ratio"]) == event["ratios"][voice]
                    and float(row["source_hz"]) == event["source_hz"], "Control identity/timebase mismatch")
            source = int(row["processing_source_sample"])
            if event["sample"] != 0:
                require(event["sample"] <= source < event["sample"] + native["instances"][voice]["quantum"], "Control applied early or missed its fixed quantum")
            require(int(row["applied_input_begin"]) - native["instances"][voice]["control_lag"] == source,
                    "Engine control clock mismatch")
        result.append(timeline)
    require(all(0 <= int(row["voice"]) < voices for row in chunks + controls), "Unexpected timeline voice")
    return result


def available_at(timeline, output_sample, callback=True):
    starts = [row["output_begin"] for row in timeline]
    index = bisect.bisect_right(starts, output_sample) - 1
    if index < 0: return None
    row = timeline[index]
    if output_sample >= row["output_begin"] + row["count"]: return None
    return row["callback_available_source_samples" if callback else "available_source_samples"]


def callback_metrics(rows, rate, audit_available, quality, expected_frames=None):
    require(rows, "No measured callbacks")
    previous = 0
    occupancy = []; ns = []; allocations = 0
    for row in rows:
        begin, frames, cost, count = (int(row[key]) for key in ("begin", "frames", "ns", "allocations"))
        require(begin == previous and frames > 0 and cost >= 0 and count >= 0, "Invalid callback coverage")
        previous += frames
        occupancy.append(cost * rate / (1e9 * frames)); ns.append(cost)
        allocations += count
    require(expected_frames is None or previous == expected_frames, "Truncated callback tail coverage")
    p999 = percentile(occupancy, .999)
    return {"callbacks": len(rows), "ns_max": max(ns), "occupancy_max": max(occupancy), "occupancy_p999": p999,
            "overdue_callbacks": sum(x > 1 for x in occupancy),
            "occupancy_target_met_on_this_run_only": p999 < quality["callback_occupancy_p999_max_exclusive"] and max(occupancy) <= 1,
            "allocation_calls": allocations if audit_available else None,
            "callbacks_with_allocations": sum(int(row["allocations"]) > 0 for row in rows) if audit_available else None,
            "scope": "Instrumented virtual callbacks include adapter, all voices, audit/hash/timeline overhead; Release only, not Logic or hard realtime proof"}


def availability_metrics(timeline, offset, source_frames, rate):
    delays = []
    missing = 0
    for sample in range(round(rate*.05),source_frames-round(rate*.05),round(rate*.01)):
        arrival = available_at(timeline,offset+sample)
        if arrival is None: missing += 1
        else: delays.append((arrival-sample)*1000/rate)
    return {"sampled_source_frames":len(delays)+missing,"missing":missing,
            "median_ms":percentile(delays,.5) if delays else None,"p95_ms":percentile(delays,.95) if delays else None,
            "maximum_ms":max(delays) if delays else None,
            "scope":"Native packet availability on a 10 ms nominal source grid, including callback return; assumes queried output offset, not physical monitoring or non-unity waveform correlation"}


def pitch_measurements(output, offset, source_frames, expected_hz, rate):
    # Independent full-range estimator: never constrain its search around the answer.
    window = 8192
    centers = sorted(set(round(source_frames * fraction) for fraction in (.35, .5, .65)))
    observations = []
    for center in centers:
        begin = offset + center - window // 2
        end = begin + window
        valid = center - window // 2 >= round(rate * .05) and center + window // 2 <= source_frames - round(rate * .05)
        if not valid:
            observations.append({"source_sample": center, "eligible": False, "f0_hz": None, "error_cents": None})
            continue
        if begin < 0 or end > len(output):
            observations.append({"source_sample": center, "eligible": True, "f0_hz": None,
                                 "error_cents": None, "reason": "missing_output_support"})
            continue
        pitch = estimate_output_pitch(output[begin:end], rate, minimum=16, maximum=5000)
        hz = pitch["f0_hz"]
        observations.append({"source_sample": center, "eligible": True, "f0_hz": hz,
                             "confidence": pitch["confidence"], "error_cents": cents(hz, expected_hz) if hz else None})
    eligible = [row for row in observations if row["eligible"]]
    good = sum(row["error_cents"] is not None and abs(row["error_cents"]) <= 25 for row in eligible)
    return {"observations": observations, "eligible_frames": len(eligible), "within_25c_frames": good,
            "missing_estimates": sum(row["f0_hz"] is None for row in eligible),
            "within_25c_fraction": good / len(eligible) if eligible else None,
            "scope": "Analytic steady controls only; missing estimates fail; no claim of vocal or transition accuracy"}


def impulse_delay(source, output, timeline, expected_offset, rate):
    observed = measure_unity_delay(source, output, maximum=rate)
    delay = observed["delay_samples"]
    input_peak = max(range(len(source)), key=lambda i: abs(source[i]))
    output_peak = input_peak + delay
    arrival = available_at(timeline, output_peak)
    return {"output_offset_samples": delay, "queried_nominal_offset_samples": expected_offset,
            "query_error_samples": delay - expected_offset,
            "peak_available_source_sample": arrival,
            "causal_peak_delay_ms": (arrival - input_peak) * 1000 / rate if arrival is not None else None,
            "scope": "Unity impulse/waveform correlation only; callback availability retained after any startup trimming"}


def envelope_delay(output, timeline, source_frames, offset, rate):
    # A known amplitude step at N/2, not shifted-waveform correlation.
    window = max(1, round(rate * .005))
    rms = [(start, math.sqrt(sum(float(x) ** 2 for x in output[start:start + window]) / window))
           for start in range(offset, min(len(output) - window + 1, offset + source_frames), window)]
    source_step = source_frames // 2
    before = [value for start, value in rms if source_step - rate * .2 <= start - offset < source_step - rate * .08]
    after = [value for start, value in rms if source_step + rate * .15 <= start - offset < source_frames - rate * .05]
    if not before or not after: return {"status": "unobservable", "reason": "insufficient step plateaus"}
    low = percentile(before, .5); high = percentile(after, .5)
    if high < low * 2 or high < 1e-7: return {"status": "unobservable", "reason": "step contrast lost", "before_rms": low, "after_rms": high}
    threshold = low + .5 * (high - low)
    crossing = next((start + window for start, value in rms if start + window >= offset + source_step - rate * .05 and value >= threshold), None)
    arrival = available_at(timeline, crossing - 1) if crossing is not None else None
    return {"status": "measured" if arrival is not None else "missing", "source_step": source_step,
            "output_threshold_window_end": crossing, "window_samples": window,
            "relative_to_nominal_ms": (crossing - offset - source_step) * 1000 / rate if crossing is not None else None,
            "causal_threshold_delay_ms": (arrival - source_step) * 1000 / rate if arrival is not None else None,
            "scope": "5 ms RMS amplitude-step observer; threshold latency includes observer and callback availability; no waveform correlation or timing backdating"}


def ratio_settling(output, timeline, events, voice, offset, rate):
    window, hop = 4096, round(rate * .01)
    measurements = []
    for index, event in enumerate(events[1:], 1):
        stop = events[index + 1]["sample"] if index + 1 < len(events) else events[-1]["sample"] + round(rate * .2)
        target = event["source_hz"] * event["ratios"][voice]
        began = None; settled = None
        for center in range(event["sample"], stop, hop):
            begin = offset + center - window // 2; end = begin + window
            if begin < 0 or end > len(output): continue
            estimate = estimate_output_pitch(output[begin:end], rate, minimum=16, maximum=5000)
            good = estimate["f0_hz"] is not None and abs(cents(estimate["f0_hz"], target)) <= 25
            if not good: began = None
            elif began is None: began = center
            elif center - began >= round(rate * .02):
                arrival = available_at(timeline, end - 1)
                settled = {"output_center": center + offset, "observer_end": end,
                           "available_source_sample": arrival,
                           "request_to_observed_dwell_ms": (arrival - event["sample"]) * 1000 / rate if arrival is not None else None}
                break
        measurements.append({"requested_source_sample": event["sample"], "target_hz": target, "settled": settled})
    return {"events": measurements, "analysis_window_samples": window, "dwell_ms": 20,
            "scope": "Descriptive output-F0 observer; its centered-window lookahead and completed dwell are included in arrival, not engine-only response or tracking latency"}


def formant_measurements(output, offset, frames, rate, expected):
    begin = offset + round(rate * .1); end = offset + min(frames - round(rate * .1), round(rate * .9))
    if end - begin < 4096: return {"status": "pending", "reason": "insufficient stable synthetic resonator support"}
    instrument = estimate_resonances(output[begin:end], rate)
    measured = instrument["resonances_hz"]
    errors = [abs(actual - reference) / reference for actual, reference in zip(measured, expected)]
    return {"status": "measured", "expected_hz": expected, "measured_hz": measured,
            "fraction_errors": errors, "median_fraction_error": percentile(errors, .5), "p95_fraction_error": percentile(errors, .95),
            "scope": "Independent fixed-band synthetic broadband resonator peaks only, not actual vocal formant truth"}


def reference_pitch_measurements(output, reference, ratio, offset, source_frames, rate, window=8192, provenance="Supplied source reference"):
    """Keep known stable and moving/expressive reference errors separate."""
    observations = []
    excluded = {"uncertain": 0, "unvoiced": 0, "boundary_support": 0}
    for frame in reference:
        if frame["uncertain"]: excluded["uncertain"] += 1; continue
        if not frame["voiced"]: excluded["unvoiced"] += 1; continue
        center = frame["sample"]
        if center - window // 2 < rate * .05 or center + window // 2 > source_frames - rate * .05:
            excluded["boundary_support"] += 1; continue
        begin = center + offset - window // 2; end = begin + window
        pitch = estimate_output_pitch(output[begin:end], rate, minimum=16, maximum=5000) if begin >= 0 and end <= len(output) else {"f0_hz": None, "confidence": 0}
        expected = frame["f0_hz"] * ratio
        observations.append({"source_sample": center, "stable": frame["stable"], "reference_hz": frame["f0_hz"],
                             "expected_hz": expected, "observed_hz": pitch["f0_hz"], "confidence": pitch["confidence"],
                             "error_cents": cents(pitch["f0_hz"], expected) if pitch["f0_hz"] else None})
    groups = {}
    for name, stable in (("stable", True), ("expressive_unstable", False)):
        rows = [row for row in observations if row["stable"] == stable]
        good = sum(row["error_cents"] is not None and abs(row["error_cents"]) <= 25 for row in rows)
        groups[name] = {"frames": len(rows), "within_25c_frames": good, "within_25c_fraction": good / len(rows) if rows else None,
                        "missing_estimates": sum(row["observed_hz"] is None for row in rows)}
    return {"groups": groups, "excluded": excluded, "observations": observations,
            "analysis_window_samples":window,
            "scope": provenance + ". Unstable bends/articulation retained separately, not counted correct or tuned away. Output observer temporal averaging limits remain."}


def human_reference_pitch(output, reference, ratio, offset, source_frames, rate):
    return reference_pitch_measurements(output,reference,ratio,offset,source_frames,rate,
        provenance="Two reviewed agreeing source annotations, not automated truth")
