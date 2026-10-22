import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("routing", ROOT / "scripts/routing.py")
routing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routing)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="voxide-routing-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def capture(self):
        context = {"tick": 10, "frame": 0, "epoch": 1, "block": 1, "frames": 64,
                   "source": "main", "held_keys": 0, "held_known": True, "midi_truncated_blocks": 0}
        return [
            {"kind": "header", "schema": "voxide.routing.v1", "instance": "test", "version": "0.1.0",
             "build": "routing-003", "dropped_before_capture": 0},
            dict(context, kind="midi", sequence=1, offset=7, prefix="903c50", midi_size=3),
            dict(context, kind="midi", sequence=2, offset=23, prefix="803c00", midi_size=3),
            dict(context, kind="audio", sequence=3, source_hash="1234", left_hash="1234", right_hash="1234",
                 main_peak=0.125, side_peak=0, left_peak=0.125, right_peak=0.125, non_finite_observations=0,
                 musical_midi_known=True, musical_key_presses=0, musical_physical_keys=0,
                 musical_sustained_keys=0, musical_sounding_pitches=0, bypassed=False),
            {"kind": "end", "last_sequence": 3, "dropped_records_total": 0, "dropped_during_capture": 0},
        ]

    def analyze(self, rows, **options):
        path = self.root / "capture.jsonl"
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        return routing.analyze(path, **options)

    def test_valid_capture_and_requirements(self):
        rows = self.capture()
        rows[0]["midi_state_schema"] = "voxide.midi-state.v1"
        result = self.analyze(rows, require_audio=True, require_midi=True, require_offsets=True,
                              require_notes=True, require_released=True)
        self.assertTrue(result["exact_selected_dry_stereo"])
        self.assertEqual(result["midi_records"], 2)
        self.assertEqual(result["status"], "valid_capture")
        self.assertEqual(result["note_pairs"], 1)

    def test_rejects_gaps_overflow_bad_offsets_and_unknown_notes(self):
        for change in ("gap", "overflow", "offset", "timestamp", "counter", "held", "nan", "bad_peak", "footer"):
            with self.subTest(change=change):
                rows = self.capture()
                if change == "gap": rows[2]["sequence"] = 5
                if change == "overflow": rows[-1]["dropped_during_capture"] = 1
                if change == "offset": rows[1]["offset"] = -1
                if change == "timestamp": rows[1]["epoch"] = 2
                if change == "counter": rows[1]["midi_truncated_blocks"] = 1
                if change == "held": rows[3]["held_known"] = False
                if change == "nan": rows[3]["non_finite_observations"] = 1
                if change == "bad_peak": rows[3]["left_peak"] = float("nan")
                if change == "footer": rows[-1]["last_sequence"] = 4
                with self.assertRaises(ValueError): self.analyze(rows)

    def test_old_recovered_overflow_is_not_a_new_capture_failure(self):
        rows = self.capture()
        for row in rows[1:-1]: row["midi_truncated_blocks"] = 2
        self.assertEqual(self.analyze(rows)["status"], "valid_capture")

    def test_silence_is_not_proof_of_required_audio(self):
        rows = self.capture()
        rows[3]["left_peak"] = 0
        with self.assertRaisesRegex(ValueError, "nonzero audio"):
            self.analyze(rows, require_audio=True)

    def test_missing_midi_is_not_proof_of_required_midi(self):
        rows = self.capture()
        rows = [rows[0], dict(rows[3], sequence=1), dict(rows[-1], last_sequence=1)]
        with self.assertRaisesRegex(ValueError, "Required MIDI"):
            self.analyze(rows, require_midi=True)

    def test_note_requirements_reject_non_notes_unmatched_and_held_notes(self):
        for prefix, size in (("b07b00", 3), ("f80000", 3), ("f00000", 4096), ("903d50", 3)):
            with self.subTest(prefix=prefix):
                rows = self.capture()
                rows[1].update(prefix=prefix, midi_size=size)
                with self.assertRaisesRegex(ValueError, "matching MIDI note-on/off"):
                    self.analyze(rows, require_notes=True)
        rows = self.capture()
        rows[2]["prefix"] = "903c00"  # Zero-velocity note-on is a release.
        self.assertEqual(self.analyze(rows, require_notes=True)["note_pairs"], 1)
        rows[3]["held_keys"] = 1
        rows[0]["midi_state_schema"] = "voxide.midi-state.v1"
        rows[3].update(musical_key_presses=1, musical_physical_keys=1, musical_sounding_pitches=1)
        with self.assertRaisesRegex(ValueError, "Held keys remain"):
            self.analyze(rows, require_released=True)

    def test_release_uses_repeat_and_sustain_counts_not_legacy_bitset(self):
        for presses, physical, sustained in ((1, 1, 0), (0, 0, 1)):
            rows = self.capture()
            rows[0]["midi_state_schema"] = "voxide.midi-state.v1"
            rows[3].update(held_keys=0, musical_key_presses=presses, musical_physical_keys=physical,
                           musical_sustained_keys=sustained, musical_sounding_pitches=1)
            with self.assertRaisesRegex(ValueError, "Held keys remain"):
                self.analyze(rows, require_released=True)

    def test_release_requires_known_unbypassed_authoritative_counts(self):
        with self.assertRaisesRegex(ValueError, "authoritative"):
            self.analyze(self.capture(), require_released=True)
        self.assertEqual(self.analyze(self.capture())["status"], "valid_capture")
        for change in ("unknown", "bypassed", "missing", "inconsistent"):
            rows = self.capture()
            rows[0]["midi_state_schema"] = "voxide.midi-state.v1"
            if change == "unknown": rows[3]["musical_midi_known"] = False
            if change == "bypassed": rows[3]["bypassed"] = True
            if change == "missing": del rows[3]["musical_key_presses"]
            if change == "inconsistent": rows[3]["musical_physical_keys"] = 1
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.analyze(rows, require_released=True)

    def test_note_offsets_cannot_be_satisfied_by_a_controller(self):
        rows = self.capture()
        rows[1]["offset"] = rows[2]["offset"] = 0
        rows.insert(3, dict(rows[2], prefix="b07b00", offset=23, sequence=3))
        rows[-2]["sequence"] = rows[-1]["last_sequence"] = 4
        with self.assertRaisesRegex(ValueError, "within-block MIDI offset"):
            self.analyze(rows, require_notes=True, require_offsets=True)

    def test_complete_capture_reports_discarded_tail(self):
        rows = self.capture()
        rows[-1]["incomplete_tail_records"] = 1
        result = self.analyze(rows)
        self.assertEqual(result["status"], "valid_capture")
        self.assertEqual(result["incomplete_tail_records"], 1)

    def test_route_mismatch_and_aborted_capture(self):
        rows = self.capture()
        rows[3]["right_hash"] = "different"
        self.assertFalse(self.analyze(rows)["exact_selected_dry_stereo"])
        with self.assertRaises(ValueError): self.analyze(rows[:-1])

    def test_fixture_generation_is_repeatable_and_refuses_overwrite(self):
        first = routing.prepare(self.root / "a")
        second = routing.prepare(self.root / "b")
        self.assertEqual(first, second)
        with wave.open(str(self.root / "a/routing-probe.wav")) as audio:
            self.assertEqual((audio.getnchannels(), audio.getframerate(), audio.getnframes()), (1, 48000, 384000))
        self.assertEqual((self.root / "a/routing-probe.mid").read_bytes()[:4], b"MThd")
        with self.assertRaises(FileExistsError): routing.prepare(self.root / "a")


if __name__ == "__main__":
    unittest.main()
