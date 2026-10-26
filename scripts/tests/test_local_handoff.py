from pathlib import Path
import hashlib
import json
import plistlib
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import local_handoff as handoff


class LocalHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="voxide-handoff-tests-");self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.component=self.root/"build/candidate/voxide.component"
        for name in handoff.BUNDLE_FILES:
            path=self.component/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b"fixture")
        (self.component/"Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier":handoff.au.BUNDLE_ID,"CFBundleShortVersionString":"0.4.0","CFBundleExecutable":"voxide","AudioComponents":[handoff.au.IDENTITY]}))
        self.index=self.root/"docs/evidence/pr-10/handoff-index.json";self.index.parent.mkdir(parents=True)
        document=self.root/"docs/result.md";document.write_text("Negative qualification fixture, not human evidence")
        self.index.write_text(json.dumps({"schema":"voxide.pr10-evidence-index.v1","qualification":"not_qualified","entries":[{"id":"fixture","status":"open","document":"docs/result.md","artifact_manifest":"build/missing/artifacts.json"}]}))
        self.root_patch=patch.object(handoff,"ROOT",self.root);self.root_patch.start();self.addCleanup(self.root_patch.stop)

    def inspect(self):
        with patch.object(handoff,"verify_linkage",return_value=["/usr/lib/fixture"]),patch.object(handoff.subprocess,"check_output",return_value="fixture symbols"):
            return handoff.inspect_component(self.component)

    def test_local_identity_check_never_promotes_qualification(self):
        output=self.root/"build/report"
        with patch.object(handoff,"verify_linkage",return_value=["/usr/lib/fixture"]),patch.object(handoff.subprocess,"check_output",return_value="fixture symbols"):
            handoff.verify(self.component,output)
        report=handoff.load_json(output/"report.json")
        self.assertEqual(report["status"],"local_identity_and_evidence_check_pass_NOT_qualification")
        self.assertEqual(report["qualification"],"not_qualified");self.assertFalse(report["installed_files_accessed"])
        self.assertFalse(report["evidence"]["entries"][0]["raw_artifact_available_in_this_checkout"])

    def test_installed_and_private_paths_rejected_before_bundle_access(self):
        for path in (self.root/"Library/Audio/Plug-Ins/Components/voxide.component",self.root/"evaluation/pr-09/voxide.component"):
            with self.subTest(path=str(path)),patch.object(handoff.au,"check_identity") as identity,self.assertRaisesRegex(ValueError,"local build"):
                handoff.inspect_component(path)
            identity.assert_not_called()

    def test_unsafe_executable_metadata_rejected_before_linkage(self):
        path=self.component/"Contents/Info.plist";info=plistlib.loads(path.read_bytes());info["CFBundleExecutable"]="../../../private";path.write_bytes(plistlib.dumps(info))
        with patch.object(handoff,"verify_linkage") as linkage,self.assertRaisesRegex(ValueError,"executable path"):handoff.inspect_component(self.component)
        linkage.assert_not_called()

    def test_unrelated_bundle_payload_is_not_read(self):
        (self.component/"Contents/unknown.wav").write_bytes(b"synthetic unapproved payload")
        with patch.object(handoff,"sha256") as digest,self.assertRaisesRegex(ValueError,"Unexpected bundle layout"):handoff.inspect_component(self.component)
        digest.assert_not_called()

    def test_expected_hash_mismatch_and_product_symbols_rejected(self):
        with self.assertRaisesRegex(ValueError,"expected identity"):handoff.inspect_component(self.component,"a"*64)
        with patch.object(handoff,"verify_linkage",return_value=[]),patch.object(handoff.subprocess,"check_output",return_value="voxide::audit::begin"),self.assertRaisesRegex(ValueError,"Forbidden"):
            handoff.inspect_component(self.component)

    def test_changed_candidate_keeps_failed_report(self):
        output=self.root/"build/failure"
        def mutate(*_,**__):(self.component/"Contents/MacOS/voxide").write_bytes(b"changed");return "fixture"
        with patch.object(handoff,"verify_linkage",return_value=[]),patch.object(handoff.subprocess,"check_output",side_effect=mutate),self.assertRaisesRegex(ValueError,"changed"):
            handoff.verify(self.component,output)
        self.assertEqual(handoff.load_json(output/"report.json")["status"],"fail")

    def test_reports_cannot_mutate_verified_component_or_artifact(self):
        artifact=self.component.parent
        for output in (self.component/"report",artifact/"report"):
            with self.subTest(output=str(output)),self.assertRaisesRegex(ValueError,"disjoint"):
                handoff.verify(self.component,output,artifact=artifact)
            self.assertFalse(output.exists())

    def test_artifact_exact_manifest_and_mutation_checks(self):
        directory=self.root/"build/artifact";directory.mkdir();(directory/"source.txt").write_text("synthetic source")
        digest=hashlib.sha256((directory/"source.txt").read_bytes()).hexdigest()
        (directory/"artifacts.json").write_text(json.dumps({"schema":"voxide.artifacts.v1","files_sha256":{"source.txt":digest}}))
        self.assertEqual(handoff.inspect_artifact(directory)["verified_files"],1)
        (directory/"source.txt").write_text("edited")
        with self.assertRaisesRegex(ValueError,"bytes changed"):handoff.inspect_artifact(directory)

    def test_artifact_links_unknown_files_and_path_escape_refused(self):
        directory=self.root/"build/artifact";directory.mkdir();outside=self.root/"outside";outside.write_text("preserved")
        (directory/"linked").symlink_to(outside)
        (directory/"artifacts.json").write_text(json.dumps({"schema":"voxide.artifacts.v1","files_sha256":{"linked":"a"*64}}))
        with self.assertRaisesRegex(ValueError,"Unsafe artifact"):handoff.inspect_artifact(directory)
        for name in ("../outside","/absolute","build/../private","./source"):
            with self.subTest(name=name),self.assertRaises(ValueError):handoff.relative_path(name)
        self.assertEqual(outside.read_text(),"preserved")

    def test_index_refuses_private_artifact_references_and_missing_documents(self):
        value=json.loads(self.index.read_text());value["entries"][0]["artifact_manifest"]="evaluation/private/receipt.json";self.index.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,"out-of-scope"):handoff.evidence_index()
        value["entries"][0].pop("artifact_manifest");value["entries"][0]["document"]="docs/missing.md";self.index.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,"Missing tracked"):handoff.evidence_index()

    def test_index_symlink_refused_before_read(self):
        saved=self.root/"saved-index.json";self.index.rename(saved);self.index.symlink_to(saved)
        with self.assertRaisesRegex(ValueError,"symlink"):handoff.evidence_index()

    def test_dirty_reproduction_refused_without_clone_or_discard(self):
        with patch.object(handoff.subprocess,"check_output",return_value=" M user-work"),patch.object(handoff.subprocess,"run") as run, \
             patch.object(handoff,"cache_inventory") as cache,self.assertRaisesRegex(ValueError,"committed, clean"):
            handoff.reproduce(self.root/"cache")
        run.assert_not_called();cache.assert_not_called()

    def test_missing_offline_cache_blocks_clone(self):
        (self.root/"cmake").mkdir();(self.root/"cmake/JucePin.cmake").write_text('set(VOXIDE_JUCE_REVISION "fixture")\nset(VOXIDE_JUCE_SHA256 "'+"a"*64+'")\n')
        (self.root/"cmake/engine-dependencies.json").write_text(json.dumps({"packages":[{"name":"rubberband","revision":"fixture","sha256":"b"*64}]}))
        with patch.object(handoff.subprocess,"check_output",side_effect=["","revision","tree"]),patch.object(handoff.subprocess,"run") as run,self.assertRaisesRegex(ValueError,"offline archive"):
            handoff.reproduce(self.root/"cache")
        run.assert_not_called();self.assertFalse((self.root/"build/pr-10-reproduction").exists())
