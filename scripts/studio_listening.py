#!/usr/bin/env python3
"""Explicitly approved development listening renders. Never playback or formal grading."""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess

from evaluation_common import ROOT, contained, digest_string, load_json, read_wav_bytes, require, sha256, write_json
from engine_metrics import read_float, read_csv, write_float_wav, callback_metrics
from evaluation_contract import load_contract
from interaction_evaluation import CHANNELS, identity, provenance, verify_provenance, stamp
from studio_pilot import SCOPE, PROTOCOL, validate_documents
from studio_validation import listening_timeline

CLIP_C_PROTOCOL = ROOT / "docs/evidence/pr-06a/clip-c-protocol.json"


def private_path(path):
    path = Path(path)
    if not path.is_absolute(): path = ROOT / path
    require(path.is_relative_to(ROOT), "Private pilot path outside repository")
    result = contained(ROOT, str(path.relative_to(ROOT)))
    require(result.resolve().is_relative_to((ROOT / "evaluation/pr-06a").resolve()), "Expected ignored PR06A evidence path")
    return result


def approval_context(path):
    """Validate authorization BEFORE touching the selected recording."""
    scope, protocol = validate_documents()
    path = private_path(path)
    approval = load_json(path)
    version = approval.get("schema")
    require(version in ("voxide.studio-listening-approval.v1", "voxide.studio-listening-approval.v2")
            and approval.get("approved_by") == "user", "Missing explicit user approval")
    require(approval.get("private_render_authorized") is True and approval.get("listening_only_without_annotations") is True,
            "Listening-only annotation exception/render not approved")
    require(approval.get("formal_accuracy_approved") is False and approval.get("holdout_authorized") is False
            and approval.get("automatic_playback_authorized") is False and approval.get("installation_authorized") is False, "Unexpected approval scope")
    require(approval.get("scope_sha256") == sha256(SCOPE) and approval.get("protocol_sha256") == sha256(PROTOCOL), "Approved public protocol/scope changed")
    proposal_path = private_path(approval["proposal"])
    require(sha256(proposal_path) == approval.get("proposal_sha256"), "Approved source proposal changed")
    proposal = load_json(proposal_path)
    require(proposal.get("schema") == "voxide.studio-listening-proposal.v1" and proposal.get("scope_sha256") == approval["scope_sha256"]
            and proposal.get("protocol_sha256") == approval["protocol_sha256"], "Source proposal binding mismatch")
    index = approval.get("source_index")
    require(type(index) is int and proposal["source"]["index"] == index, "Approval/proposal source mismatch")
    if version == "voxide.studio-listening-approval.v1":
        require(index == 0, "Original approval is for excerpt a only")
    else:
        require(index == 2 and approval.get("trial_id") == "pr06a-clip-c-001", "Extension is for clip c only")
        require(approval.get("extension_protocol_sha256") == sha256(CLIP_C_PROTOCOL), "Clip-c extension protocol changed")
        extension = load_json(CLIP_C_PROTOCOL)
        require(extension.get("schema") == "voxide.studio-listening-extension.v1" and extension.get("id") == approval["trial_id"]
                and extension.get("source_index") == index and extension.get("source_label") == "c", "Unsupported source extension")
        require(extension.get("base_scope_sha256") == approval["scope_sha256"] and extension.get("base_protocol_sha256") == approval["protocol_sha256"]
                and extension.get("candidates") == approval.get("candidates") and extension.get("key_scale") == approval.get("key_scale"), "Extension differs from approved base settings")
    require(approval.get("candidates") == [c["id"] for c in protocol["candidates"]], "Approved candidate set changed")
    require(approval.get("key_scale") == {"root": 0, "scale": 0, "label": "C major diagnostic", "diagnostic_only": True}, "Key/scale differs from explicit trial approval")
    return path, approval, proposal_path, proposal, scope, protocol


def approved_source(proposal):
    selected = proposal["source"]
    manifest = contained(ROOT, selected["corpus"])
    require(manifest.resolve().is_relative_to((ROOT / "evaluation").resolve()), "Corpus outside private evaluation root")
    require(sha256(manifest) == selected["corpus_sha256"], "Approved corpus changed")
    corpus = load_json(manifest)
    require(corpus.get("schema") == "voxide.corpus.v1", "Invalid corpus schema")
    source = corpus["sources"][selected["index"]]
    require(source.get("split") == "development" and source.get("origin") == "recording", "Development recordings only; no holdout")
    require(source.get("id") == selected["source_id"] and source.get("audio") == selected["audio"]
            and source.get("rights") == selected["rights"] and source["rights"].get("local_evaluation_permitted") is True,
            "Source identity/permission changed")
    audio = contained(manifest.parent, source["audio"]["path"])
    require(audio.stat().st_size <= 16*1024*1024, "Pilot source exceeds short-file bound")
    encoded = audio.read_bytes()
    require(hashlib.sha256(encoded).hexdigest() == source["audio"]["sha256"], "Approved audio hash changed")
    info, values = read_wav_bytes(encoded)
    require(all(info[k] == source[k] for k in ("sample_rate", "channels", "bits", "frames")), "Approved WAV metadata mismatch")
    require(info["frames"] == selected["frames"] == 576000 and info["sample_rate"] == selected["sample_rate"] == 48000
            and info["channels"] == 1, "Expected exact 12-second native 48kHz excerpt")
    require(sha256(manifest) == selected["corpus_sha256"], "Corpus changed during source read")
    return audio, encoded, info, values


def check_legacy_consumption(proposal_digest):
    """Resolve only PR06A legacy claim/authorization metadata, never audio payloads.

    Receipt AND proposal relocation must not lose historical consumption. Older
    claims lack a proposal digest, so resolve their bound report or original
    approval; an unresolvable claim fails closed instead of granting a retry.
    """
    evidence = private_path(ROOT / "evaluation/pr-06a")
    for path in evidence.rglob("render-claim.json"):
        path = private_path(path)
        try:
            claim = load_json(path)
            require(claim.get("schema") == "voxide.studio-render-claim.v1" and digest_string(claim.get("approval_sha256")),
                    "Invalid legacy claim")
            report_path = private_path(private_path(claim["run"]) / "report.json")
            if report_path.exists():
                report = load_json(report_path)
                require(report.get("approval_sha256") == claim["approval_sha256"], "Legacy report/approval mismatch")
                digest = report.get("proposal_sha256")
            else:
                original = private_path(path.parent / "approval.json")
                require(sha256(original) == claim["approval_sha256"], "Missing bound legacy authorization")
                digest = load_json(original).get("proposal_sha256")
            require(digest_string(digest), "Unresolved legacy proposal identity")
        except (ValueError, KeyError, OSError) as error:
            raise FileExistsError("Unresolved legacy consumption; new rendering refused: " + str(path)) from error
        if digest == proposal_digest:
            raise FileExistsError("Legacy proposal/trial already consumed: " + str(path))


def claim_render(approval_path, approval, proposal_path, directory):
    """Consume a proposal/trial once, including receipts consumed before v2 claims."""
    # Historical claims stay authoritative and immutable, even when called using
    # a copied or archived receipt rather than its original file location.
    for parent in {approval_path.parent, proposal_path.parent}:
        legacy = private_path(parent / "render-claim.json")
        if legacy.exists():
            raise FileExistsError("Legacy render approval already consumed: " + str(legacy))
    trial = "pr06a-excerpt-a-001" if approval["source_index"] == 0 else "pr06a-clip-c-001"
    proposal_digest = approval["proposal_sha256"]
    require(sha256(proposal_path) == proposal_digest, "Approved proposal changed before consumption")
    check_legacy_consumption(proposal_digest)
    claim = private_path(ROOT / "evaluation/pr-06a/render-claims" / (trial + "-" + proposal_digest + ".json"))
    claim.parent.mkdir(parents=True, exist_ok=True)
    write_json(claim, {"schema": "voxide.studio-render-claim.v2", "trial_id": trial,
               "proposal_sha256": proposal_digest, "approval_sha256": sha256(approval_path),
               "run": str(directory.relative_to(ROOT)), "scope": "One comparison per approved proposal/trial; copies cannot authorize retries"})
    return claim


def safety_checks(native, outputs, source, controls, candidate, protocol, *, playback_gain=1.):
    """No pitch truth is inferred. Every playable export must pass these gates."""
    require(type(playback_gain) in (int, float) and playback_gain in (1., .5), "Only original or approved common half-level playback gain")
    rate = 48000
    frames, tail, delay = len(source), round(rate*.6), rate//10
    require((native["sample_rate"], native["window"], native["hop"], native["mode"], native["treatment"], native["reserve_profile"])
            == (rate, candidate["window"], candidate["hop"], 2, 0, 1), "Native configuration differs from approved trial")
    require(native.get("shift_limit") == 12 and native.get("inactive_uncertain") is True, "Studio range/uncertainty guards not active")
    require(native["source_frames"] == frames and native["zero_tail"] == tail and native["output_frames"] == frames+tail
            and native["latency_samples"] == delay, "Duration/declared-delay mismatch")
    require(set(outputs) == set(CHANNELS) and all(len(x) == frames+tail for x in outputs.values()), "Missing/truncated stem")
    require(all(math.isfinite(x) for audio in outputs.values() for x in audio), "Nonfinite output; no playable export")
    require(len(native["voices"]) == 3 and all(not v["underflows"] and not v["late_samples"] for v in native["voices"]), "Missing/late primary delivery")
    for key in ("missing_metadata", "fifo_overflow", "bad_events", "late_controls", "telemetry_dropped", "invalid_input"):
        require(native[key] == 0, "Native delivery/control failure: " + key)
    require(native["unrendered_finish_peak"] <= 1e-6, "Unrendered nonzero finish tail")
    nulls = {}
    for name, shift in (("lead-direct", 0), ("lead-aligned", delay)):
        maximum = squared = 0.
        for i, value in enumerate(outputs[name]):
            at = i-shift
            expected = source[at] if 0 <= at < frames else 0.
            error = float(value)-expected
            maximum = max(maximum, abs(error)); squared += error*error
        rms = math.sqrt(squared/(frames+tail))
        require(maximum <= 1e-6 and rms <= 1e-7, "Lead null failed")
        nulls[name] = {"max_abs": maximum, "rms": rms, "delay_samples": shift}
    applied, timeline_checks = listening_timeline(native, controls, candidate)
    previous = {}
    active = [0, 0, 0]; seen = [0, 0, 0]
    for row in applied:
        v, source_at, wall = int(row["voice"]), int(row["source"]), int(row["wall"])
        shift = float(row["applied_shift"])
        require(math.isfinite(shift) and abs(shift) <= 12.000001, "Applied ratio exceeds +/-12")
        require(int(row["frame_available"]) <= wall+1, "Future pitch frame consumed")
        require(int(row["voiced"]) != 0 or int(row["active"]) == 0, "Uncertain source retained an active pitched target")
        if v in previous:
            before = previous[v]
            require(source_at > int(before["source"]) and abs(shift-float(before["applied_shift"])) <= 2400*(source_at-int(before["source"]))/rate+1e-6, "Unbounded ratio transition")
        previous[v] = row
        if 0 <= source_at < frames:
            seen[v] += 1; active[v] += int(row["active"])
    maximum_sum_error = 0.
    for i in range(frames+tail):
        expected = outputs["lead-aligned"][i] + sum(outputs["voice"+str(v+1)][i] for v in range(3))/3
        maximum_sum_error = max(maximum_sum_error, abs(float(outputs["sum-aligned"][i])-expected))
    require(maximum_sum_error <= 1e-6, "Complete blend differs from fixed-gain sum")
    # Only fixed, predeclared gains. Raw native stems are NOT playable exports.
    previews = {"dry": array.array("f", outputs["lead-aligned"]), "mix": array.array("f", outputs["sum-aligned"])}
    for v in range(3):
        previews["harmony-"+str(v+1)] = array.array("f", (float(x)/3 for x in outputs["voice"+str(v+1)]))
        require(active[v] > 0 and max(map(abs, previews["harmony-"+str(v+1)]), default=0) > 1e-6, "Silent/inactive harmony is not a three-voice listening result")
    untrimmed_peaks = {name: max(map(abs, values), default=0) for name, values in previews.items()}
    if playback_gain == .5:
        # The amendment is not permission to rescue a full-scale-over preview.
        require(all(value < 1. for value in untrimmed_peaks.values()), "Untrimmed preview reaches full scale; half-level export refused")
        previews = {name: array.array("f", (x*.5 for x in values)) for name, values in previews.items()}
    peaks = {name: max(map(abs, values), default=0) for name, values in previews.items()}
    require(all(value <= protocol["safe_export"]["playable_export_peak_max"] for value in peaks.values()), "Preview exceeds predeclared safe peak ceiling; do not normalize/clip")
    return previews, {"lead_null": nulls, "preview_peaks": peaks, "fixed_sum_max_error": maximum_sum_error, "telemetry": timeline_checks,
                      "playback_gain": playback_gain, "untrimmed_preview_peaks": untrimmed_peaks,
                      "raw_peaks": {name: max(map(abs, audio), default=0) for name, audio in outputs.items()},
                      "voice_active_controls": active, "voice_controls": seen,
                      "scope": "Safe-export engineering checks only; source/target pitch accuracy and aesthetic judgments remain ungraded"}


def run(approval_path, build):
    approval_path, approval, proposal_path, proposal, scope, protocol = approval_context(approval_path)
    build = Path(build).resolve()
    for candidate in protocol["candidates"]:
        require((build/("voxide_"+candidate["engine"]+"_interaction")).is_file(), "Build the isolated Release evaluators first")
    directory = private_path(ROOT / "evaluation/pr-06a" / ("listening-"+stamp()))
    claim = claim_render(approval_path, approval, proposal_path, directory)
    directory.mkdir(parents=True, exist_ok=False)
    report = {"schema": "voxide.studio-listening-run.v1", "status": "running", "cases": [], "key_scale": approval["key_scale"],
              "trial_id": approval.get("trial_id", "pr06a-excerpt-a-001"), "source_index": approval["source_index"],
              "render_claim": str(claim.relative_to(ROOT)),
              "approval_sha256": sha256(approval_path), "proposal_sha256": sha256(proposal_path),
              "scope_sha256": sha256(SCOPE), "protocol_sha256": sha256(PROTOCOL),
              "human_pitch_accuracy": "pending_unannotated_listening_only", "formal_listening": "pending", "product_acceptance": "pending",
              "scope": "User-approved development preference comparison, not a graded vocal or AU qualification"}
    if approval.get("extension_protocol_sha256"):
        report["extension_protocol_sha256"] = approval["extension_protocol_sha256"]
    try:
        p = provenance(build, directory)
        capabilities = {}
        for candidate in protocol["candidates"]:
            result = subprocess.run([str(build/("voxide_"+candidate["engine"]+"_interaction")), "--describe"], capture_output=True, timeout=30)
            require(result.returncode == 0 and not result.stderr, "Cannot attest native build before source access")
            description = json.loads(result.stdout)
            require(description.get("schema") == "voxide.interaction-capabilities.v1" and description.get("compiled_source_identity") == identity()
                    and description.get("profile") == "Release" and not description.get("sanitizer") and description.get("audit_available") is True
                    and description.get("shift_limits") == [12, 24] and description.get("inactive_uncertain_supported") is True,
                    "Stale/sanitized/unsupported native build; source remains unread")
            require(description.get("engine") == {"signalsmith": "signalsmith", "rubberband": "rubberband-r3"}[candidate["engine"]], "Wrong native engine")
            capabilities[candidate["id"]] = description
        report["native_capabilities"] = capabilities
        # Preserve the exact authorization artifacts used, privately.
        for path, name in ((approval_path, "approval.json"), (proposal_path, "proposal.json")):
            shutil.copyfile(path, directory/name)
        require(sha256(directory/"approval.json") == report["approval_sha256"] and sha256(directory/"proposal.json") == report["proposal_sha256"], "Authorization changed during archival")
        source_path, encoded, info, values = approved_source(proposal)
        with (directory/"original-source.wav").open("xb") as stream: stream.write(encoded)
        rms = math.sqrt(sum(x*x for x in values)/len(values))
        require(rms > 1e-8 and math.isfinite(rms), "Silent/invalid source RMS")
        gain = min(1., 10**(-24/20)/rms)
        source = array.array("f", (x*gain for x in values))
        report["source"] = {"audio_sha256": hashlib.sha256(encoded).hexdigest(), "input_float32_sha256": hashlib.sha256(source.tobytes()).hexdigest(),
                            "frames": len(source), "sample_rate": info["sample_rate"], "source_rms": rms, "source_gain": gain,
                            "audio_identity_verified": True, "source_conditions": proposal["source"]["source_conditions"]}
        with (directory/"input-scaled.f32").open("xb") as stream: stream.write(source.tobytes())
        staged = []
        for candidate in protocol["candidates"]:
            case = directory/candidate["id"]; case.mkdir()
            events = case/"events.txt"
            # Explicit diagnostic C major; no key detection or oracle source F0.
            events.write_text("0 0 H 0 0 2741 2 4 0 0 0 1\n")
            command = [str(build/("voxide_"+candidate["engine"]+"_interaction")), "48000", str(candidate["window"]), str(candidate["hop"]),
                       "2", "0", "1", str(events), str(case/"render"), "128", "28800", "12", "1"]
            row = {"candidate": candidate["id"], "command": command, "status": "running"}; report["cases"].append(row)
            write_json(case/"settings.json", {"candidate": candidate, "key_scale": approval["key_scale"], "trial": protocol["initial_trial"],
                       "source_gain": gain, "mode": "tracked scale", "shift_limit": 12, "inactive_uncertain": True})
            result = subprocess.run(command, input=source.tobytes(), capture_output=True, timeout=120)
            (case/"stdout.txt").write_bytes(result.stdout); (case/"stderr.txt").write_bytes(result.stderr)
            row["return_code"] = result.returncode
            if result.returncode:
                row["status"] = "native_failed_no_export"; continue
            try:
                native = load_json(case/"render-native.json")
                require(native["compiled_source_identity"] == identity() and native["profile"] == "Release" and not native["sanitizer"]
                        and native["audit_available"], "Stale/sanitized/unaudited native build")
                require(not result.stderr, "Native diagnostic output requires investigation")
                outputs = {name: read_float(case/("render-"+name+".f32"))[0] for name in CHANNELS}
                controls = read_csv(case/"render-telemetry.csv")
                previews, checks = safety_checks(native, outputs, source, controls, candidate, protocol)
                callback = callback_metrics(read_csv(case/"render-callbacks.csv"), 48000, True, load_contract()["quality"], len(source)+28800)
                row.update(status="safe_export_checks_passed", checks=checks, native=native, callback=callback,
                           callback_allocation_gate="pass" if callback["allocation_calls"] == 0 else "fail_not_waived_by_file_preview",
                           human_pitch_accuracy="pending", formal_listening="pending")
                staged.append((candidate, previews))
            except (ValueError, KeyError) as error:
                row.update(status="withheld_no_playable_export", error=str(error))
        # Only publish playable files AFTER both cases and provenance/source checks.
        verify_provenance(build, p)
        require(sha256(approval_path) == report["approval_sha256"] and sha256(proposal_path) == report["proposal_sha256"], "Authorization changed during render")
        if "extension_protocol_sha256" in report:
            require(sha256(CLIP_C_PROTOCOL) == report["extension_protocol_sha256"], "Extension protocol changed during render")
        require(sha256(source_path) == report["source"]["audio_sha256"], "Source changed during render")
        require(sha256(contained(ROOT, proposal["source"]["corpus"])) == proposal["source"]["corpus_sha256"], "Corpus changed during render")
        report["source_build_unchanged"] = True
        if len(staged) == 2:
            require(staged[0][1]["dry"].tobytes() == staged[1][1]["dry"].tobytes(), "Candidate dry lead differs")
            destination = directory/"previews"; destination.mkdir()
            exports = {}
            dry = staged[0][1]["dry"]
            write_float_wav(destination/"00-dry.wav", 48000, dry.tobytes())
            exports["00-dry.wav"] = sha256(destination/"00-dry.wav")
            for candidate, previews in staged:
                for name, audio in previews.items():
                    if name == "dry": continue
                    filename = candidate["id"]+"-"+name+".wav"
                    write_float_wav(destination/filename, 48000, audio.tobytes()); exports[filename] = sha256(destination/filename)
            write_json(destination/"index.json", {"schema": "voxide.studio-preview-index.v1", "files_sha256": exports,
                       "scope": "Listening preference only, not independent or formal pitch qualification", "key_scale": approval["key_scale"],
                       "trial_id": report["trial_id"], "source_index": report["source_index"],
                       "delay_samples": 4800, "duration_seconds": 12.6, "source_gain": gain, "harmony_gain_each": 1/3,
                       "playback": "Manual only. Begin at low headphone/interface volume; digital peak checks do not guarantee hearing safety.",
                       "suggested_order": ["00-dry.wav", "signalsmith-2048-512-mix.wav", "rubberband-r3-short-mix.wav"],
                       "feedback": protocol["feedback"]})
            report.update(status="previews_ready_preference_and_formal_gates_pending", previews="previews/index.json")
        else:
            report["status"] = "comparison_withheld_due_to_failed_export_checks"
    except Exception as error:
        report.update(status="failed_no_authorized_preview_claim", error=str(error)); raise
    finally:
        write_json(directory/"report.json", report)
        print("Private listening evidence:", (directory/"report.json").relative_to(ROOT))
        print("Status:", report["status"], "— no playback, formal pitch grade or product acceptance.")
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--build", type=Path, default=ROOT/"build/interaction-release")
    args = parser.parse_args()
    run(args.approval, args.build)


if __name__ == "__main__":
    main()
