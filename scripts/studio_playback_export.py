#!/usr/bin/env python3
"""Single-use, approved clip-c half-level export from retained outputs. No DSP/playback."""
import argparse
import array
import hashlib
import math
from pathlib import Path

from evaluation_common import ROOT, contained, load_json, read_wav_bytes, require, sha256, write_json
from engine_metrics import read_csv, read_float, write_float_wav
from interaction_evaluation import CHANNELS, IDENTITY_FILES, stamp
from studio_listening import approval_context, private_path, safety_checks, CLIP_C_PROTOCOL

PROTOCOL = ROOT / "docs/evidence/pr-06a/half-level-export-protocol.json"


def export_context(path):
    path = private_path(path)
    receipt = load_json(path)
    require(receipt.get("schema") == "voxide.studio-playback-export-approval.v1" and receipt.get("approved_by") == "user",
            "Missing explicit playback-export approval")
    require(receipt.get("trial_id") == "pr06a-clip-c-half-level-001" and type(receipt.get("playback_gain")) is float
            and receipt["playback_gain"] == .5, "Only the approved fixed common half-level export")
    require(receipt.get("protocol_sha256") == sha256(PROTOCOL), "Playback-export protocol changed")
    amendment = load_json(PROTOCOL)
    require(amendment.get("id") == receipt["trial_id"] and amendment.get("playback_gain") == .5, "Unsupported playback amendment")
    require(all(receipt.get(key) is False for key in ("dsp_rerender_authorized", "automatic_playback_authorized", "formal_acceptance_authorized")),
            "Unexpected playback-export approval scope")
    require("candidate_gains" not in receipt and "stem_gains" not in receipt, "Per-candidate/stem gains are forbidden")
    run = private_path(receipt["original_run"])
    bindings = {"report.json": "original_report_sha256", "archive-integrity.json": "archive_sha256"}
    for name, key in bindings.items():
        require(sha256(run/name) == receipt.get(key), "Original report/archive binding changed")
    report = load_json(run/"report.json")
    require(report.get("status") == "comparison_withheld_due_to_failed_export_checks" and report.get("source_build_unchanged") is True
            and report.get("trial_id") == "pr06a-clip-c-001" and report.get("source_index") == 2, "Expected original withheld clip-c trial")
    context = approval_context(run/"approval.json")
    _, approval, proposal_path, proposal, _, protocol = context
    require(report["approval_sha256"] == sha256(run/"approval.json") and report["proposal_sha256"] == sha256(proposal_path)
            == sha256(run/"proposal.json"), "Original authorization binding changed")
    require(report["scope_sha256"] == approval["scope_sha256"] and report["protocol_sha256"] == approval["protocol_sha256"]
            and report["extension_protocol_sha256"] == sha256(CLIP_C_PROTOCOL) and report["key_scale"] == approval["key_scale"], "Original protocol mismatch")
    claim_path = private_path(report.get("render_claim", proposal_path.parent/"render-claim.json"))
    require(sha256(claim_path) == receipt.get("render_claim_sha256"), "Consumed render claim changed")
    claim = load_json(claim_path)
    require(claim.get("approval_sha256") == report["approval_sha256"] and private_path(claim["run"]) == run,
            "Original render claim does not match retained run")
    require(protocol["safe_export"]["playable_export_peak_max"] == .5, "Original ceiling must remain unchanged")
    return path, receipt, run, report, proposal, protocol


def verify_archive(run):
    """Validate historical snapshots, not today's source/build identity."""
    archive = load_json(run/"archive-integrity.json")
    require(archive.get("schema") == "voxide.studio-archive-integrity.v1", "Invalid archive manifest")
    files = archive["files_sha256"]
    required = {"report.json", "approval.json", "proposal.json", "provenance.json", "original-source.wav", "input-scaled.f32", "corpus-manifest-snapshot.json"}
    require(required <= files.keys(), "Incomplete archive bindings")
    for name, digest in files.items():
        require(sha256(contained(run, name)) == digest, "Retained artifact changed: " + name)
    provenance = load_json(run/"provenance.json")
    for name, digest in provenance["files"].items():
        snapshot = "source-snapshot/"+name
        require(files.get(snapshot) == digest, "Archived source provenance mismatch")
    for engine, digest in provenance["binaries"].items():
        require(files.get("binaries/voxide_"+engine+"_interaction") == digest, "Archived binary provenance mismatch")
    require(set(provenance["binaries"]) == {"signalsmith", "rubberband"}, "Incomplete candidate binaries")
    for name, key in (("libengine_allocation_audit.dylib", "audit_sha256"), ("CMakeCache.txt", "cache_sha256")):
        require(files.get("binaries/"+name) == provenance[key], "Archived runtime/build provenance mismatch")
    compiled = hashlib.sha256("".join(name+"|"+provenance["files"][name]+"\n" for name in IDENTITY_FILES).encode()).hexdigest()
    require(compiled == provenance["compiled_source_identity"], "Archived compiled identity mismatch")
    return files, provenance


def retained_source(run, report, proposal):
    selected = proposal["source"]
    require(sha256(run/"corpus-manifest-snapshot.json") == selected["corpus_sha256"], "Archived corpus changed")
    corpus = load_json(run/"corpus-manifest-snapshot.json")
    source = corpus["sources"][2]
    require(corpus.get("schema") == "voxide.corpus.v1" and selected["index"] == 2 and source.get("split") == "development"
            and source.get("origin") == "recording" and source["id"] == selected["source_id"] and source["audio"] == selected["audio"]
            and source["rights"] == selected["rights"] and source["rights"].get("local_evaluation_permitted") is True, "Archived source identity/permission mismatch")
    digest = sha256(run/"original-source.wav")
    require(digest == selected["audio"]["sha256"] == report["source"]["audio_sha256"], "Archived source audio changed")
    info, values = read_wav_bytes((run/"original-source.wav").read_bytes())
    require(all(info[k] == source[k] for k in ("sample_rate", "channels", "bits", "frames"))
            and info["frames"] == selected["frames"] == report["source"]["frames"] == 576000
            and info["sample_rate"] == selected["sample_rate"] == report["source"]["sample_rate"] == 48000 and info["channels"] == 1, "Archived source metadata mismatch")
    rms = math.sqrt(sum(x*x for x in values)/len(values))
    require(math.isfinite(rms) and rms > 1e-8, "Invalid archived source RMS")
    gain = min(1., 10**(-24/20)/rms)
    expected = array.array("f", (x*gain for x in values))
    scaled, payload = read_float(run/"input-scaled.f32")
    require(gain == report["source"]["source_gain"] and rms == report["source"]["source_rms"] and expected.tobytes() == payload
            and hashlib.sha256(payload).hexdigest() == report["source"]["input_float32_sha256"], "Retained DSP input/attenuation changed")
    return scaled


def export_claim_path(receipt):
    # Key by retained run + amendment, not receipt location: copying a receipt
    # into another directory cannot authorize another export.
    return private_path(ROOT/"evaluation/pr-06a/playback-export-claims"/
                        ("pr06a-clip-c-half-level-001-"+receipt["original_report_sha256"]+".json"))


def export(path):
    path, receipt, run, original, proposal, protocol = export_context(path)
    receipt_digest = sha256(path)
    directory = ROOT/"evaluation/pr-06a"/("playback-half-"+stamp())
    # Claim BEFORE reading any audio; consumed approvals cannot publish again.
    claim_path = export_claim_path(receipt); claim_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(claim_path, {"schema": "voxide.studio-playback-export-claim.v1", "approval_sha256": receipt_digest,
               "approval": str(path.relative_to(ROOT)),
               "package": str(directory.relative_to(ROOT)), "original_report_sha256": receipt["original_report_sha256"]})
    directory.mkdir(parents=True, exist_ok=False)
    result = {"schema": "voxide.studio-playback-export.v1", "status": "failed_no_preview_index", "playback_gain": .5,
              "original_run": str(run.relative_to(ROOT)), "original_report_sha256": receipt["original_report_sha256"],
              "archive_sha256": receipt["archive_sha256"], "approval_sha256": receipt_digest, "cases": [],
              "claim": str(claim_path.relative_to(ROOT)),
              "scope": "Playback-only export; original withheld result unchanged, no DSP rerender or formal acceptance"}
    try:
        files, provenance = verify_archive(run)
        source = retained_source(run, original, proposal)
        require([c["candidate"] for c in original["cases"]] == [c["id"] for c in protocol["candidates"]], "Original candidate set mismatch")
        require([c["status"] for c in original["cases"]] == ["safe_export_checks_passed", "withheld_no_playable_export"]
                and original["cases"][1].get("error") == "Preview exceeds predeclared safe peak ceiling; do not normalize/clip", "Unexpected original failure")
        staged = []
        for candidate, row in zip(protocol["candidates"], original["cases"]):
            case = run/candidate["id"]
            names = ["render-native.json", "render-telemetry.csv", "stderr.txt", "settings.json", "events.txt"]
            names += ["render-"+name+".f32" for name in CHANNELS]
            require(all(candidate["id"]+"/"+name in files for name in names), "Unbound retained output/control artifact")
            require(row["return_code"] == 0 and not (case/"stderr.txt").read_bytes(), "Native execution/diagnostic failure")
            native = load_json(case/"render-native.json")
            require(native["compiled_source_identity"] == provenance["compiled_source_identity"] and native["profile"] == "Release"
                    and not native["sanitizer"] and native["audit_available"] is True, "Original native provenance mismatch")
            settings = load_json(case/"settings.json")
            require(settings == {"candidate": candidate, "key_scale": original["key_scale"], "trial": protocol["initial_trial"],
                    "source_gain": original["source"]["source_gain"], "mode": "tracked scale", "shift_limit": 12, "inactive_uncertain": True}
                    and (case/"events.txt").read_text() == "0 0 H 0 0 2741 2 4 0 0 0 1\n", "Retained DSP settings changed")
            outputs = {name: read_float(case/("render-"+name+".f32"))[0] for name in CHANNELS}
            previews, checks = safety_checks(native, outputs, source, read_csv(case/"render-telemetry.csv"), candidate, protocol, playback_gain=.5)
            result["cases"].append({"candidate": candidate["id"], "checks": checks,
                                    "callback_allocation_gate": "not_requalified_or_waived_by_playback_export"})
            staged.append((candidate, previews))
        require(staged[0][1]["dry"].tobytes() == staged[1][1]["dry"].tobytes(), "Candidate dry mismatch")
        # Recheck all bound inputs before publishing either candidate.
        export_context(path); verify_archive(run)
        require(sha256(path) == receipt_digest, "Export receipt changed during validation")
        write_json(directory/"approval.json", receipt)
        write_json(directory/"raw-identities.json", {"original_archive_sha256": receipt["archive_sha256"], "files_sha256": files})
        destination = directory/"previews"; destination.mkdir()
        exports = {}; peaks = {}
        for candidate, previews in staged:
            for name, audio in previews.items():
                filename = "00-dry.wav" if name == "dry" else candidate["id"]+"-"+name+".wav"
                if filename in exports: continue
                payload = audio.tobytes()
                write_float_wav(destination/filename, 48000, payload)
                require((destination/filename).read_bytes()[56:] == payload, "Export WAV payload changed")
                exports[filename] = sha256(destination/filename); peaks[filename] = max(map(abs, audio))
        require(len(exports) == 9, "Incomplete playback package")
        result.update(status="half_level_previews_ready_formal_gates_pending", previews="previews/index.json")
        write_json(directory/"report.json", result)
        write_json(destination/"index.json", {"schema": "voxide.studio-playback-preview-index.v1", "files_sha256": exports,
                   "report_sha256": sha256(directory/"report.json"), "raw_identities_sha256": sha256(directory/"raw-identities.json"),
                   "original_run": result["original_run"], "original_report_sha256": receipt["original_report_sha256"],
                   "playback_gain": .5, "source_gain": original["source"]["source_gain"], "harmony_gain_each_before_playback": 1/3,
                   "preview_peaks": peaks, "peak_ceiling": .5, "sample_rate": 48000, "frames": 604800,
                   "duration_seconds": 12.6, "delay_samples": 4800, "key_scale": original["key_scale"],
                   "playback": "Manual only; begin at low headphone/interface volume. Export guards do not guarantee hearing safety.",
                   "feedback": protocol["feedback"], "scope": result["scope"]})
    except Exception as error:
        if not (directory/"report.json").exists():
            result["error"] = str(error); write_json(directory/"report.json", result)
        raise
    print("Half-level listening package:", (directory/"previews").relative_to(ROOT))
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", type=Path, required=True)
    export(parser.parse_args().approval)


if __name__ == "__main__": main()
