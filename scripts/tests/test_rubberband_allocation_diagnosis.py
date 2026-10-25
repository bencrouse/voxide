import array
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rubberband_allocation_diagnosis as diagnosis
from evaluation_common import write_json


class RubberBandAllocationDiagnosisTests(unittest.TestCase):
    def test_exact_bounded_matrix_and_prescribed_control_endpoints(self):
        self.assertEqual(len(diagnosis.cases()), 8)
        self.assertEqual(len(set(diagnosis.cases())), 8)
        for rate in (44100, 48000):
            for mode in ("static", "changing"):
                controls = list(diagnosis.expected_controls(rate, mode))
                self.assertEqual(len(controls), 3*((rate*18//5+127)//128))
                self.assertEqual(controls[-1][0]+controls[-1][1], rate*18//5)
                self.assertTrue(all(abs(row[3]) <= 12 for row in controls))
                self.assertIn(-12, [row[3] for row in controls])
                self.assertIn(12, [row[3] for row in controls])

    def pair(self, root):
        for name in ("fresh", "silent"):
            p = root/name; p.mkdir()
            write_json(p/"native.json", {"identity": "test", "rate": 48000, "workload": "changing", "frames": 100,
                "start_pad": 100, "start_trim": 100, "input_hash": "same", "control_hash": "same",
                "callback_allocations": 0, "finish_allocations": 0})
            (p/"source.f32").write_bytes(b"same-source")
            (p/"controls.csv").write_text("same-controls")
            for voice in range(3): (p/f"voice{voice}.f32").write_bytes(array.array("f", [.01]*100).tobytes())
        return root/"fresh", root/"silent"

    def test_comparison_keeps_allocations_finish_and_every_output_failure(self):
        for fault in ("none", "difference", "length", "nonfinite", "callback", "finish"):
            with tempfile.TemporaryDirectory() as temp:
                a, b = self.pair(Path(temp))
                if fault in ("callback", "finish"):
                    native = diagnosis.load_json(b/"native.json"); native[fault+"_allocations"] = 1
                    diagnosis.save_owned_json(b/"native.json", native)
                elif fault != "none":
                    samples = [.01]*100
                    if fault == "difference": samples[-1] = .02
                    elif fault == "length": samples.pop()
                    elif fault == "nonfinite": samples[-1] = float("nan")
                    (b/"voice2.f32").write_bytes(array.array("f", samples).tobytes())
                if fault == "nonfinite":
                    with self.assertRaisesRegex(ValueError, "Invalid float32"): diagnosis.compare(a, b)
                else:
                    self.assertEqual(diagnosis.compare(a, b)["pass"], fault == "none", fault)

    def test_control_or_source_changes_cannot_be_called_neutral_preparation(self):
        for file in ("controls.csv", "source.f32"):
            with tempfile.TemporaryDirectory() as temp:
                a, b = self.pair(Path(temp)); (b/file).write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "bytes differ"): diagnosis.compare(a, b)

    def test_consumed_claim_blocks_before_binary_attestation_or_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); claims = root/"build/rubberband-allocation-diagnosis/claims"; claims.mkdir(parents=True)
            claim = claims/"test.json"; claim.write_text("consumed")
            with patch.object(diagnosis, "ROOT", root), patch.object(diagnosis, "load_json", return_value={"id": "test", "native_capture_cap": 8}), \
                 patch.object(diagnosis.subprocess, "run") as run, patch.object(diagnosis.subprocess, "check_output") as attest, \
                 self.assertRaises(FileExistsError): diagnosis.run()
            run.assert_not_called(); attest.assert_not_called()
            self.assertEqual(claim.read_text(), "consumed")

    def test_oversized_matrix_rejected_before_claim_or_execution(self):
        with patch.object(diagnosis, "cases", return_value=diagnosis.cases()+[(48000, "extra", "silent")]), \
             patch.object(diagnosis.subprocess, "run") as run, self.assertRaisesRegex(ValueError, "Capture cap"):
            diagnosis.run()
        run.assert_not_called()

    def test_failed_attestation_retains_consumed_claim_and_failure_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); protocol = root/"protocol.json"
            write_json(protocol, {"id": "test", "native_capture_cap": 8})
            with patch.object(diagnosis, "ROOT", root), patch.object(diagnosis, "PROTOCOL", protocol), \
                 patch.object(diagnosis, "BUILD", root/"missing"), patch.object(diagnosis, "compiled_identity", return_value="test"), \
                 patch.object(diagnosis, "source_fingerprint", return_value={}), \
                 patch.object(diagnosis.subprocess, "check_output", side_effect=FileNotFoundError("missing binary")), \
                 patch.object(diagnosis.subprocess, "run") as native, self.assertRaises(FileNotFoundError): diagnosis.run()
            native.assert_not_called()
            claim = diagnosis.load_json(root/"build/rubberband-allocation-diagnosis/claims/test.json")
            self.assertEqual(claim["status"], "consumed")
            report = diagnosis.load_json(root/claim["run"]/"report.json")
            self.assertEqual(report["native_executions"], 0)
            self.assertNotEqual(report["status"], "running")
            self.assertIn("missing binary", report["error"])

    def test_atomic_updates_preserve_original_if_staging_file_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"report.json"; path.write_text("original")
            path.with_suffix(".json.next").write_text("unfamiliar")
            with self.assertRaises(FileExistsError): diagnosis.save_owned_json(path, {"new": True})
            self.assertEqual(path.read_text(), "original")
