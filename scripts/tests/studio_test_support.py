"""Synthetic serialized telemetry, independent of the production validators."""
import csv


def synthetic_timeline(rate, total, engine="signalsmith", *, oracle=False):
    # Literal clocks from the pinned adapter/tracker, not calls to studio_clocks.
    analysis = 0 if oracle else {44100: 1001, 48000: 1045}[rate]
    quantum, lag, offset, finish = (512, 1024, 2048, 1024) if engine == "signalsmith" else (128, 0, 0, 0)
    fields = "kind epoch wall source voice requested available frame_begin frame_end frame_available hz confidence voiced active target_midi requested_shift applied_shift weight first_output count request_kind".split()
    def row(**values):
        result = dict.fromkeys(fields, "0"); result.update({key: str(value) for key, value in values.items()}); return result
    rows = [row(kind=2, request_kind=3)]
    quanta = (total-analysis)//quantum
    for index in range(quanta):
        wall = analysis+(index+1)*quantum-1
        source = index*quantum-lag
        for voice in range(3):
            active = int(source >= 0)
            rows.append(row(wall=wall, source=source, voice=voice, hz=220*active, confidence=active,
                            voiced=active, active=active, target_midi=57, request_kind=3 if active else 0))
            rows.append(row(kind=1, wall=wall, voice=voice, first_output=index*quantum-offset, count=quantum,
                            available=min(total, (wall//128+1)*128)))
    if finish:
        for voice in range(3):
            rows.append(row(kind=1, wall=total, voice=voice, first_output=quanta*quantum-offset, count=finish, available=total))
    metadata = {"analysis_delay_samples": analysis,
                "voices": [{"underflows": 0, "late_samples": 0, "native_frames": quanta*quantum+finish} for _ in range(3)]}
    return metadata, rows


def write_csv(path, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
