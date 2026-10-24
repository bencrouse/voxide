import array
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import studio_listening as listening
from studio_pilot import validate_documents, SCOPE, PROTOCOL
from evaluation_common import sha256
from studio_test_support import synthetic_timeline


class StudioListeningTests(unittest.TestCase):
    def fixture(self, engine="signalsmith"):
        frames, delay, tail = 4800, 4800, 28800
        source = array.array("f", [.01]*frames)
        direct = array.array("f", source); direct.extend([0.]*tail)
        aligned = array.array("f", [0.]*delay); aligned.extend(source); aligned.extend([0.]*(tail-delay))
        outputs = {name: array.array("f", [0.]*(frames+tail)) for name in listening.CHANNELS}
        outputs["lead-direct"] = direct; outputs["lead-aligned"] = aligned
        for v in range(3): outputs["voice"+str(v+1)] = array.array("f", (x*.5 for x in aligned))
        outputs["sum-aligned"] = array.array("f", (x*1.5 for x in aligned))
        native = {"sample_rate": 48000, "window": 2048, "hop": 512, "mode": 2, "treatment": 0, "reserve_profile": 1,
                  "shift_limit": 12, "inactive_uncertain": True, "source_frames": frames, "zero_tail": tail,
                  "output_frames": frames+tail, "latency_samples": delay, "voices": [{"underflows": 0, "late_samples": 0} for _ in range(3)],
                  "missing_metadata": 0, "fifo_overflow": 0, "bad_events": 0, "late_controls": 0, "telemetry_dropped": 0, "invalid_input": 0,
                  "unrendered_finish_peak": 0}
        metadata, controls = synthetic_timeline(48000, frames+tail, engine)
        native.update(metadata)
        _, protocol = validate_documents()
        candidate = next(c for c in protocol["candidates"] if c["engine"] == engine)
        native.update(window=candidate["window"], hop=candidate["hop"])
        return native, outputs, source, controls, candidate, protocol

    def test_positive_synthetic_export_preserves_fixed_gains_and_null(self):
        previews, checks = listening.safety_checks(*self.fixture())
        self.assertEqual(set(previews), {"dry", "mix", "harmony-1", "harmony-2", "harmony-3"})
        self.assertEqual(checks["lead_null"]["lead-aligned"]["max_abs"], 0)
        self.assertAlmostEqual(max(previews["harmony-1"]), .005/3, places=8)

    def test_unsafe_and_invalid_native_outputs_are_withheld_not_repaired(self):
        for fault in ("nan", "loud", "null", "truncated", "missing", "old_guard", "uncertainty", "silent", "tail"):
            native, outputs, source, controls, candidate, protocol = self.fixture()
            if fault == "nan": outputs["native1"][100] = float("nan")
            elif fault == "loud":
                for v in range(3): outputs["voice"+str(v+1)][5000] = 2
                outputs["sum-aligned"][5000] = outputs["lead-aligned"][5000]+2
            elif fault == "null": outputs["lead-aligned"][5000] = .2
            elif fault == "truncated": outputs["voice1"].pop()
            elif fault == "missing": native["voices"][0]["underflows"] = 1
            elif fault == "old_guard": native["shift_limit"] = 24
            elif fault == "uncertainty":
                next(r for r in controls if r["kind"] == "0" and r["active"] == "1")["voiced"] = "0"
            elif fault == "silent":
                for v in range(3): outputs["voice"+str(v+1)] = array.array("f", [0.]*len(outputs["voice1"]))
                outputs["sum-aligned"] = array.array("f", outputs["lead-aligned"])
            else: native["unrendered_finish_peak"] = .01
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                listening.safety_checks(native, outputs, source, controls, candidate, protocol)

    def test_future_pitch_and_out_of_range_control_are_refused(self):
        for key, value in (("frame_available", "999999"), ("applied_shift", "13")):
            data = self.fixture(); next(r for r in data[3] if r["kind"] == "0")[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): listening.safety_checks(*data)

    def test_half_level_applies_identically_to_every_preview(self):
        data = self.fixture()
        original, _ = listening.safety_checks(*data)
        trimmed, checks = listening.safety_checks(*data, playback_gain=.5)
        self.assertEqual(checks["playback_gain"], .5)
        for name in original:
            self.assertEqual(trimmed[name].tobytes(), array.array("f", (x*.5 for x in original[name])).tobytes())

    def test_half_level_keeps_full_scale_nonfinite_and_delivery_failures(self):
        for fault in ("full_scale", "nonfinite", "missing", "fixed_sum", "ceiling"):
            data = self.fixture(); native, outputs, _, _, _, protocol = data
            if fault in ("full_scale", "ceiling"):
                for v in range(3): outputs["voice"+str(v+1)][5000] = 1.
                outputs["sum-aligned"][5000] = outputs["lead-aligned"][5000]+1.
            elif fault == "nonfinite": outputs["native2"][5000] = float("inf")
            elif fault == "missing": native["voices"][2]["late_samples"] = 1
            else: outputs["sum-aligned"][5000] = .1
            if fault == "ceiling": protocol["safe_export"]["playable_export_peak_max"] = .001
            with self.subTest(fault=fault), self.assertRaises(ValueError): listening.safety_checks(*data, playback_gain=.5)

    def test_half_level_can_clear_margin_but_not_original_result(self):
        data = self.fixture(); outputs = data[1]
        for v in range(3): outputs["voice"+str(v+1)][5000] = .6
        outputs["sum-aligned"][5000] = outputs["lead-aligned"][5000]+.6
        with self.assertRaisesRegex(ValueError, "safe peak ceiling"): listening.safety_checks(*data)
        previews, _ = listening.safety_checks(*data, playback_gain=.5)
        self.assertLess(max(previews["mix"]), .5)
        with self.assertRaisesRegex(ValueError, "safe peak ceiling"): listening.safety_checks(*data)

    def test_arbitrary_playback_gains_are_refused(self):
        for gain in (0, .25, .75, 2, True, float("nan"), {"signalsmith": .5}):
            with self.subTest(gain=gain), self.assertRaises(ValueError): listening.safety_checks(*self.fixture(), playback_gain=gain)

    def test_incomplete_or_invalid_telemetry_never_authorizes_export(self):
        for fault in ("three_rows", "middle_control", "head_control", "tail_control", "no_output", "middle_output", "tail_output",
                      "request_missing", "request_invalid", "request_extra", "output_deadline", "callback_clock", "epoch", "columns"):
            data = self.fixture("rubberband" if fault == "output_deadline" else "signalsmith"); rows = data[3]
            if fault == "three_rows": rows[:] = [next(r for r in rows if r["kind"] == "0" and r["voice"] == str(v) and r["active"] == "1") for v in range(3)]
            elif fault in ("middle_control", "head_control", "tail_control", "middle_output", "tail_output"):
                kind = "0" if fault.endswith("control") else "1"
                indices = [i for i, r in enumerate(rows) if r["kind"] == kind and r["voice"] == "0"]
                at = indices[0] if fault == "head_control" else indices[-1] if fault.startswith("tail") else indices[len(indices)//2]
                rows.pop(at)
            elif fault == "no_output": rows[:] = [r for r in rows if r["kind"] != "1"]
            elif fault == "request_missing": rows.pop(0)
            elif fault == "request_invalid": rows[0]["available"] = "999999"
            elif fault == "request_extra": rows.insert(0, copy.copy(rows[0]))
            elif fault == "output_deadline":
                total = data[0]["output_frames"]
                for row in rows:
                    if row["kind"] == "1":
                        wall = min(total, int(row["wall"])+5120)
                        row["wall"] = str(wall); row["available"] = str(min(total, (wall//128+1)*128))
                rows.sort(key=lambda r: int(r["wall"]))
            elif fault == "callback_clock": next(r for r in rows if r["kind"] == "1")["available"] = "0"
            elif fault == "epoch": rows[-1]["epoch"] = "1"
            else: del rows[-1]["frame_begin"]
            with self.subTest(fault=fault), self.assertRaisesRegex(ValueError, "delivery deadline" if fault == "output_deadline" else ".*"):
                listening.safety_checks(*data)

    def test_control_grid_cannot_be_hidden_by_also_truncating_native_counts(self):
        data = self.fixture(); rows = data[3]
        # Even coherent output counter edits cannot excuse a missing control tail.
        last = max(int(r["source"]) for r in rows if r["kind"] == "0")
        rows[:] = [r for r in rows if not (r["kind"] == "0" and int(r["source"]) == last)]
        with self.assertRaisesRegex(ValueError, "control quantum/tail"): listening.safety_checks(*data)

    def test_collapsed_and_backdated_packets_cannot_forge_output_coverage(self):
        for engine in ("signalsmith", "rubberband"):
            for fault in ("collapsed", "backdated"):
                data = self.fixture(engine); native, _, _, rows, candidate, _ = data
                if fault == "collapsed":
                    packets = []
                    for voice in range(3):
                        row = copy.copy(next(r for r in rows if r["kind"] == "1" and r["voice"] == str(voice)))
                        row.update(wall="0", available="128", count=str(native["voices"][voice]["native_frames"]))
                        packets.append(row)
                    rows[:] = [r for r in rows if r["kind"] != "1"] + packets
                else:
                    for row in rows:
                        if row["kind"] == "1": row.update(wall="0", available="128")
                rows.sort(key=lambda r: int(r["wall"]))
                with self.subTest(engine=engine, fault=fault), self.assertRaisesRegex(ValueError, "packet|retrieval"):
                    listening.safety_checks(*data)

    def test_rubberband_packets_cannot_claim_more_frames_than_supplied(self):
        data = self.fixture("rubberband")
        next(r for r in data[3] if r["kind"] == "1")["count"] = "1024"
        with self.assertRaisesRegex(ValueError, "Noncausal Rubber Band"): listening.safety_checks(*data)

    def test_signalsmith_packet_size_is_not_just_an_unchecked_total(self):
        data = self.fixture()
        next(r for r in data[3] if r["kind"] == "1")["count"] = "256"
        with self.assertRaisesRegex(ValueError, "production clock/count"): listening.safety_checks(*data)

    def approval_fixture(self, root):
        directory = root/"evaluation/pr-06a/proposal"; directory.mkdir(parents=True)
        proposal = directory/"proposal.json"
        proposal.write_text(json.dumps({"schema": "voxide.studio-listening-proposal.v1", "source": {"index": 0},
                                       "scope_sha256": sha256(SCOPE), "protocol_sha256": sha256(PROTOCOL)}))
        approval = {"schema": "voxide.studio-listening-approval.v1", "approved_by": "user", "private_render_authorized": True,
                    "listening_only_without_annotations": True, "formal_accuracy_approved": False, "holdout_authorized": False,
                    "automatic_playback_authorized": False, "installation_authorized": False,
                    "scope_sha256": sha256(SCOPE), "protocol_sha256": sha256(PROTOCOL),
                    "proposal": str(proposal.relative_to(root)), "proposal_sha256": sha256(proposal), "source_index": 0,
                    "candidates": ["signalsmith-2048-512", "rubberband-r3-short"],
                    "key_scale": {"root": 0, "scale": 0, "label": "C major diagnostic", "diagnostic_only": True}}
        path = directory/"approval.json"; path.write_text(json.dumps(approval))
        return path, approval

    def test_approval_is_required_and_cannot_expand_to_other_scope(self):
        documents = validate_documents()
        for fault in (None, "exception", "source", "candidate", "key", "formal", "protocol"):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve(); path, approval = self.approval_fixture(root)
                if fault == "exception": approval["listening_only_without_annotations"] = False
                elif fault == "source": approval["source_index"] = 2
                elif fault == "candidate": approval["candidates"].append("rubberband-standard")
                elif fault == "key": approval["key_scale"]["root"] = 1
                elif fault == "formal": approval["formal_accuracy_approved"] = True
                elif fault == "protocol": approval["protocol_sha256"] = "0"*64
                path.write_text(json.dumps(approval))
                with patch("studio_listening.ROOT", root), patch("studio_listening.validate_documents", return_value=documents):
                    if fault is None: self.assertEqual(listening.approval_context(path)[1], approval)
                    else:
                        with self.subTest(fault=fault), self.assertRaises(ValueError): listening.approval_context(path)

    def test_audio_substitution_is_refused_before_decode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); directory = root/"evaluation/existing"; directory.mkdir(parents=True)
            audio = directory/"source.wav"; audio.write_bytes(b"substituted recording")
            rights = {"local_evaluation_permitted": True}; record = {"path": "source.wav", "sha256": "a"*64}
            source = {"split": "development", "origin": "recording", "id": "source-a", "audio": record, "rights": rights}
            manifest = directory/"corpus.json"; manifest.write_text(json.dumps({"schema": "voxide.corpus.v1", "sources": [source]}))
            proposal = {"source": {"corpus": str(manifest.relative_to(root)), "corpus_sha256": sha256(manifest), "index": 0,
                                   "source_id": "source-a", "audio": record, "rights": rights}}
            with patch("studio_listening.ROOT", root), patch("studio_listening.read_wav_bytes") as decode, self.assertRaisesRegex(ValueError, "audio hash changed"):
                listening.approved_source(proposal)
            decode.assert_not_called()

    def test_clip_c_requires_its_own_versioned_bound_receipt(self):
        documents = validate_documents()
        for fault in (None, "old_receipt", "source_b", "extension_hash", "trial_id"):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve(); path, approval = self.approval_fixture(root)
                proposal = root / approval["proposal"]
                data = json.loads(proposal.read_text()); data["source"]["index"] = 2
                proposal.write_text(json.dumps(data))
                approval.update(schema="voxide.studio-listening-approval.v2", source_index=2, trial_id="pr06a-clip-c-001",
                                proposal_sha256=sha256(proposal), extension_protocol_sha256=sha256(listening.CLIP_C_PROTOCOL))
                if fault == "old_receipt": approval["schema"] = "voxide.studio-listening-approval.v1"
                elif fault == "source_b": approval["source_index"] = 1
                elif fault == "extension_hash": approval["extension_protocol_sha256"] = "0"*64
                elif fault == "trial_id": approval["trial_id"] = "arbitrary-new-trial"
                path.write_text(json.dumps(approval))
                with patch("studio_listening.ROOT", root), patch("studio_listening.validate_documents", return_value=documents):
                    if fault is None: self.assertEqual(listening.approval_context(path)[1], approval)
                    else:
                        with self.subTest(fault=fault), self.assertRaises(ValueError): listening.approval_context(path)

    def test_source_c_cannot_be_substituted_under_original_approval(self):
        documents = validate_documents()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); path, approval = self.approval_fixture(root)
            proposal = root / approval["proposal"]
            data = json.loads(proposal.read_text()); data["source"]["index"] = 2
            proposal.write_text(json.dumps(data))
            with patch("studio_listening.ROOT", root), patch("studio_listening.validate_documents", return_value=documents), self.assertRaisesRegex(ValueError, "proposal changed"):
                listening.approval_context(path)

    def test_consumed_receipt_cannot_render_or_read_audio_again(self):
        documents = validate_documents()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); path, _ = self.approval_fixture(root)
            claim = path.parent / "render-claim.json"; claim.write_text('{"already_consumed":true}\n')
            build = root / "build/test"; build.mkdir(parents=True)
            for engine in ("signalsmith", "rubberband"):
                (build / ("voxide_" + engine + "_interaction")).touch()
            with patch("studio_listening.ROOT", root), patch("studio_listening.validate_documents", return_value=documents), \
                 patch("studio_listening.approved_source") as read_audio, patch("studio_listening.subprocess.run") as execute, self.assertRaises(FileExistsError):
                listening.run(path, build)
            read_audio.assert_not_called(); execute.assert_not_called()
            self.assertEqual(claim.read_text(), '{"already_consumed":true}\n')

    def test_copied_and_archived_receipts_honor_legacy_consumption(self):
        documents = validate_documents()
        for archived in (False, True):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve(); path, approval = self.approval_fixture(root)
                legacy = path.parent/"render-claim.json"; legacy.write_text("consumed, never rewrite")
                destination = root/"evaluation/pr-06a"/("archive" if archived else "copy"); destination.mkdir()
                copy_path = destination/"approval.json"; copy_path.write_bytes(path.read_bytes())
                build = root/"build"; build.mkdir()
                for engine in ("signalsmith", "rubberband"): (build/("voxide_"+engine+"_interaction")).touch()
                with patch.object(listening, "ROOT", root), patch.object(listening, "validate_documents", return_value=documents), \
                     patch.object(listening, "approved_source") as read_audio, patch.object(listening, "provenance") as attest, self.assertRaises(FileExistsError):
                    listening.run(copy_path, build)
                read_audio.assert_not_called(); attest.assert_not_called()
                self.assertEqual(legacy.read_text(), "consumed, never rewrite")
                self.assertFalse(list((root/"evaluation/pr-06a").glob("listening-*")))

    def test_canonical_claim_survives_receipt_and_proposal_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); path, approval = self.approval_fixture(root)
            proposal = root/approval["proposal"]
            with patch.object(listening, "ROOT", root):
                claim = listening.claim_render(path, approval, proposal, root/"evaluation/pr-06a/run")
                before = claim.read_bytes()
                copied = root/"evaluation/pr-06a/copied"; copied.mkdir()
                copy_path = copied/"approval.json"; copy_path.write_bytes(path.read_bytes())
                copied_proposal = copied/"proposal.json"; copied_proposal.write_bytes(proposal.read_bytes())
                for candidate_proposal in (proposal, copied_proposal):
                    with self.assertRaises(FileExistsError):
                        listening.claim_render(copy_path, approval, candidate_proposal, root/"evaluation/pr-06a/another")
                self.assertEqual(claim.read_bytes(), before)

    def test_failed_attempt_claim_blocks_copied_receipt_before_source_read(self):
        documents = validate_documents()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); path, _ = self.approval_fixture(root)
            build = root/"build"; build.mkdir()
            for engine in ("signalsmith", "rubberband"): (build/("voxide_"+engine+"_interaction")).touch()
            with patch.object(listening, "ROOT", root), patch.object(listening, "validate_documents", return_value=documents), \
                 patch.object(listening, "approved_source") as read_audio, patch.object(listening, "provenance", side_effect=RuntimeError("stopped before audio")) as attest:
                with self.assertRaisesRegex(RuntimeError, "stopped before audio"): listening.run(path, build)
                copied = root/"evaluation/pr-06a/copy"; copied.mkdir()
                copy_path = copied/"approval.json"; copy_path.write_bytes(path.read_bytes())
                with self.assertRaises(FileExistsError): listening.run(copy_path, build)
                read_audio.assert_not_called(); self.assertEqual(attest.call_count, 1)
                self.assertEqual(len(list((root/"evaluation/pr-06a").glob("listening-*"))), 1)

    def test_changed_proposal_cannot_consume_a_different_canonical_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); path, approval = self.approval_fixture(root)
            proposal = root/approval["proposal"]; proposal.write_text(proposal.read_text()+"\n")
            with patch.object(listening, "ROOT", root), self.assertRaisesRegex(ValueError, "changed before consumption"):
                listening.claim_render(path, approval, proposal, root/"evaluation/pr-06a/run")
            self.assertFalse((root/"evaluation/pr-06a/render-claims").exists())

    def test_legacy_consumption_survives_relocated_proposal_through_entry_point(self):
        documents = validate_documents()
        for has_report in (False, True):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve(); path, approval = self.approval_fixture(root)
                run = root/"evaluation/pr-06a/legacy-run"; run.mkdir()
                claim = path.parent/"render-claim.json"
                claim.write_text(json.dumps({"schema": "voxide.studio-render-claim.v1", "approval_sha256": sha256(path), "run": str(run.relative_to(root))}))
                if has_report:
                    (run/"report.json").write_text(json.dumps({"approval_sha256": sha256(path), "proposal_sha256": approval["proposal_sha256"]}))
                before = claim.read_bytes()
                copied = root/"evaluation/pr-06a/relocated"; copied.mkdir()
                proposal_copy = copied/"proposal.json"; proposal_copy.write_bytes((root/approval["proposal"]).read_bytes())
                relocated = dict(approval); relocated["proposal"] = str(proposal_copy.relative_to(root))
                receipt_copy = copied/"approval.json"; receipt_copy.write_text(json.dumps(relocated))
                build = root/"build"; build.mkdir()
                for engine in ("signalsmith", "rubberband"): (build/("voxide_"+engine+"_interaction")).touch()
                with patch.object(listening, "ROOT", root), patch.object(listening, "validate_documents", return_value=documents), \
                     patch.object(listening, "approved_source") as audio, patch.object(listening, "provenance") as attest:
                    listening.approval_context(receipt_copy)  # Authorization itself is valid.
                    with self.assertRaisesRegex(FileExistsError, "already consumed"): listening.run(receipt_copy, build)
                audio.assert_not_called(); attest.assert_not_called()
                self.assertEqual(claim.read_bytes(), before)
                self.assertFalse(list((root/"evaluation/pr-06a").glob("listening-*")))

    def test_unresolvable_legacy_consumption_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); path, approval = self.approval_fixture(root)
            unknown = root/"evaluation/pr-06a/unknown"; unknown.mkdir()
            (unknown/"render-claim.json").write_text('{"schema":"voxide.studio-render-claim.v1"}')
            with patch.object(listening, "ROOT", root), self.assertRaisesRegex(FileExistsError, "Unresolved legacy"):
                listening.claim_render(path, approval, root/approval["proposal"], root/"evaluation/pr-06a/run")
            self.assertFalse((root/"evaluation/pr-06a/render-claims").exists())


if __name__ == "__main__": unittest.main()
