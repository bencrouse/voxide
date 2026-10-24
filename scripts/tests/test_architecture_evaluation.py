import sys
import unittest
import json
import subprocess
import tempfile
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from architecture_evaluation import calibrate,period_pitch,positive_crossings,observed_response,tone,decision,native,identity


class ArchitectureInstruments(unittest.TestCase):
    def test_full_range_and_late_response_controls(self):
        result=calibrate()
        self.assertEqual(result["status"],"pass")
        self.assertEqual(len(result["steady"]),10)
        self.assertTrue(all(r["correct_side_of_50ms_ceiling"] for r in result["response"]))

    def test_interpolated_crossings_do_not_use_expected_pitch(self):
        self.assertEqual(positive_crossings([-1,1,-1,3]),[.5,2.25])
        observed=period_pitch(tone(48000,311),48000)
        self.assertAlmostEqual(observed["hz"],311,places=3)

    def test_silence_and_two_tones_are_not_false_confirmations(self):
        self.assertIsNone(period_pitch([0.]*8192,48000)["hz"])
        mix=[x+y for x,y in zip(tone(48000,220),tone(48000,311))]
        self.assertIsNone(period_pitch(mix,48000)["hz"])

    def test_insufficient_low_frequency_support_is_not_a_pass(self):
        self.assertIsNone(period_pitch(tone(48000,20.6,.05),48000)["hz"])

    def test_unavailable_observer_end_is_not_backdated(self):
        audio=tone(48000,330,.1)
        self.assertEqual(observed_response(audio,48000,330,0,[])["status"],"unresolved")
        result=observed_response(audio,48000,330,0,[{"first":0,"count":len(audio),"wall":len(audio)+500}])
        self.assertEqual(result["available_sample"],len(audio)+500)
        self.assertGreaterEqual(result["completed_output_sample"],round(48000*.020))

    def test_later_event_cannot_satisfy_an_earlier_request(self):
        audio=list(tone(48000,220,.1))+list(tone(48000,330,.1))
        packets=[{"first":0,"count":len(audio),"wall":len(audio)}]
        self.assertEqual(observed_response(audio,48000,330,0,packets,stop=4800)["status"],"unresolved")

    def test_decision_is_derived_from_observed_blockers_not_predetermined(self):
        row={"case":"steady-control","backend":"builtin","window":256,"status":"rendered"}
        self.assertEqual(decision([row])["recommendation"],"pause_for_remaining_qualification")
        row["steady"]=[{"period_error_cents":200,"nacf_error_cents":200}]
        self.assertEqual(decision([row])["recommendation"],"no_go_for_product_integration_under_tested_scope")

    def test_nonfinite_native_stems_never_get_quality_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); case=root/"invalid"
            def execute(command,**kwargs):
                (case/"render.json").write_text(json.dumps({"identity":identity(),"build":"Release","sanitizer":"","audit_available":True,"voices":[{"nonfinite":1}]}))
                return subprocess.CompletedProcess(command,0,b"",b"")
            with patch("architecture_evaluation.subprocess.run",side_effect=execute):
                result=native(root,root,"invalid","accelerate",48000,256,32,[0.]*100,[(0,220,(0,0,0))])
            self.assertEqual(result["status"],"native_nonfinite")
            self.assertNotIn("steady",result)


if __name__=="__main__": unittest.main()
