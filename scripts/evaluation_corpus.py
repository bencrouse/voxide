"""Private corpus metadata, two independent annotations, and explicit holdout seal."""
from pathlib import Path

from evaluation_common import (CONTRACT, contained, digest_string, finite, identifier, integer, load_json,
                               require, sha256, wav_identity, write_json)
from evaluation_contract import load_contract, require_holdout_approvals
from evaluation_metrics import cents


def validate_annotation(data, source_id, info, expected_pcm_sha256=None, policy=None):
    require(data.get("schema") == "voxide.annotation.v2", "Unsupported annotation schema")
    require(data.get("source_id") == source_id and identifier(data.get("annotator_id")), "Annotation identity mismatch")
    require(digest_string(data.get("source_pcm_sha256")), "Missing annotation source PCM digest")
    if expected_pcm_sha256 is not None:
        require(data["source_pcm_sha256"] == expected_pcm_sha256, "Annotation source PCM mismatch")
    require(data.get("origin") in ("human", "synthetic"), "Missing annotation origin")
    require(integer(data.get("sample_rate"), 1) and integer(data.get("frames"), 1)
            and data["sample_rate"] == info["sample_rate"] and data["frames"] == info["frames"],
            "Annotation timebase mismatch")
    require(isinstance(data.get("grid"), list) and data["grid"], "Missing annotation grid")
    previous = -1
    for frame in data["grid"]:
        require(integer(frame.get("sample"), 0, info["frames"] - 1) and frame["sample"] > previous,
                "Invalid annotation timestamp")
        previous = frame["sample"]
        require(all(type(frame.get(key)) is bool for key in ("voiced", "stable", "uncertain")),
                "Missing annotation flags")
        hz = frame.get("f0_hz")
        require((frame["voiced"] and finite(hz) and 0 < hz < info["sample_rate"] / 2)
                or (not frame["voiced"] and hz is None), "Invalid F0/voicing annotation")
    if data["origin"] == "human":
        policy = load_contract() if policy is None else policy
        hop = round(policy["measurement"]["frame_hop_ms"] * info["sample_rate"] / 1000)
        require([frame["sample"] for frame in data["grid"]] == list(range(0, info["frames"], hop)),
                "Human annotations require the complete contract sample grid")
    ids = set()
    for landmark in data.get("landmarks", []):
        require(identifier(landmark.get("id")) and landmark["id"] not in ids, "Duplicate landmark ID")
        ids.add(landmark["id"])
        require(landmark.get("kind") in ("onset", "transition", "consonant", "ending"), "Invalid landmark kind")
        require(integer(landmark.get("sample"), 0, info["frames"] - 1)
                and integer(landmark.get("uncertainty_samples"), 0, info["frames"]), "Invalid landmark timestamp/uncertainty")
    return data


def compare_annotations(first, second, policy=None):
    policy = load_contract() if policy is None else policy
    tolerance = policy["quality"]["pitch_tolerance_cents"]
    require(first["source_id"] == second["source_id"] and first["sample_rate"] == second["sample_rate"]
            and first["frames"] == second["frames"]
            and first["source_pcm_sha256"] == second["source_pcm_sha256"], "Annotation sources/timebases/PCM differ")
    require(first["annotator_id"] != second["annotator_id"], "Annotators must be distinct")
    require([x["sample"] for x in first["grid"]] == [x["sample"] for x in second["grid"]],
            "Annotators must use the same sample grid")
    uncertain, comparable, disagreements = 0, 0, []
    for a, b in zip(first["grid"], second["grid"]):
        if a["uncertain"] or b["uncertain"]:
            uncertain += 1
            continue
        comparable += 1
        if a["voiced"] != b["voiced"] or a["stable"] != b["stable"] or (
                a["voiced"] and abs(cents(a["f0_hz"], b["f0_hz"])) > tolerance):
            disagreements.append(a["sample"])
    left = {x["id"]: x for x in first.get("landmarks", [])}
    right = {x["id"]: x for x in second.get("landmarks", [])}
    landmark_disagreements = []
    for key in sorted(left.keys() | right.keys()):
        a, b = left.get(key), right.get(key)
        if a is None or b is None or a["kind"] != b["kind"] or abs(a["sample"] - b["sample"]) > (
                a["uncertainty_samples"] + b["uncertainty_samples"]):
            landmark_disagreements.append(key)
    return {"schema": "voxide.annotation-agreement.v1", "source_id": first["source_id"],
            "source_pcm_sha256": first["source_pcm_sha256"], "contract_sha256": policy["_sha256"],
            "annotators": [first["annotator_id"], second["annotator_id"]],
            "comparable_frames": comparable, "uncertain_frames": uncertain,
            "disagreement_samples": disagreements, "landmark_disagreements": landmark_disagreements,
            "status": "agreement" if comparable and not disagreements and not landmark_disagreements else "needs_review",
            "scope": "Agreement is not proof of true pitch; uncertainty remains excluded"}


def validate_corpus(path, contract_path=CONTRACT):
    policy = load_contract(contract_path)
    resources = policy["listening"]
    path = Path(path)
    data = load_json(path)
    require(data.get("schema") == "voxide.corpus.v1" and identifier(data.get("id")), "Invalid corpus schema/ID")
    require(isinstance(data.get("sources"), list) and isinstance(data.get("reviewers"), list), "Missing corpus lists")
    reviewers = {}
    for person in data["reviewers"]:
        require(identifier(person.get("id")) and person["id"] not in reviewers, "Duplicate/invalid reviewer")
        require(type(person.get("independent")) is bool, "Missing reviewer independence")
        require(isinstance(person.get("roles"), list) and person["roles"] and
                set(person["roles"]) <= {"annotator", "listener", "singer", "engineer_producer"}, "Invalid reviewer roles")
        reviewers[person["id"]] = person
    ids, speakers, file_hashes, pending, disagreements = set(), {}, {}, [], []
    counts = {"development": 0, "holdout": 0}
    purposes = {"corpus_excerpt": 0, "user_session": 0}
    for source in data["sources"]:
        source_id = source.get("id")
        require(identifier(source_id) and source_id not in ids, "Duplicate/invalid source ID")
        ids.add(source_id)
        speaker = source.get("speaker_id")
        require(identifier(speaker), "Invalid speaker ID")
        split = source.get("split")
        require(split in counts, "Invalid corpus split")
        require(speaker not in speakers or speakers[speaker] == split, "Singer leakage across development/holdout")
        speakers[speaker] = split
        counts[split] += 1
        require(source.get("purpose") in purposes, "Missing source purpose")
        purposes[source["purpose"]] += 1
        rights = source.get("rights", {})
        require(rights.get("local_evaluation_permitted") is True and identifier(rights.get("consent_id")),
                "Missing explicit local evaluation permission/consent reference")
        require(source.get("origin") == "recording", "Private corpus must contain recordings, not invented singers")
        audio = contained(path.parent, source["audio"]["path"])
        digest = sha256(audio)
        require(digest == source["audio"]["sha256"], "Corpus audio hash mismatch")
        info, audio_pcm = wav_identity(audio)
        require(audio_pcm not in file_hashes, "Duplicate recording PCM in corpus")
        file_hashes[audio_pcm] = split
        require(all(integer(source.get(k), 1) and source[k] == info[k]
                    for k in ("sample_rate", "channels", "bits", "frames")),
                "Corpus audio metadata mismatch")
        annotations, annotators = [], set()
        for record in source.get("annotations", []):
            annotation_path = contained(path.parent, record["path"])
            require(sha256(annotation_path) == record["sha256"], "Annotation hash mismatch")
            annotation = validate_annotation(load_json(annotation_path), source_id, info, audio_pcm, policy)
            person = annotation["annotator_id"]
            require(annotation["origin"] == "human" and person in reviewers
                    and "annotator" in reviewers[person]["roles"] and person not in annotators,
                    "Expected distinct registered human annotators")
            if annotation.get("review_status") != "completed":
                pending.append(source_id + ": annotation is not declared completed by its reviewer")
            annotators.add(person)
            annotations.append(annotation)
        if len(annotations) != 2:
            pending.append(source_id + ": requires exactly two human annotations")
        else:
            result = compare_annotations(*annotations, policy=policy)
            if result["status"] != "agreement":
                disagreements.append(result)
                pending.append(source_id + ": annotation disagreement/uncertainty requires review")
            if not any(a["voiced"] and b["voiced"] and a["stable"] and b["stable"]
                       and not a["uncertain"] and not b["uncertain"]
                       for a, b in zip(annotations[0]["grid"], annotations[1]["grid"])):
                pending.append(source_id + ": no jointly stable/certain voiced reference frames")
        duration = info["frames"] / info["sample_rate"]
        if not resources["excerpt_seconds_min"] <= duration <= resources["excerpt_seconds_max"]:
            pending.append(source_id + ": outside contract excerpt duration")
        if not source.get("coverage_tags") or not isinstance(source["coverage_tags"], list):
            pending.append(source_id + ": missing coverage tags")
    listeners = [p for p in reviewers.values() if "listener" in p["roles"]]
    required = ((purposes["corpus_excerpt"] >= resources["excerpts"] and purposes["user_session"] >= resources["user_passages"],
                 "required corpus excerpts/user passages not yet supplied"),
                (len(speakers) >= resources["singers"], "required singers not yet supplied"),
                (all(counts.values()), "both development and holdout must be populated"),
                (len(listeners) >= resources["listeners"], "required listeners not yet identified"),
                (sum(p["independent"] for p in listeners) >= resources["independent_listeners"], "required independent listeners not yet identified"),
                (sum("singer" in p["roles"] for p in listeners) >= resources["singer_listeners"], "required singer listeners not yet identified"),
                (sum("engineer_producer" in p["roles"] for p in listeners) >= resources["vocal_engineers_or_producers"], "required engineer/producer listeners not yet identified"),
                (data.get("split_approved") is True, "singer-separated split/coverage approval pending"))
    pending.extend(reason for condition, reason in required if not condition)
    return {"schema": "voxide.corpus-validation.v1", "status": "pending" if pending else "pass",
            "contract_sha256": policy["_sha256"],
            "manifest_sha256": sha256(path), "sources": len(ids), "singers": len(speakers),
            "split_counts": counts, "blockers": pending, "annotation_disagreements": disagreements,
            "scope": "Corpus readiness, not completed listening or product qualification"}


def corpus_files(path):
    path = Path(path)
    data = load_json(path)
    records = {path.name: sha256(path)}
    for source in data["sources"]:
        for record in [source["audio"], *source.get("annotations", [])]:
            records[record["path"]] = sha256(contained(path.parent, record["path"]))
    return records


def seal_corpus(path, settings, output, contract_path=CONTRACT):
    contract = load_contract(contract_path)
    require(validate_corpus(path, contract_path)["status"] == "pass", "Cannot seal an incomplete/unreviewed corpus")
    require_holdout_approvals(contract)
    configuration = load_json(settings)
    candidate = configuration.get("candidate", {})
    require(configuration.get("schema") == "voxide.frozen-settings.v1"
            and identifier(configuration.get("id")) and configuration.get("approved_for_holdout") is True
            and configuration.get("contract_sha256") == sha256(contract_path)
            and identifier(candidate.get("id")) and isinstance(candidate.get("revision"), str)
            and candidate["revision"] and isinstance(candidate.get("parameters"), dict) and candidate["parameters"],
            "Explicit settings freeze approval required")
    write_json(output, {"schema": "voxide.holdout-seal.v1", "corpus_files": corpus_files(path),
                        "settings_sha256": sha256(settings), "settings_id": configuration["id"],
                        "contract_sha256": sha256(contract_path)})


def select_sources(path, split="development", seal=None, settings=None, allow_holdout=False, contract_path=CONTRACT):
    require(split in ("development", "holdout"), "Unknown split")
    contract = load_contract(contract_path)
    readiness = validate_corpus(path, contract_path)
    if split == "holdout":
        require(allow_holdout and seal is not None and settings is not None, "Holdout requires explicit access and frozen settings/seal")
        frozen = load_json(seal)
        require(frozen.get("schema") == "voxide.holdout-seal.v1"
                and frozen["corpus_files"] == corpus_files(path)
                and frozen["settings_sha256"] == sha256(settings)
                and frozen.get("contract_sha256") == sha256(contract_path),
                "Corpus/settings/contract changed since holdout seal")
        require_holdout_approvals(contract)
        require(readiness["status"] == "pass", "Corpus readiness no longer passes")
    return [source["id"] for source in load_json(path)["sources"] if source["split"] == split]
