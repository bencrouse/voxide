"""One validated numerical policy shared by scoring and holdout entry points."""
from evaluation_common import CONTRACT, finite, identifier, integer, load_json, require, sha256


def load_contract(path=CONTRACT):
    data = load_json(path)
    require(data.get("schema") == "voxide.evaluation-contract.v1" and identifier(data.get("id")),
            "Invalid contract schema/identity")
    require(data.get("numerical_approval", {}).get("status") == "approved", "Numerical contract approval missing")
    support = data.get("support", {})
    expected = {"input_midi_min": 40, "input_midi_max": 84, "shift_semitones_min": -24,
                "shift_semitones_max": 24, "sample_rates": [44100, 48000], "input_channels": 1,
                "harmony_voices": 3, "original_lead": True}
    require(all(type(support.get(key)) is type(value) and support[key] == value
                for key, value in expected.items()), "Unsupported support envelope; fixture revision required")
    quality, timing = data.get("quality", {}), data.get("timing_ms", {})
    for key in ("pitch_tolerance_cents", "stable_accuracy_min", "octave_error_fraction_max_exclusive",
                "formant_median_fraction_max", "formant_p95_fraction_max"):
        require(finite(quality.get(key)) and quality[key] > 0, "Invalid quality threshold: " + key)
    require(quality["pitch_tolerance_cents"] < 600 and quality["stable_accuracy_min"] <= 1
            and quality["octave_error_fraction_max_exclusive"] <= 1
            and quality["formant_median_fraction_max"] <= quality["formant_p95_fraction_max"] <= 1,
            "Invalid pitch/proportion/formant policy")
    for key in ("processing_mix_ceiling", "recognition_high_p95", "recognition_low_p95",
                "recognition_boundary_hz", "midi_target"):
        require(finite(timing.get(key)) and timing[key] > 0, "Invalid timing threshold: " + key)
    for key in ("max_abs", "rms"):
        value = data.get("deterministic_tolerance", {}).get(key)
        require(finite(value) and value >= 0, "Invalid null tolerance: " + key)
    measurement = data.get("measurement", {})
    for key in ("frame_hop_ms", "settling_dwell_ms"):
        require(finite(measurement.get(key)) and measurement[key] > 0
                and round(measurement[key] * 44100 / 1000) >= 1, "Invalid measurement interval: " + key)
    require(measurement.get("percentile") == "nearest-rank", "Unsupported percentile policy")
    listening = data.get("listening", {})
    for key in ("singers", "excerpts", "user_passages", "annotators", "listeners", "independent_listeners",
                "vocal_engineers_or_producers", "singer_listeners", "excerpt_seconds_min", "excerpt_seconds_max"):
        require(integer(listening.get(key), 1), "Invalid resource requirement: " + key)
    require(listening["annotators"] == 2 and listening["excerpt_seconds_min"] <= listening["excerpt_seconds_max"],
            "Unsupported annotation count/excerpt policy")
    data["_sha256"] = sha256(path)
    return data


def require_holdout_approvals(contract):
    require(contract.get("musical_policy_approval") == "approved", "Musical-policy approval required before holdout use")
    require(contract.get("measurement_protocol_approval") == "approved", "Measurement protocol approval required before holdout use")
    require(contract.get("listening", {}).get("protocol_status") == "approved", "Listening protocol approval required before holdout use")
    require(contract.get("resource_approval") == "approved", "Resource approval required before holdout use")
