"""Fail-closed checks for the two pinned studio research configurations. No I/O."""
import math
import bisect

from evaluation_common import require


def studio_clocks(rate, window, hop, engine):
    require(rate in (44100, 48000), "Unsupported studio rate")
    # Pinned EngineAdapter: Signalsmith symmetric window, split computation off;
    # Rubber Band uses zero nominal offset/control lag after its one startup trim.
    if engine == "signalsmith":
        require((window, hop) == (2048, 512), "Unsupported Signalsmith studio clock")
        lag, offset = window//2, window
    else:
        require(engine in ("rubberband", "rubberband-r3") and (window, hop) == (1, 128), "Unsupported Rubber Band studio clock")
        lag = offset = 0
    # PitchTracker: comparison=512 at rate/2, maxLag=ceil(rate/2/E2)+1,
    # analysis reserve = support/2 + hop, with C++ positive round semantics.
    analysis = 512 + math.ceil((rate/2)/82.4068892282175) + 1 + 2*math.floor(rate*.0025+.5)
    return {"quantum": hop, "lag": lag, "offset": offset, "analysis": analysis}


def control_coverage(rows, *, rate, total, clocks, compact=False):
    quantum, lag, analysis = (clocks[k] for k in ("quantum", "lag", "analysis"))
    expected = max(0, (total-analysis)//quantum)
    require(expected > 0, "No complete studio control quanta")
    seen = [0, 0, 0]; previous = [None, None, None]
    shift_key = "shift" if compact else "applied_shift"
    for row in rows:
        voice, source, wall = (int(row[k]) for k in ("voice", "source", "wall"))
        require(0 <= voice < 3, "Invalid control voice")
        require(source == seen[voice]*quantum-lag and wall == analysis+(seen[voice]+1)*quantum-1,
                "Incomplete/out-of-order control quantum coverage")
        shift, hz, confidence = (float(row[k]) for k in (shift_key, "hz", "confidence"))
        require(all(math.isfinite(x) for x in (shift, hz, confidence)) and abs(shift) <= 12.000001
                and hz >= 0 and 0 <= confidence <= 1, "Invalid studio control values")
        voiced, active = (int(row[k]) for k in ("voiced", "active"))
        require(voiced in (0, 1) and active in (0, 1) and (voiced or not active), "Invalid studio uncertainty/activation")
        require(0 <= int(row["frame_available"]) <= wall+1, "Future pitch frame consumed")
        if previous[voice] is not None:
            require(abs(shift-previous[voice]) <= 2400*quantum/rate+1e-6, "Unbounded ratio transition")
        previous[voice] = shift; seen[voice] += 1
    require(seen == [expected]*3, "Incomplete control quantum/tail coverage")
    return {"per_voice_quanta": seen, "first_source": -lag, "last_source": (expected-1)*quantum-lag}


def listening_timeline(native, rows, candidate, *, callback_partitions=(128,)):
    """The approved listening command uses one epoch, H-at-zero and 128 callbacks."""
    rate, total, latency = (native[k] for k in ("sample_rate", "output_frames", "latency_samples"))
    clocks = studio_clocks(rate, candidate["window"], candidate["hop"], candidate["engine"])
    require(native["analysis_delay_samples"] == clocks["analysis"], "Studio analysis reserve changed")
    require(callback_partitions and all(type(n) is int and 1 <= n <= 4096 for n in callback_partitions), "Invalid callback schedule")
    callback_ends = []; position = index = 0
    while position < total:
        position = min(total, position+callback_partitions[index % len(callback_partitions)])
        callback_ends.append(position); index += 1
    integer_fields = ("kind", "epoch", "wall", "source", "voice", "requested", "available", "frame_begin", "frame_end",
                      "frame_available", "voiced", "active", "first_output", "count", "request_kind")
    float_fields = ("hz", "confidence", "target_midi", "requested_shift", "applied_shift", "weight")
    parsed = []
    for row in rows:
        require(set(integer_fields+float_fields) <= row.keys(), "Missing telemetry clock/evidence columns")
        item = {key: int(row[key]) for key in integer_fields}
        item.update({key: float(row[key]) for key in float_fields})
        require(all(math.isfinite(item[key]) for key in float_fields), "Nonfinite telemetry")
        require(item["kind"] in (0, 1, 2) and item["epoch"] == 0 and 0 <= item["wall"] <= total,
                "Invalid telemetry kind/epoch/clock")
        require(not parsed or item["wall"] >= parsed[-1]["wall"], "Out-of-order telemetry")
        require(0 <= item["frame_begin"] <= item["frame_end"] <= item["frame_available"] <= item["wall"]+1,
                "Invalid pitch support/availability")
        require(item["voiced"] in (0, 1) and item["active"] in (0, 1) and 0 <= item["confidence"] <= 1
                and 0 <= item["weight"] <= 1, "Invalid telemetry flags/weights")
        parsed.append(item)
    requests = [r for r in parsed if r["kind"] == 2]
    require(len(requests) == 1, "Missing/extra approved request evidence")
    request = requests[0]
    require(request["request_kind"] == 3 and all(request[k] == 0 for k in integer_fields if k not in ("kind", "request_kind"))
            and all(request[k] == 0 for k in float_fields), "Request differs from approved H-at-zero event")
    controls = [r for r in parsed if r["kind"] == 0]
    checks = control_coverage(controls, rate=rate, total=total, clocks=clocks)
    for row in controls:
        require(row["requested"] == row["available"] == 0 and row["request_kind"] == (3 if row["source"] >= 0 else 0)
                and row["count"] == row["first_output"] == 0, "Invalid request-to-control chronology")
    packets = [[r for r in parsed if r["kind"] == 1 and r["voice"] == v] for v in range(3)]
    require(sum(map(len, packets)) == sum(r["kind"] == 1 for r in parsed), "Invalid output voice")
    covered = []
    for voice, stream in enumerate(packets):
        require(stream, "Missing output evidence")
        next_output = -clocks["offset"]
        quanta = (total-clocks["analysis"])//clocks["quantum"]
        for index, row in enumerate(stream):
            require(0 <= row["count"] <= 1024 and row["first_output"] == next_output, "Invalid/missing output packet or retrieval bound")
            if candidate["engine"] == "signalsmith":
                # This wrapper always returns one quantum per process(), then
                # exactly outputLatency=1024 samples from finish(). No start pad.
                require(index <= quanta, "Extra Signalsmith output packet")
                wall = clocks["analysis"]+(index+1)*clocks["quantum"]-1 if index < quanta else total
                count = clocks["quantum"] if index < quanta else clocks["lag"]
                require((row["wall"], row["count"]) == (wall, count), "Invalid Signalsmith packet production clock/count")
            elif row["wall"] != total:
                # Rubber Band may retrieve several <=1024-sample chunks and
                # zero-count startup-trim records. Meaningful frames cannot
                # precede the input quanta that make them causally possible.
                if row["wall"] == 0:
                    require(row["count"] == 0, "Noncausal Rubber Band startup packet")
                else:
                    supplied = row["wall"]+1-clocks["analysis"]
                    require(supplied > 0 and supplied % clocks["quantum"] == 0
                            and next_output+row["count"] <= supplied, "Noncausal Rubber Band packet production")
            end_index = bisect.bisect_right(callback_ends, row["wall"])
            expected_available = callback_ends[end_index] if end_index < len(callback_ends) else total
            require(row["available"] == expected_available, "Invalid output callback availability")
            end = next_output+row["count"]
            earliest = max(0, next_output)
            if end > earliest and earliest < total-latency:
                require(row["wall"] <= earliest+latency, "Output missed fixed delivery deadline")
            next_output = end
        if candidate["engine"] == "signalsmith":
            require(len(stream) == quanta+1, "Incomplete Signalsmith output/finish packets")
        frames = native["voices"][voice]["native_frames"]
        require(type(frames) is int and frames >= 0 and next_output+clocks["offset"] == frames
                and next_output >= total-latency, "Incomplete native output/tail coverage")
        covered.append(frames)
    checks["output_frames_per_voice"] = covered
    return controls, checks


def fixed_sum_checks(direct, aligned, voices, sums):
    result = {}
    for name, lead in (("sum-direct", direct), ("sum-aligned", aligned)):
        maximum = squared = 0.
        for i, value in enumerate(sums[name]):
            expected = lead[i] + sum(voice[i] for voice in voices)/3
            error = float(value)-expected
            maximum = max(maximum, abs(error)); squared += error*error
        result[name] = {"max_abs": maximum, "rms": math.sqrt(squared/len(lead))}
    return result
