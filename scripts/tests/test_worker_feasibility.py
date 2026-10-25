import array
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import worker_feasibility as worker
from evaluation_common import write_json
from studio_test_support import synthetic_timeline


class WorkerFeasibilityTests(unittest.TestCase):
    def fixture(self, mode="offline"):
        rate=48000; total=rate*28//5; analysis=1045; fed=(total-analysis)//128*128
        source=array.array("f", [.01]*(rate*5)+[0.]*(rate*3//5))
        delay=rate//10; aligned=array.array("f", [0.]*delay)+source[:total-delay]
        audio=[source, aligned]+[array.array("f", [.001]*total) for _ in range(6)]
        audio += [array.array("f", (x+.001 for x in lead)) for lead in (source, aligned)]
        metadata, timeline=synthetic_timeline(rate,total,engine="rubberband")
        for at in (rate*8//5,rate*14//5,rate*4):
            template=dict(timeline[0]); template.update(kind="2",wall=str(at),requested=str(at),available=str(at),request_kind="3")
            timeline.append(template)
        timeline.sort(key=lambda r:int(r["wall"]))
        input_hash=worker.fnv(w[0] for w in struct.iter_unpack("I",source[:fed].tobytes()))
        control_words=[]
        for r in timeline:
            if r["kind"]=="0" and r["voice"]=="0":
                for value in (float(r["applied_shift"]),float(r["hz"]) if int(r["voiced"]) else 0.):
                    control_words.append(struct.unpack("Q",struct.pack("d",value))[0])
        voices=[dict(v,input_hash=input_hash,control_hash=worker.fnv(control_words)) for v in metadata["voices"]]
        metrics=[{"failed":False,"audit_detected":True,"commands":fed//128+10,"native_frames":fed+1280,"body_allocations":1} for _ in range(3)]
        native={"identity":"test","rate":rate,"block":128,"mode":mode,"profile":"Release","sanitizer":"","audit_available":True,
                "complete":True,"frames":total,"error":"","latency_samples":delay,"analysis_samples":analysis,
                "voices":voices,"workers":metrics,"failed_closed":False,"first_failure":total,"finish_peak":0,
                **dict.fromkeys(("bad_events","late_controls","telemetry_dropped","invalid_input","missing_metadata","fifo_overflow"),0)}
        callbacks=[{"begin":str(i),"frames":str(min(128,total-i)),"ns":"1","allocations":"0","late_ns":"0",
                    "finish_ns":str((i+min(128,total-i))*10**9//rate-1),"deadline_ns":str((i+min(128,total-i))*10**9//rate)}
                   for i in range(0,total,128)]
        return native,source,audio,timeline,callbacks

    def validate_fixture(self, fixture):
        native,source,audio,timeline,callbacks=fixture
        def floats(path):
            return (source,b"") if path.name=="source.f32" else (audio[int(path.stem.removeprefix("channel"))],b"")
        with patch.object(worker,"load_json",return_value=native),patch.object(worker,"read_float",side_effect=floats), \
             patch.object(worker,"read_csv",side_effect=lambda p:timeline if p.name=="telemetry.csv" else callbacks):
            return worker.validate(Path("synthetic/offline"),48000,128,native["mode"],"test")

    def test_fixed_fourteen_capture_six_process_bound(self):
        self.assertEqual(len(worker.jobs()),6)
        self.assertEqual(sum(j[3] for j in worker.jobs()),14)
        self.assertEqual(len(set(worker.jobs())),6)

    def test_complete_worker_fixture_passes_without_hiding_worker_allocations(self):
        result=self.validate_fixture(self.fixture())
        self.assertTrue(result["pass"])
        self.assertEqual(result["callback"]["allocation_calls"],0)
        self.assertEqual(sum(w["body_allocations"] for w in result["native"]["workers"]),3)

    def test_callback_allocation_and_scheduled_deadline_failure_stay_failed(self):
        for fault in ("allocation","deadline","worker"):
            fixture=self.fixture("paced")
            if fault=="allocation":fixture[4][0]["allocations"]="1"
            elif fault=="deadline":fixture[4][0]["finish_ns"]=str(int(fixture[4][0]["deadline_ns"])+1)
            else:fixture[0]["workers"][0]["failed"]=True
            self.assertFalse(self.validate_fixture(fixture)["pass"],fault)

    def test_truncated_packets_wrong_hash_and_self_consistent_short_duration_rejected(self):
        for fault in ("packet","hash","duration","tail"):
            fixture=self.fixture()
            if fault=="packet":fixture[3].pop()
            elif fault=="hash":fixture[0]["voices"][0]["input_hash"]="wrong"
            elif fault=="duration":fixture[0]["frames"]-=128
            else:fixture[1][-1]=.001
            with self.subTest(fault=fault),self.assertRaises(ValueError):self.validate_fixture(fixture)

    def test_consumed_claim_blocks_before_binary_or_native_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); claims=root/"build/worker-feasibility/claims"; claims.mkdir(parents=True)
            claim=claims/"test.json";claim.write_text("consumed")
            protocol={"id":"test","captures":{"process_cap":6,"total_cap":14}}
            with patch.object(worker,"ROOT",root),patch.object(worker,"load_json",return_value=protocol), \
                 patch.object(worker.subprocess,"check_output") as attest,patch.object(worker.subprocess,"run") as execute, \
                 self.assertRaises(FileExistsError):worker.run()
            attest.assert_not_called();execute.assert_not_called();self.assertEqual(claim.read_text(),"consumed")

    def test_oversized_matrix_rejected_before_execution(self):
        with patch.object(worker,"jobs",return_value=worker.jobs()+[(48000,128,"fault",1)]), \
             patch.object(worker.subprocess,"run") as execute,self.assertRaisesRegex(ValueError,"cap mismatch"):worker.run()
        execute.assert_not_called()
