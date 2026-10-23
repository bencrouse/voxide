import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine_metrics import (available_at, callback_metrics, validate_timeline, write_float_wav,
                            pitch_measurements, impulse_delay, human_reference_pitch)
from engine_evaluation import harmonics, trials, summarize_configurations
from evaluation_contract import load_contract


class EngineMetricsTests(unittest.TestCase):
    def test_float_wav_keeps_over_unity_samples_without_normalizing(self):
        with tempfile.TemporaryDirectory(prefix="voxide-float-wav-") as temporary:
            path = Path(temporary) / "render.wav"
            payload = struct.pack("<fff", -1.25, 0, 1.5)
            write_float_wav(path, 48000, payload)
            self.assertEqual(path.read_bytes()[56:], payload)
            self.assertEqual(path.read_bytes()[36:40],b"fact")
            self.assertEqual(struct.unpack_from("<H", path.read_bytes(), 20)[0], 3)
            with self.assertRaises(FileExistsError): write_float_wav(path, 48000, payload)

    def test_callback_availability_is_not_backdated_to_quantum(self):
        chunks = [{"output_begin":0,"count":128,"available_source_samples":128,"callback_available_source_samples":257}]
        self.assertEqual(available_at(chunks, 127), 257)
        self.assertEqual(available_at(chunks, 127, callback=False), 128)
        self.assertIsNone(available_at(chunks, 128))

    def test_fifo_coverage_and_control_timebase_fail_closed(self):
        native = {"voices":1,"source_frames":256,"zero_tail_supplied":0,
                  "instances":[{"output_frames":256,"quantum":128,"control_lag":0}]}
        chunks = [{"voice":"0","output_begin":str(start),"count":"128","available_source_samples":str(start+128),
                   "callback_available_source_samples":str(start+128)} for start in (0,128)]
        controls = [{"voice":"0","requested_source_sample":"0","applied_input_begin":"0","processing_source_sample":"0","ratio":"1","source_hz":"220"}]
        expected = [{"sample":0,"ratios":[1,1,1],"source_hz":220}]
        self.assertEqual(len(validate_timeline(native, chunks, controls, expected)[0]), 2)
        for key, value in (("output_begin","129"), ("count","127"), ("callback_available_source_samples","127")):
            broken = [dict(row) for row in chunks]; broken[1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): validate_timeline(native, broken, controls, expected)
        early = [dict(controls[0], requested_source_sample="128", processing_source_sample="127", applied_input_begin="127")]
        with self.assertRaises(ValueError): validate_timeline(native, chunks, early, [dict(expected[0], sample=128)])

    def test_callback_cost_and_allocation_failures_are_not_hidden(self):
        rows = [{"begin":"0","frames":"128","ns":"3000000","allocations":"2"}]
        metric = callback_metrics(rows, 48000, True, {"callback_occupancy_p999_max_exclusive":.5})
        self.assertEqual(metric["allocation_calls"], 2)
        self.assertEqual(metric["overdue_callbacks"], 1)
        self.assertFalse(metric["occupancy_target_met_on_this_run_only"])
        self.assertIsNone(callback_metrics(rows,48000,False,{"callback_occupancy_p999_max_exclusive":.5})["allocation_calls"])
        with self.assertRaisesRegex(ValueError,"tail coverage"):
            callback_metrics(rows,48000,True,{"callback_occupancy_p999_max_exclusive":.5},expected_frames=256)

    def test_pitch_missing_estimates_stay_failures_and_wrong_octave_is_detected(self):
        perfect = harmonics(48000, 1, 220)
        self.assertEqual(pitch_measurements(perfect,0,len(perfect),220,48000)["within_25c_fraction"], 1)
        self.assertEqual(pitch_measurements(perfect,0,len(perfect),440,48000)["within_25c_fraction"], 0)
        silent = pitch_measurements([0.0]*48000,0,48000,220,48000)
        self.assertEqual(silent["missing_estimates"], 3)
        self.assertEqual(silent["within_25c_fraction"], 0)

    def test_high_output_register_does_not_fall_into_integer_lag_octave_trap(self):
        target = 1046.5022612023945 * 4
        perfect = harmonics(48000,1,target)
        metric = pitch_measurements(perfect,0,len(perfect),target,48000)
        self.assertEqual(metric["within_25c_fraction"],1)
        self.assertTrue(all(abs(row["error_cents"]) < 5 for row in metric["observations"]))

    def test_truncated_output_cannot_escape_the_pitch_denominator(self):
        with patch("engine_metrics.estimate_output_pitch",return_value={"f0_hz":220,"confidence":1}):
            metric = pitch_measurements([.1]*28800,0,48000,220,48000)
        self.assertEqual(metric["eligible_frames"],3)
        self.assertEqual(metric["missing_estimates"],1)
        self.assertAlmostEqual(metric["within_25c_fraction"],2/3)
        self.assertEqual(metric["observations"][-1]["reason"],"missing_output_support")

    def test_summary_retains_stable_grid_failures_and_unresolved_observers(self):
        case = {"case":"test-case","engine":"signalsmith","window":512,"rate":48000,"voices":1,"render_status":"rendered",
                "measurements":{"callback":{"ns_max":1,"occupancy_p999":.01,"allocation_calls":0,"overdue_callbacks":0,
                                             "occupancy_target_met_on_this_run_only":True},
                    "reset":{"reset_vs_fresh_max_abs":0,"reset_vs_fresh_rms":0,"reset_silence_peak":0},
                    "voices":[{"voice":0,"source_grid_pitch":{"groups":{
                        "stable":{"frames":3,"within_25c_fraction":0},
                        "expressive_unstable":{"frames":2,"within_25c_fraction":0}},"excluded":{"uncertain":1}},
                        "ratio_settling":{"events":[{"requested_source_sample":9600,"target_hz":440,"settled":None},
                            {"requested_source_sample":19200,"target_hz":220,"settled":{"available_source_sample":24000,"request_to_observed_dwell_ms":100}}]},
                        "envelope_delay":{"status":"unobservable","reason":"step contrast lost"}}]}}
        summary = summarize_configurations([case],load_contract())[0]
        self.assertEqual(summary["pitch_failed_cases"],["test-case"])
        self.assertEqual(summary["source_grid_pitch_failed_cases"],["test-case"])
        self.assertEqual(len(summary["ratio_settling_observations"]),2)
        self.assertEqual(summary["unresolved_ratio_observations"][0]["requested_source_sample"],9600)
        self.assertEqual(summary["unresolved_envelope_observations"][0]["reason"],"step contrast lost")
        grid = case["measurements"]["voices"][0]["source_grid_pitch"]
        grid["groups"]["stable"] = {"frames":0,"within_25c_fraction":None}
        summary = summarize_configurations([case],load_contract())[0]
        self.assertEqual(summary["pitch_failed_cases"],[])
        self.assertEqual(summary["source_grid_pitch_observations"][0]["expressive_unstable"]["frames"],2)

    def test_full_matrix_covers_all_configurations_rates_shifts_and_voice_counts(self):
        matrix = list(trials())
        self.assertEqual(len(matrix), 930)
        self.assertEqual({row[0] for row in matrix}, {44100,48000})
        self.assertEqual({row[5] for row in matrix}, {1,3})
        self.assertEqual({row[6][0] for row in matrix if row[4]=='tone-low'}, {-24,-12,-7,-3,0,3,7,12,24})
        self.assertLess(len(list(trials(True))), len(matrix))
        protocol = json.loads((Path(__file__).resolve().parents[2]/"docs/evidence/pr-04/protocol.json").read_text())
        self.assertEqual(protocol["full_matrix_cases"],len(matrix))
        self.assertEqual(protocol["signalsmith_options"]["seed"],0x564f5849)

    def test_human_reference_keeps_unstable_expression_and_uncertainty_separate(self):
        audio = harmonics(48000,1,220)
        grid = [{"sample":24000,"voiced":True,"stable":True,"uncertain":False,"f0_hz":220},
                {"sample":25000,"voiced":True,"stable":False,"uncertain":False,"f0_hz":440},
                {"sample":26000,"voiced":True,"stable":True,"uncertain":True,"f0_hz":220}]
        metric = human_reference_pitch(audio,grid,1,0,len(audio),48000)
        self.assertEqual(metric["groups"]["stable"]["within_25c_fraction"],1)
        self.assertEqual(metric["groups"]["expressive_unstable"]["within_25c_fraction"],0)
        self.assertEqual(metric["excluded"]["uncertain"],1)


if __name__ == "__main__": unittest.main()
