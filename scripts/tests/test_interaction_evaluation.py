import json
from pathlib import Path
import sys
import tempfile
import unittest
import array
import subprocess
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from interaction_evaluation import trials, fixture, events_and_reference, scale_shift, summarize, identity, private, render, measure, observed_dwell, CHANNELS
from evaluation_contract import load_contract


class InteractionTests(unittest.TestCase):
    def test_complete_declared_coverage(self):
        matrix=list(trials())
        self.assertEqual(len(matrix),520)
        self.assertEqual({row[0] for row in matrix},{44100,48000})
        self.assertEqual({row[4] for row in matrix},{0,1})
        self.assertEqual({row[5] for row in matrix},{0,1})
        self.assertEqual({row[6] for row in matrix},{0,1,2,3})
        self.assertEqual({row[7] for row in matrix},{"upper","lower","mixed"})
        protocol=json.loads((Path(__file__).resolve().parents[2]/"docs/evidence/pr-05/protocol.json").read_text())
        self.assertEqual(protocol["full_matrix_cases"],len(matrix))
        self.assertEqual(len(identity()),64)

    def test_reference_is_synthetic_and_events_are_independent_of_measured_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=fixture(Path(temporary),48000)
            names={row["name"] for row in source["reference"]["regions"]}
            self.assertTrue({"breathy","z","s","sh","plosive","bend","ending","silence","bleed"}<=names)
            events,desired=events_and_reference(source,0,"mixed")
            self.assertTrue(all(a[0]<=b[0] for a,b in zip(events,events[1:])))
            first=next(row for row in source["reference"]["grid"] if row["voiced"])
            self.assertAlmostEqual(desired[0][0]["f0_hz"],first["f0_hz"]*.25)
            self.assertAlmostEqual(desired[2][0]["f0_hz"],first["f0_hz"]*4)
            self.assertFalse(all(row["stable"] for row in desired[0]))
            for mode in (1,2,3):
                events,_=events_and_reference(source,mode,"upper")
                self.assertFalse(any(event[2]=="P" for event in events))
                self.assertEqual({event[2] for event in events},{{1:"T",2:"H",3:"M"}[mode]})

    def test_scale_mapping_preserves_input_deviation(self):
        self.assertEqual(scale_shift(60,"upper"),[4,7,12])
        self.assertEqual(scale_shift(60.1,"upper"),[4,7,12])
        self.assertEqual(scale_shift(60,"mixed"),[-24,7,24])

    def test_observed_dwell_restarts_on_gaps_and_counts_window_callback_completion(self):
        observations=[{"source_sample":6000,"error_cents":0},{"source_sample":10800,"error_cents":0}]
        callbacks=[{"begin":0,"frames":20000}]
        self.assertIsNone(observed_dwell(observations,0,20000,0,4800,48000,callbacks))
        observations.append({"source_sample":13200,"error_cents":0})
        observed=observed_dwell(observations,0,20000,0,4800,48000,[{"begin":0,"frames":23000}])
        self.assertEqual(observed["observer_end"],13200+4800+4096)
        self.assertEqual(observed["available_sample"],23000)
        self.assertGreater(observed["request_to_observed_ms"],13200*1000/48000)

    def test_failed_and_unobservable_groups_are_not_summarized_as_passes(self):
        case={"case":"broken","engine":"signalsmith","window":512,"rate":48000,"reserve_profile":0,"treatment":1,"mode":0,"status":"rendered",
              "native":{"voices":[{"underflows":100}]},"measurements":{"gates":{"fixed_delivery":"fail","human_articulation":"pending"},
                "callback":{"occupancy_p999":.3},"voices":[{"voice":0,"pitch":{"groups":{"stable":{"frames":2,"within_25c_fraction":0}}}}]}}
        result=summarize([case])[0]
        self.assertEqual(result["failed_cases"]["fixed_delivery"],["broken"])
        self.assertEqual(result["failed_cases"]["stable_pitch"],["broken"])
        case["measurements"]["voices"][0]["pitch"]["groups"]["stable"]={"frames":0,"within_25c_fraction":None}
        self.assertTrue(summarize([case])[0]["unresolved_pitch_groups"])

    def test_private_missing_references_do_not_render_or_invent_truth(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve(); manifest=root/"corpus.json"
            manifest.write_text(json.dumps({"sources":[{"id":"required-expressive-c","audio":{"sha256":"a"*64},"annotations":[]}]}))
            with patch("interaction_evaluation.ROOT",root), patch("interaction_evaluation.select_sources",return_value=["required-expressive-c"]), \
                 patch("interaction_evaluation.provenance",return_value={}),patch("interaction_evaluation.verify_provenance"),patch("interaction_evaluation.render") as render:
                private(root/"unused-build",manifest)
            render.assert_not_called()
            report=json.loads(next((root/"evaluation/pr-05").glob("*/private-report.json")).read_text())
            self.assertEqual(report["sources"][0]["status"],"pending_human_references")

    def test_private_substitution_after_permission_validation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve(); manifest=root/"corpus.json"; audio=root/"source.wav"; audio.write_bytes(b"substituted bytes")
            manifest.write_text(json.dumps({"sources":[{"id":"development","audio":{"path":"source.wav","sha256":"a"*64},"annotations":[{},{}]}]}))
            with patch("interaction_evaluation.ROOT",root),patch("interaction_evaluation.select_sources",return_value=["development"]), \
                 patch("interaction_evaluation.provenance",return_value={}), self.assertRaisesRegex(ValueError,"source changed after selection"):
                private(root/"unused",manifest)

    def test_stale_or_sanitized_native_evidence_is_refused(self):
        for problem in ("stale","sanitized","unaudited"):
            with tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary); source=fixture(root,48000,True); case=root/"case"
                def native(command,**kwargs):
                    result={"compiled_source_identity":identity(),"profile":"Release","sanitizer":"","audit_available":True}
                    if problem=="stale": result["compiled_source_identity"]="0"*64
                    elif problem=="sanitized": result["sanitizer"]="address"
                    else: result["audit_available"]=False
                    (case/"render-native.json").write_text(json.dumps(result))
                    return subprocess.CompletedProcess(command,0,b"",b"")
                with patch("interaction_evaluation.subprocess.run",side_effect=native), self.subTest(problem=problem), self.assertRaisesRegex(ValueError,"Stale, sanitized or unaudited"):
                    render(root,case,source,(48000,"signalsmith",512,128,1,0,0,"upper",True))

    def test_lead_null_and_failed_delivery_cannot_become_research_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            case=Path(temporary); frames=12000; total=20000; delay=4800
            values=array.array("f",[.1]*frames)
            direct=list(values)+[0.]*(total-frames); aligned=[0.]*delay+list(values)+[0.]*(total-frames-delay)
            output={name:([0.]*total) for name in CHANNELS}; output["lead-direct"]=direct; output["lead-aligned"]=aligned
            output["sum-direct"]=direct; output["sum-aligned"]=aligned
            native={"sample_rate":48000,"latency_samples":delay,"source_frames":frames,"output_frames":total,
                    "voices":[{"underflows":1,"late_samples":0}]*3,"missing_metadata":0,"fifo_overflow":0,"bad_events":0,
                    "late_controls":0,"telemetry_dropped":0,"unrendered_finish_peak":0}
            source={"values":values,"reference":{"regions":[{"name":"synthetic","begin":0,"end":frames}]}}
            (case/"render-callbacks.csv").write_text(f"begin,frames,ns,allocations\n0,{total},100,0\n")
            (case/"render-telemetry.csv").write_text("kind,request_kind\n")
            meter={"groups":{"stable":{"frames":0,"within_25c_fraction":None}},"observations":[]}
            with patch("interaction_evaluation.reference_pitch_measurements",return_value=meter):
                result=measure(native,output,source,[[]]*3,case,load_contract())
                self.assertEqual(result["gates"]["lead_null"],"pass")
                self.assertEqual(result["gates"]["fixed_delivery"],"fail")
                output["lead-aligned"][5000]=.2
                self.assertEqual(measure(native,output,source,[[]]*3,case,load_contract())["gates"]["lead_null"],"fail")


if __name__=="__main__": unittest.main()
