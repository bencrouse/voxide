#!/usr/bin/env python3
"""Metadata-only PR06A proposal preparation. No audio payload reads or rendering."""
import argparse
import hashlib
from pathlib import Path

from evaluation_common import ROOT, contained, load_json, require, sha256, write_json
from interaction_evaluation import stamp

SCOPE = ROOT / "docs/evidence/pr-06a/studio-scope.json"
PROTOCOL = ROOT / "docs/evidence/pr-06a/listening-protocol.json"
BASELINE_CASES = {
    "signalsmith-2048-512": ("signalsmith", 2048, 512, ["case-0136", "case-0137", "case-0396", "case-0397"]),
    "rubberband-r3-short": ("rubberband", 1, 128, ["case-0188", "case-0189", "case-0448", "case-0449"]),
}


def validate_documents():
    scope, protocol = load_json(SCOPE), load_json(PROTOCOL)
    require(scope.get("schema") == "voxide.studio-pilot-scope.v1" and scope.get("id") == "pr06a-studio-001", "Unsupported studio scope")
    require(protocol.get("schema") == "voxide.studio-listening-protocol.v1" and protocol.get("id") == "pr06a-listening-001", "Unsupported listening protocol")
    require(scope["status"] == "proposal_not_product_qualification" and protocol["status"] == "proposal_requires_explicit_trial_approval", "Preparation must not claim trial approval")
    support = scope["support"]
    require((support["shift_semitones_min"], support["shift_semitones_max"], support["harmony_voices"], support["input_midi_min"], support["input_midi_max"])
            == (-12, 12, 3, 40, 84) and support["sample_rates"] == [44100, 48000] and support["mode"] == "scale", "Unexpected studio support delta")
    for baseline in scope["historical_baselines"]:
        require(sha256(contained(ROOT, baseline["path"])) == baseline["sha256"], "Historical baseline changed")
    require(protocol["scope_path"] == str(SCOPE.relative_to(ROOT)), "Protocol scope binding mismatch")
    retained = scope["retained"]
    for key, value in {"pitch_tolerance_cents": 25, "stable_accuracy_min": .99,
                       "octave_error_fraction_max_exclusive": .001, "wrong_note_duration_ms_max": 50,
                       "callback_allocation_calls_max": 0, "callback_occupancy_p999_max_exclusive": .5,
                       "overdue_callbacks_max": 0, "nonfinite_samples_max": 0, "lead_null_max_abs": 1e-6,
                       "lead_null_rms": 1e-7, "native_repeat_max_abs": 1e-6, "native_repeat_rms": 1e-7}.items():
        require(retained.get(key) == value, "Retained technical gate changed: " + key)
    candidates = protocol["candidates"]
    require(len(candidates) == 2 and {c["id"] for c in candidates} == set(BASELINE_CASES), "Bounded candidate set changed")
    for c in candidates:
        engine, window, hop, cases = BASELINE_CASES[c["id"]]
        require((c["engine"], c["window"], c["hop"], c["basis_case_ids"]) == (engine, window, hop, cases), "Candidate differs from retained configuration")
    trial = protocol["initial_trial"]
    require(trial["degrees"] == [2, 4, 0] and trial["octaves"] == [0, 0, 1] and trial["shift_guard_semitones"] == [-12, 12], "Unapproved musical change")
    require(trial["processing_reserve_ms"] == scope["retained"]["processing_studio_ceiling_ms"] == 100, "Unexpected processing budget")
    require(trial["lead_gain"] == 1 and abs(trial["harmony_gain_each"] - 1/3) < 1e-15, "Unexpected fixed mixer gain")
    require(protocol["safe_export"]["playable_export_peak_max"] == .5, "Unexpected preview ceiling")
    return scope, protocol


def evidence_summary(protocol):
    path = contained(ROOT, protocol["basis_report"])
    snapshot = path.read_bytes()
    report = load_json(path)
    require(report["status"] == "research_complete_not_product_pass" and report["source_build_unchanged"], "Missing retained qualification")
    cases = {row["case"]: row for row in report["cases"]}
    rows = []
    for c in protocol["candidates"]:
        observations = []
        for name in c["basis_case_ids"]:
            row = cases[name]
            require((row["engine"], row["window"], row["hop"], row["reserve_profile"], row["treatment"], row["mode"])
                    == (c["engine"], c["window"], c["hop"], 1, 0, 2), "Retained case identity mismatch")
            require(row["rate"] in (44100, 48000) and row["voicing"] in ("upper", "lower") and not row["impulse"], "Unexpected basis case scope")
            require(row["status"] == "rendered", "Retained render failed")
            m = row["measurements"]
            observations.append({"case": name, "rate": row["rate"], "voicing": row["voicing"], "gates": m["gates"],
                                 "stable_pitch": [v["pitch"]["groups"]["stable"] for v in m["voices"]]})
        rows.append({"candidate": c["id"], "observations": observations, "scope": "Historical synthetic evidence only; all failures retained, not a new vocal/quality pass"})
    digest = hashlib.sha256(snapshot).hexdigest()
    require(sha256(path) == digest, "Basis evidence changed during proposal")
    return {"path": str(path.relative_to(ROOT)), "sha256": digest, "candidates": rows}


def propose(manifest, index=0):
    """Select only explicitly registered metadata. Do NOT call validate_corpus:
    it opens every recording. Actual PCM/hash checks belong after trial approval.
    """
    _, protocol = validate_documents()
    # Check the destination BEFORE reading private metadata. Do not resolve away
    # a symlink into a public directory and then write through its original path.
    directory = contained(ROOT, "evaluation/pr-06a/proposal-" + stamp())
    evaluation = contained(ROOT, "evaluation")
    manifest = Path(manifest)
    if not manifest.is_absolute(): manifest = ROOT / manifest
    require(manifest.is_relative_to(ROOT), "Private manifest must be under ignored evaluation/")
    manifest = contained(ROOT, str(manifest.relative_to(ROOT)))
    require(manifest.is_relative_to(evaluation) and manifest.is_file(), "Private manifest must be under ignored evaluation/")
    snapshot = manifest.read_bytes()
    corpus = load_json(manifest)
    require(corpus.get("schema") == "voxide.corpus.v1", "Unsupported corpus metadata")
    sources = corpus.get("sources", [])
    require(type(index) is int and 0 <= index < len(sources), "Invalid explicit source index")
    source = sources[index]
    require(source.get("split") == "development", "Only development sources may be proposed; no holdout")
    rights = source.get("rights", {})
    require(rights.get("local_evaluation_permitted") is True and isinstance(rights.get("consent_id"), str) and rights["consent_id"], "Missing local evaluation permission")
    require(source.get("sample_rate") in (44100, 48000) and source.get("channels") == 1 and source.get("origin") == "recording", "Source metadata outside studio scope")
    require(type(source.get("frames")) is int and 10 <= source["frames"]/source["sample_rate"] <= 15, "Expected existing short excerpt")
    audio = source.get("audio", {})
    digest = audio.get("sha256", "")
    require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), "Missing declared source hash")
    # Resolve containment/stat only: payload and header remain unread here.
    require(contained(manifest.parent, audio["path"]).is_file(), "Registered source missing")
    manifest_hash = hashlib.sha256(snapshot).hexdigest()
    require(sha256(manifest) == manifest_hash, "Manifest changed during preparation")
    record = {
        "schema": "voxide.studio-listening-proposal.v1", "status": "pending_explicit_trial_approval",
        "scope_sha256": sha256(SCOPE), "protocol_sha256": sha256(PROTOCOL),
        "source": {"corpus": str(manifest.relative_to(ROOT)), "corpus_sha256": manifest_hash, "index": index,
                   "source_id": source["id"], "audio": audio, "sample_rate": source["sample_rate"], "frames": source["frames"],
                   "rights": rights, "source_conditions": source.get("source_conditions", {}), "registered_annotations": len(source.get("annotations", []))},
        "target_key_scale": "pending_user_selection", "audio_payload_read": False, "audio_identity_verified": False,
        "annotation_exception_approved": False, "private_render_authorized": False,
        "basis": evidence_summary(protocol),
        "scope": "Metadata-only proposal. No renderer, annotation bypass, playback, holdout access or formal pitch grade.",
    }
    directory.mkdir(parents=True, exist_ok=False)
    contained(ROOT, str(directory.relative_to(ROOT)))
    write_json(directory / "proposal.json", record)
    return directory / "proposal.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-corpus", type=Path, required=True)
    parser.add_argument("--source-index", type=int, default=0, help="Explicit registered source index; default first excerpt")
    args = parser.parse_args()
    path = propose(args.development_corpus, args.source_index)
    print("Metadata-only proposal:", path.relative_to(ROOT))
    print("Pending: listening-only annotation exception, exact trial approval and user-selected key/scale. No audio rendered/read.")


if __name__ == "__main__":
    main()
