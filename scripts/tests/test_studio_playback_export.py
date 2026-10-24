import array
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import studio_playback_export as playback
import studio_listening as listening
from evaluation_common import sha256, write_json, write_wav, read_wav_bytes
from studio_pilot import SCOPE, PROTOCOL, validate_documents
from studio_test_support import synthetic_timeline, write_csv


class PlaybackExportTests(unittest.TestCase):
    def fixture(self, root, *, audio=False):
        run = root/"evaluation/pr-06a/retained"; run.mkdir(parents=True)
        proposal_dir = root/"evaluation/pr-06a/proposal"; proposal_dir.mkdir()
        export_dir = root/"evaluation/pr-06a/export-approval"; export_dir.mkdir()
        _, protocol = validate_documents()
        # Synthetic registered source only. Nothing from ignored evaluation is used.
        source = {"id": "synthetic-c", "split": "development", "origin": "recording", "sample_rate": 48000,
                  "channels": 1, "bits": 24, "frames": 576000, "rights": {"local_evaluation_permitted": True},
                  "audio": {"path": "synthetic.wav", "sha256": "a"*64}}
        if audio:
            write_wav(run/"original-source.wav", 48000, [.01]*576000)
            source["audio"]["sha256"] = sha256(run/"original-source.wav")
        corpus = run/"corpus-manifest-snapshot.json"
        write_json(corpus, {"schema": "voxide.corpus.v1", "sources": [{}, {}, source]})
        selected = {"index": 2, "source_id": source["id"], "rights": source["rights"], "audio": source["audio"],
                    "sample_rate": 48000, "frames": 576000, "corpus_sha256": sha256(corpus)}
        proposal = {"schema": "voxide.studio-listening-proposal.v1", "source": selected,
                    "scope_sha256": sha256(SCOPE), "protocol_sha256": sha256(PROTOCOL)}
        write_json(proposal_dir/"proposal.json", proposal); write_json(run/"proposal.json", proposal)
        key = {"root": 0, "scale": 0, "label": "C major diagnostic", "diagnostic_only": True}
        approval = {"schema": "voxide.studio-listening-approval.v2", "approved_by": "user", "private_render_authorized": True,
                    "listening_only_without_annotations": True, "formal_accuracy_approved": False, "holdout_authorized": False,
                    "automatic_playback_authorized": False, "installation_authorized": False, "source_index": 2,
                    "trial_id": "pr06a-clip-c-001", "extension_protocol_sha256": sha256(listening.CLIP_C_PROTOCOL),
                    "proposal": str((proposal_dir/"proposal.json").relative_to(root)), "proposal_sha256": sha256(proposal_dir/"proposal.json"),
                    "scope_sha256": sha256(SCOPE), "protocol_sha256": sha256(PROTOCOL), "key_scale": key,
                    "candidates": [c["id"] for c in protocol["candidates"]]}
        write_json(run/"approval.json", approval)
        claim = proposal_dir/"render-claim.json"
        write_json(claim, {"approval_sha256": sha256(run/"approval.json"), "run": str(run.relative_to(root))})
        report = {"status": "comparison_withheld_due_to_failed_export_checks", "source_build_unchanged": True,
                  "trial_id": "pr06a-clip-c-001", "source_index": 2, "approval_sha256": sha256(run/"approval.json"),
                  "proposal_sha256": sha256(run/"proposal.json"), "scope_sha256": sha256(SCOPE), "protocol_sha256": sha256(PROTOCOL),
                  "extension_protocol_sha256": sha256(listening.CLIP_C_PROTOCOL), "key_scale": key, "cases": []}
        p = {"files": {}, "binaries": {}}
        for name in playback.IDENTITY_FILES:
            path = run/"source-snapshot"/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("synthetic source\n")
            p["files"][name] = sha256(path)
        p["compiled_source_identity"] = hashlib.sha256("".join(name+"|"+p["files"][name]+"\n" for name in playback.IDENTITY_FILES).encode()).hexdigest()
        (run/"binaries").mkdir()
        for engine in ("signalsmith", "rubberband"):
            path = run/"binaries"/("voxide_"+engine+"_interaction"); path.write_bytes(b"never executed")
            p["binaries"][engine] = sha256(path)
        for name, key_name in (("libengine_allocation_audit.dylib", "audit_sha256"), ("CMakeCache.txt", "cache_sha256")):
            path = run/"binaries"/name; path.write_bytes(b"synthetic metadata"); p[key_name] = sha256(path)
        write_json(run/"provenance.json", p)
        if audio:
            _, values = read_wav_bytes((run/"original-source.wav").read_bytes())
            rms = (sum(x*x for x in values)/len(values))**.5
            gain = min(1., 10**(-24/20)/rms)
            scaled = array.array("f", (x*gain for x in values)); (run/"input-scaled.f32").write_bytes(scaled.tobytes())
            report["source"] = {"audio_sha256": source["audio"]["sha256"], "source_gain": gain, "source_rms": rms,
                                "input_float32_sha256": sha256(run/"input-scaled.f32"), "frames": 576000, "sample_rate": 48000}
            aligned = array.array("f", [0.]*4800); aligned.extend(scaled); aligned.extend([0.]*24000)
            for index, candidate in enumerate(protocol["candidates"]):
                case = run/candidate["id"]; case.mkdir()
                outputs = {name: array.array("f", [0.]*604800) for name in playback.CHANNELS}
                outputs["lead-direct"] = scaled+array.array("f", [0.]*28800); outputs["lead-aligned"] = aligned
                for v in range(3): outputs["voice"+str(v+1)] = array.array("f", (x*.5 for x in aligned))
                # Second candidate has a finite blend crossing only the original margin.
                if index:
                    for v in range(3): outputs["voice"+str(v+1)][5000] = .6
                outputs["sum-aligned"] = array.array("f", (aligned[i]+sum(outputs["voice"+str(v+1)][i] for v in range(3))/3 for i in range(604800)))
                for name, values in outputs.items(): (case/("render-"+name+".f32")).write_bytes(values.tobytes())
                native = {"sample_rate": 48000, "window": candidate["window"], "hop": candidate["hop"], "mode": 2, "treatment": 0,
                          "reserve_profile": 1, "shift_limit": 12, "inactive_uncertain": True, "source_frames": 576000,
                          "zero_tail": 28800, "output_frames": 604800, "latency_samples": 4800, "voices": [{"underflows": 0, "late_samples": 0} for _ in range(3)],
                          "compiled_source_identity": p["compiled_source_identity"], "profile": "Release", "sanitizer": "", "audit_available": True,
                          "unrendered_finish_peak": 0, **{key: 0 for key in ("missing_metadata", "fifo_overflow", "bad_events", "late_controls", "telemetry_dropped", "invalid_input")}}
                metadata, rows = synthetic_timeline(48000, 604800, candidate["engine"])
                native.update(metadata)
                write_json(case/"render-native.json", native)
                write_csv(case/"render-telemetry.csv", rows)
                (case/"stderr.txt").touch(); (case/"events.txt").write_text("0 0 H 0 0 2741 2 4 0 0 0 1\n")
                write_json(case/"settings.json", {"candidate": candidate, "key_scale": key, "trial": protocol["initial_trial"],
                           "source_gain": gain, "mode": "tracked scale", "shift_limit": 12, "inactive_uncertain": True})
                report["cases"].append({"candidate": candidate["id"], "return_code": 0,
                                        "status": "withheld_no_playable_export" if index else "safe_export_checks_passed",
                                        **({"error": "Preview exceeds predeclared safe peak ceiling; do not normalize/clip"} if index else {})})
        else:
            for name in ("input-scaled.f32", "original-source.wav"): (run/name).write_bytes(b"not decoded")
        write_json(run/"report.json", report)
        archive = {str(path.relative_to(run)): sha256(path) for path in run.rglob("*") if path.is_file()}
        write_json(run/"archive-integrity.json", {"schema": "voxide.studio-archive-integrity.v1", "files_sha256": archive})
        receipt = {"schema": "voxide.studio-playback-export-approval.v1", "approved_by": "user", "trial_id": "pr06a-clip-c-half-level-001",
                   "playback_gain": .5, "protocol_sha256": sha256(playback.PROTOCOL), "original_run": str(run.relative_to(root)),
                   "original_report_sha256": sha256(run/"report.json"), "archive_sha256": sha256(run/"archive-integrity.json"),
                   "render_claim_sha256": sha256(claim), "dsp_rerender_authorized": False, "automatic_playback_authorized": False,
                   "formal_acceptance_authorized": False}
        path = export_dir/"approval.json"; write_json(path, receipt)
        return path, receipt, run, archive

    def roots(self, root):
        return patch.multiple(playback, ROOT=root), patch.multiple(listening, ROOT=root)

    def test_receipt_gain_scope_and_bindings_cannot_be_expanded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); path, receipt, _, _ = self.fixture(root)
            for key, value in (("playback_gain", .25), ("candidate_gains", {"rubberband": .5}), ("stem_gains", [.5]),
                               ("original_report_sha256", "0"*64), ("archive_sha256", "0"*64), ("render_claim_sha256", "0"*64),
                               ("protocol_sha256", "0"*64), ("dsp_rerender_authorized", True), ("trial_id", "other")):
                changed = dict(receipt); changed[key] = value; path.write_text(json.dumps(changed))
                a, b = self.roots(root)
                with a, b, self.subTest(key=key), self.assertRaises(ValueError): playback.export_context(path)

    def test_artifact_tampering_and_missing_bindings_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); _, _, run, _ = self.fixture(root)
            playback.verify_archive(run)
            (run/"input-scaled.f32").write_bytes(b"substitution")
            with self.assertRaisesRegex(ValueError, "Retained artifact changed"): playback.verify_archive(run)
            manifest = run/"archive-integrity.json"; data = json.loads(manifest.read_text())
            del data["files_sha256"]["input-scaled.f32"]; manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "Incomplete archive"): playback.verify_archive(run)

    def test_consumed_export_receipt_stops_before_audio_or_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); path, receipt, _, _ = self.fixture(root)
            a, b = self.roots(root)
            with a, b:
                claim = playback.export_claim_path(receipt); claim.parent.mkdir(); claim.write_text("consumed")
                with patch.object(playback, "verify_archive") as verify, patch.object(playback, "retained_source") as source, self.assertRaises(FileExistsError):
                    playback.export(path)
            verify.assert_not_called(); source.assert_not_called(); self.assertEqual(claim.read_text(), "consumed")
            self.assertFalse(list((root/"evaluation/pr-06a").glob("playback-half-*")))

    def test_export_accepts_bound_canonical_render_claim_without_rewriting_legacy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); path, receipt, run, archive = self.fixture(root)
            legacy = root/"evaluation/pr-06a/proposal/render-claim.json"; before = legacy.read_bytes()
            canonical = root/"evaluation/pr-06a/render-claims/approved.json"; canonical.parent.mkdir()
            canonical.write_bytes(before)
            report_path = run/"report.json"; report = json.loads(report_path.read_text())
            report["render_claim"] = str(canonical.relative_to(root)); report_path.write_text(json.dumps(report))
            receipt["original_report_sha256"] = sha256(report_path); receipt["render_claim_sha256"] = sha256(canonical)
            archive["report.json"] = sha256(report_path)
            manifest = run/"archive-integrity.json"
            manifest.write_text(json.dumps({"schema": "voxide.studio-archive-integrity.v1", "files_sha256": archive}))
            receipt["archive_sha256"] = sha256(manifest)
            path.write_text(json.dumps(receipt))
            a, b = self.roots(root)
            with a, b: playback.export_context(path)
            self.assertEqual(legacy.read_bytes(), before)

    def test_complete_synthetic_export_no_dsp_and_original_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); path, _, run, archive = self.fixture(root, audio=True)
            a, b = self.roots(root)
            with a, b, patch("subprocess.run", side_effect=AssertionError("No native rendering permitted")):
                package = playback.export(path)
                with self.assertRaises(FileExistsError): playback.export(path)
                copied = path.parent/"copied.json"; copied.write_bytes(path.read_bytes())
                with self.assertRaises(FileExistsError): playback.export(copied)
            index = json.loads((package/"previews/index.json").read_text())
            self.assertEqual(len(index["files_sha256"]), 9)
            self.assertEqual(index["playback_gain"], .5)
            self.assertTrue(all(p <= .5 for p in index["preview_peaks"].values()))
            for name, digest in index["files_sha256"].items():
                wav = package/"previews"/name; self.assertEqual(sha256(wav), digest)
                data = wav.read_bytes(); self.assertEqual(len(data), 56+604800*4)
                self.assertEqual(struct.unpack_from("<I", data, 24)[0], 48000)
                values = array.array("f"); values.frombytes(data[56:])
                if name == "00-dry.wav": raw = run/"signalsmith-2048-512/render-lead-aligned.f32"; gain = .5
                else:
                    candidate = next(c for c in ("signalsmith-2048-512", "rubberband-r3-short") if name.startswith(c))
                    suffix = name[len(candidate)+1:-4]
                    channel = "sum-aligned" if suffix == "mix" else "voice"+suffix[-1]
                    raw = run/candidate/("render-"+channel+".f32"); gain = .5 if suffix == "mix" else 1/6
                original, _ = playback.read_float(raw)
                if gain == 1/6:
                    expected = array.array("f", (x*.5 for x in array.array("f", (x/3 for x in original))))
                else: expected = array.array("f", (x*.5 for x in original))
                self.assertEqual(values.tobytes(), expected.tobytes())
            self.assertTrue(all(sha256(run/name) == digest for name, digest in archive.items()))
            self.assertFalse((run/"previews").exists())

    def test_second_candidate_delivery_failure_withholds_entire_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); path, receipt, run, archive = self.fixture(root, audio=True)
            # Even a consistently archived failure is not permission to export it.
            native_path = run/"rubberband-r3-short/render-native.json"
            native = json.loads(native_path.read_text()); native["voices"][0]["underflows"] = 1
            native_path.write_text(json.dumps(native)); archive[str(native_path.relative_to(run))] = sha256(native_path)
            manifest = run/"archive-integrity.json"
            manifest.write_text(json.dumps({"schema": "voxide.studio-archive-integrity.v1", "files_sha256": archive}))
            receipt["archive_sha256"] = sha256(manifest); path.write_text(json.dumps(receipt))
            a, b = self.roots(root)
            with a, b, self.assertRaisesRegex(ValueError, "Missing/late primary"): playback.export(path)
            packages = list((root/"evaluation/pr-06a").glob("playback-half-*"))
            self.assertEqual(len(packages), 1)
            self.assertFalse((packages[0]/"previews").exists())
            self.assertEqual(json.loads((packages[0]/"report.json").read_text())["status"], "failed_no_preview_index")


if __name__ == "__main__": unittest.main()
