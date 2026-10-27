from pathlib import Path
import copy
import json
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import studio_session as session


class StudioSessionTests(unittest.TestCase):
    def metadata(self):
        header={"kind":"header","schema":"voxide.pr09-session.v1","version":"0.4.0","revision":"test-fixture","profile":"Release","instance":"fixture",
            "module_path":"/not-accessed/voxide","module_file_sha256":"a"*64,"os":"fixture","cpu":"fixture","unix_ms":1000,"tick_hz":1000000000,
            "scope":"processor render body only; excludes AU wrapper, telemetry collection and file IO","pcm_recorded":False,"allocation_audit_available":False}
        rows=[]
        for i in range(6):rows.append({"kind":"callback","sequence":i+1,"tick":1000000000+i*2666667,"elapsed_ticks":1000,"frames":128,"rate":48000,
            "status":1,"active":7,"enabled":7,"root":i%2,"scale":i%2,"epoch":1,"offline":False,"bypassed":False,"transport_known":True,"playing":True,"peak":.1,"nonfinite":0})
        return [header,*rows,{"kind":"end","callbacks":6,"last_sequence":6,"dropped":0,"unix_ms":2000}]

    def parse(self,rows,expected="a"*64):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"fixture.jsonl";path.write_text("".join(json.dumps(r)+"\n" for r in rows));return session.parse_log(path,expected)

    def test_short_metadata_cannot_pass_qualification(self):
        report=self.parse(self.metadata())
        self.assertEqual(report["qualification"],"incomplete_studio_qualification")
        self.assertFalse(report["gates"]["30_minute_exposure"]);self.assertIn("allocation",report["unmeasured"][0])
        self.assertEqual(report["callbacks"],6);self.assertEqual(report["three_active_callbacks"],6)

    def test_mix_version_metadata_does_not_inherit_qualification(self):
        rows=self.metadata();rows[0]["version"]="0.5.0";report=self.parse(rows)
        self.assertEqual(report["qualification"],"incomplete_studio_qualification")
        self.assertFalse(report["gates"]["30_minute_exposure"])

    def test_long_wall_clock_does_not_invent_rendered_soak(self):
        rows=self.metadata();rows[-1]["unix_ms"]+=1800000;rows[-2]["tick"]+=1800000000000
        report=self.parse(rows);self.assertFalse(report["gates"]["30_minute_exposure"])

    def test_zero_frame_control_callbacks_are_retained_without_audio_deadlines(self):
        rows=self.metadata();rows[1]["frames"]=0
        report=self.parse(rows);self.assertEqual(report["callbacks"],6);self.assertEqual(report["zero_frame_callbacks"],1)
        for row in rows[1:-1]:row["frames"]=0
        with self.assertRaises(ValueError):self.parse(rows)

    def test_duplicate_fields_and_partial_final_line_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"fixture.jsonl";text="".join(json.dumps(r)+"\n" for r in self.metadata())
            for malformed in (text[:-1],text.replace('"frames": 128','"frames": 128, "frames": 128')):
                path.write_text(malformed)
                with self.assertRaises(ValueError):session.parse_log(path,"a"*64)

    def test_stopped_or_unknown_transport_cannot_claim_playback(self):
        for known,playing in ((False,True),(True,False)):
            rows=self.metadata()
            for row in rows[1:-1]:row.update(transport_known=known,playing=playing)
            report=self.parse(rows);self.assertEqual(report["reported_playing_seconds"],0)
            self.assertFalse(report["gates"]["30_minute_exposure"])

    def test_no_missing_aborted_repeated_or_dropped_records(self):
        cases=[]
        for change in ("footer","aborted","sequence","drop","count","unknown","clock"):
            rows=self.metadata()
            if change=="footer":rows.pop()
            if change=="aborted":rows[-1]={"kind":"aborted","reason":"fixture"}
            if change=="sequence":rows[2]["sequence"]=1
            if change=="drop":rows[-1]["dropped"]=1
            if change=="count":rows[-1]["callbacks"]=5
            if change=="unknown":rows[1]["pcm"]=[.1,.2]
            if change=="clock":rows[2]["tick"]=1
            cases.append((change,rows))
        for change,rows in cases:
            with self.subTest(change=change),self.assertRaises(ValueError):self.parse(rows)

    def test_wrong_module_debug_nonfinite_and_boolean_metadata_refused(self):
        for change in ("binary","debug","nan","bool","scope"):
            rows=self.metadata()
            if change=="binary":rows[0]["module_file_sha256"]="b"*64
            if change=="debug":rows[0]["profile"]="Debug"
            if change=="nan":rows[1]["peak"]=float("nan")
            if change=="bool":rows[1]["frames"]=True
            if change=="scope":rows[0]["allocation_audit_available"]=True
            with self.subTest(change=change),self.assertRaises(ValueError):self.parse(rows)

    def test_all_header_text_fields_reject_nonproducer_values(self):
        for key in session.HEADER_TEXT_LIMITS:
            for value in ({"pcm":[.1,.2]},["fixture"],True,42,None):
                rows=self.metadata();rows[0][key]=value
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.parse(rows)
        for key,value in (("revision",""),("instance",""),("module_path","relative/voxide"),("cpu","a"*1025),("os","bad\0text")):
            rows=self.metadata();rows[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.parse(rows)
        rows=self.metadata();rows[0].update(cpu="",os="")
        self.assertEqual(self.parse(rows)["callbacks"],6) # Native system descriptions may be unavailable.

    def test_numeric_overflow_in_header_is_rejected_before_schema_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"fixture.jsonl";text="".join(json.dumps(r)+"\n" for r in self.metadata())
            for key in ("cpu","revision","module_path","tick_hz"):
                rows=self.metadata();rows[0][key]="overflow-marker"
                malformed="".join(json.dumps(r)+"\n" for r in rows).replace('"overflow-marker"','1e999')
                path.write_text(malformed)
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,"Nonfinite JSON number"):
                    session.parse_log(path,"a"*64)

    def test_malformed_header_retains_failed_analysis_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();directory=root/"evaluation/pr-09";directory.mkdir(parents=True)
            path=directory/"malformed.jsonl";rows=self.metadata();rows[0]["module_path"]={"pcm":[.1,.2]}
            path.write_text("".join(json.dumps(r)+"\n" for r in rows));output=directory/"report"
            with patch.object(session,"ROOT",root),self.assertRaisesRegex(ValueError,"header text"):
                session.analyse(path,"a"*64,allow_session_log=True,output=output)
            self.assertEqual(session.load_json(output/"report.json")["status"],"fail")

    def test_health_peak_overdue_and_offline_fail_without_dropping_observations(self):
        rows=self.metadata();rows[1].update(status=2,peak=1.1,offline=True,nonfinite=1,elapsed_ticks=3000000)
        rows[2]["tick"]+=1000000
        report=self.parse(rows)
        for key in ("healthy","headroom","finite","zero_body_overdue","realtime_only"):self.assertFalse(report["gates"][key],key)
        self.assertEqual(report["callbacks"],6);self.assertEqual(report["overdue"],1)

    def test_consent_precedes_any_session_path_access(self):
        with patch.object(session.au,"no_symlinks") as access,self.assertRaisesRegex(ValueError,"allow-session-log"):
            session.analyse(Path("not-accessed"),"a"*64)
        access.assert_not_called()

    def test_failed_private_analysis_keeps_negative_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();directory=root/"evaluation/pr-09";directory.mkdir(parents=True)
            path=directory/"aborted.jsonl";path.write_text('{"kind":"aborted"}\n');output=directory/"report"
            with patch.object(session,"ROOT",root),self.assertRaises(ValueError):
                session.analyse(path,"a"*64,allow_session_log=True,output=output)
            report=session.load_json(output/"report.json")
            self.assertEqual(report["status"],"fail");self.assertEqual(report["qualification"],"incomplete_studio_qualification");self.assertFalse(report["audio_read"])

    def test_private_analysis_refuses_symlinks_and_outside_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();directory=root/"evaluation/pr-09";directory.mkdir(parents=True)
            target=root/"outside.jsonl";target.write_text("not read");link=directory/"linked.jsonl";link.symlink_to(target)
            with patch.object(session,"ROOT",root):
                for path in (target,link):
                    with self.subTest(path=str(path)),self.assertRaises(ValueError):session.analyse(path,"a"*64,allow_session_log=True)

    def screen_rows(self):
        rows=[]
        for rate in (44100,48000):
            for mode,partitions in enumerate(([128],[512],[32,128,257,512,1024])):
                at=i=0
                while at<rate*5:
                    n=min(partitions[i%len(partitions)],rate*5-at)
                    change=at//rate;even=change>0 and change%2==0
                    row={"case":f"{rate}-{mode}","rate":rate,"begin":at,"frames":n,"ns":1000,"allocations":0,
                        "api_error":0,"nonfinite":0,"peak":.1,"scheduler_lag_ns":1000,
                        "requested_root":(5+change)%12,"requested_scale":change%3 if change else 1,"degree1":-2 if even else 2,"degree2":3 if even else 4,"degree3":5 if even else 6}
                    for second in range(5):
                        overlap=max(0,min(at+n,(second+1)*rate)-max(at,second*rate))
                        row[f"wet{second}"]=row[f"audible{second}"]=overlap
                    rows.append(row);at+=n;i+=1
        return rows

    def test_screen_matrix_and_raw_failure_accounting(self):
        rows=self.screen_rows();report=session.analyse_screen(rows)
        self.assertEqual(len(report),6);self.assertTrue(all(c["status"]=="pass_this_screen_only" for c in report))
        rows[0].update(allocations=1,ns=10000000,peak=1.1,api_error=-1,nonfinite=1)
        rows[0]["audible0"]-=1;rows[0]["wet0"]-=1
        failed=next(c for c in session.analyse_screen(rows) if c["case"]=="44100-0")
        self.assertEqual(failed["status"],"failed_screen");self.assertEqual(failed["timing"]["allocation_calls"],1)
        self.assertEqual(failed["timing"]["overdue_callbacks"],1)

    def test_truncated_partition_changed_or_dry_screen_refused(self):
        rows=self.screen_rows()
        with self.assertRaises(ValueError):session.analyse_screen(rows[:-1])
        bad=copy.deepcopy(rows);bad[0]["frames"]=64
        with self.assertRaises(ValueError):session.analyse_screen(bad)
        for row in rows:
            for second in range(5):row[f"wet{second}"]=0
        self.assertTrue(all(c["status"]=="failed_screen" for c in session.analyse_screen(rows)))

    def test_silent_screen_cannot_pass_activity_gates(self):
        rows=self.screen_rows()
        for row in rows:
            row["peak"]=0
            for second in range(5):row[f"wet{second}"]=row[f"audible{second}"]=0
        for case in session.analyse_screen(rows):
            self.assertEqual(case["status"],"failed_screen")
            self.assertFalse(case["gates"]["audible_each_body_second"])
            self.assertFalse(case["gates"]["aggregate_wet_each_body_second"])

    def test_activity_peak_respects_native_threshold_and_serialization_rounding(self):
        rows=self.screen_rows()
        for row in rows:row["peak"]=.000001
        with self.assertRaisesRegex(ValueError,"peak threshold"):session.analyse_screen(rows)
        # Native output just above 1e-4 can serialize as exactly 0.000100.
        for row in rows:row["peak"]=.0001
        self.assertTrue(all(c["status"]=="pass_this_screen_only" for c in session.analyse_screen(rows)))

    def test_boundary_resumption_does_not_cover_previous_dry_second(self):
        rows=self.screen_rows()
        for row in rows:
            if row["case"]=="44100-2":row["wet1"]=0
        crossing=next(r for r in rows if r["case"]=="44100-2" and r["begin"]==88045)
        self.assertEqual((crossing["frames"],crossing["wet1"],crossing["wet2"]),(257,0,102))
        case=next(c for c in session.analyse_screen(rows) if c["case"]=="44100-2")
        self.assertEqual(case["wet_samples_by_second"][1],0)
        self.assertGreater(case["wet_samples_by_second"][2],0)
        self.assertFalse(case["gates"]["aggregate_wet_each_body_second"])

    def test_out_of_bucket_counts_and_old_aggregate_format_are_rejected(self):
        rows=self.screen_rows();rows[0]["wet4"]=1
        with self.assertRaisesRegex(ValueError,"per-second"):session.analyse_screen(rows)
        rows=self.screen_rows();rows[0]["wet_samples"]=rows[0]["frames"]
        for key in list(rows[0]):
            if key.startswith("wet") and key!="wet_samples" or key.startswith("audible"):rows[0].pop(key)
        with self.assertRaisesRegex(ValueError,"v2 required"):session.analyse_screen(rows)

    def test_screen_debug_refused_before_any_native_execution(self):
        with patch.object(session.au,"no_symlinks",side_effect=lambda p:p),patch.object(session,"native_binary",return_value=(Path("fixture"),"Debug")), \
             patch.object(session.subprocess,"run") as run,self.assertRaisesRegex(ValueError,"Release"):
            session.screen(Path("not-accessed"))
        run.assert_not_called()

    def test_kit_is_only_pending_metadata_and_instructions(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();(root/"docs").mkdir();(root/"docs/PR09_STUDIO_SESSION.md").write_text("Fixture instructions")
            with patch.object(session,"ROOT",root):path=session.kit()
            report=session.load_json(path/"status.json")
            self.assertEqual(report["qualification"],"incomplete_studio_qualification");self.assertFalse(report["audio_access"])
            self.assertEqual({p.name for p in path.iterdir()},{"CHECKLIST.md","status.json"})
