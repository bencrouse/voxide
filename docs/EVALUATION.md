# PR 02 — evaluation foundation

PR 01 established a dry AU and routing diagnostics. **This PR prepares trustworthy
tests; it adds no musical DSP, production pitch tracker, shifter or harmonies.**
Everything is local, offline and standard-library Python. No new dependencies,
microphone capture, file-library discovery, DAW operation, installs or uploads.
Source files are read only when their paths are explicitly supplied or they are
committed synthetic fixtures. Real recordings, names, consent, settings seals,
annotations and listening results belong under ignored `evaluation/pr-02/`.

Actual commands, outcomes and limitations are recorded in
[evaluation validation](EVALUATION_VALIDATION.md).

## What is approved, implemented, or still missing?

- **Approved by the user:** the plan's numerical targets, with the shift range
  widened to **−24…+24 semitones** on 2026-10-21. Input remains E2–C6; mathematical
  output extremes become MIDI 16–108, approximately 20.60–4,186.01 Hz. Report common
  shifts through ±7, octave shifts through ±12, and two-octave shifts separately.
  Neither the wider range nor the latency/quality targets are achieved capabilities.
- **Machine-readable baseline:** `docs/evidence/pr-02/contract.json`. Its SHA-256
  travels with engineering reports. Threshold changes require an explicit contract
  revision/review, not adjustment to make a candidate pass.
  Review revision `pr02-contract-002` keeps the approved numerical values unchanged
  and makes the still-pending measurement/listening/resource approvals enforceable.
- **Implemented:** frozen analytic fixtures, integrity/metadata/annotation validators,
  singer-separated corpus/holdout controls, a lead-copy/control render path, offline
  pitch/resonance/null/delay/response tools, negative controls and JSON evidence.
- **Still pending:** the complete qualified corpus, actual independent annotations,
  listener availability/results, split coverage and listening-procedure approval.
  Three explicitly permitted AIFF pilot recordings have now been prepared as
  lossless mono WAV copies and 12-second excerpts. The user confirms solo, untuned
  recordings of the same singer; dry status remains provisional. All three are
  registered as development-only pilot material, with no actual reviewer IDs or
  completed annotations yet. The user has passed the first coarse source-audio
  listening check; this is not pitch-reference validation or independent agreement.
  No unrelated
  audio library or private Logic project was searched.
- **Musical decisions remain open:** initial scales and degree mapping, non-scale
  notes/ties/range handling, vibrato/scoop expression, ambiguous input, slot allocation
  and unsupported-source behavior. Do not invent approval or start PR 03 against
  silently chosen semantics. New protocol choices such as the 10 ms annotation hop,
  20 ms settling dwell and draft listening levels are documented engineering
  proposals, not additional user-approved perceptual requirements.

There are two distinct outcomes: **engineering checks pass** versus **the full
PR 02 resource/approval gates are satisfied**. The former never implies the latter.
The plan's missing human gates still block full PR 02 acceptance and downstream
architecture go-decisions. Engineering implementation is not a waiver of them.

On 2026-10-22 the user approved merging the reviewed engineering foundation and
deferring detailed manual annotations until actual tracker development. This
permits the engineering merge and PR 03 development, **not** holdout access,
unapproved musical semantics, a reduced quality target or final product acceptance.
All pending approvals and reference requirements remain explicitly pending.

PR 03 subsequently records user-approved starter musical semantics in
`docs/evidence/pr-03/musical-contract.json`; this resolves the corresponding starter
decisions above, not the remaining measurement/listening/resource approvals.
`docs/TRACKING.md` documents compiled causal-tracker research, native traces and
known timing misses. PR 02's frozen contract/fixtures remain unchanged.

## Commands

```sh
make evaluation-check
python3 scripts/check.py --full --offline
```

The evaluation check validates frozen fixture files, runs focused Python regressions,
calibrates independent measurements, and creates a unique
`build/evaluation-checks/<run>/report.json` plus `tests.log`. It records source hashes,
contract/catalog hashes, Python/architecture, actual measurements and failures.
Sources changing during a run invalidate it. `acceptance_status` remains pending
when no qualified human corpus was supplied to that engineering run.

Ordinary CTest's existing `tooling` suite also discovers all new evaluation tests.
ASan/TSan remain focused on native DSP/processor tests, not Python or all host UI.
Checks regenerate probes **only in temporary directories** and compare against
committed expected hashes. Nothing updates expected audio or ratings implicitly.

### Controlled render example

```sh
python3 scripts/evaluation.py render-control \
  --source Source/Tests/Fixtures/pr02/sine-mid-48000.wav \
  --controls Source/Tests/Fixtures/pr02/sine-mid-48000-controls.json \
  --delay-samples 137 --blocks 32,64,128,257,512,1024 \
  --directory evaluation/pr-02/control-render-001
python3 scripts/evaluation.py compare-lead \
  --source Source/Tests/Fixtures/pr02/sine-mid-48000.wav \
  --output evaluation/pr-02/control-render-001/lead.wav --delay-samples 137
python3 scripts/evaluation.py measure-delay \
  --source Source/Tests/Fixtures/pr02/sine-mid-48000.wav \
  --output evaluation/pr-02/control-render-001/lead.wav --maximum-samples 256
```

The renderer writes a delayed lead and control schedule, preserving source PCM
words and bit depth, then null-checks
the **decoded output WAV**, not just an unencoded buffer. The example creates a new
directory and refuses overwrite. It does not run the plug-in or simulate harmony
voices. The measured unity path has no resampling or re-quantization; do not widen
the null tolerance to mask conversion or copy errors. A control's source sample is preserved
as `block_start + offset`; events at the same sample retain their input order.

Delay correlation is only a **unity/known-probe tool**. Silence or ambiguous peaks
are rejected. A returned delay still needs the fixed-delay null test; correlation
is not proof of perfect copying. For shifted material use envelopes/known transitions
and report uncertainty, not invalid raw-waveform alignment. These tools measure no
interface round trip, Logic PDC or analog monitoring latency.

## Schemas and private corpus intake

JSON is strict: duplicate keys and NaN/Infinity are rejected. Hashes identify exact
bytes. Evidence outputs use exclusive creation. Manifest references must remain
relative to their manifest root; traversal and symlink references are rejected.
The validators are executable schemas; the examples below show their structures.

Finite-looking exponents that overflow (`1e999`) are rejected too, including nested
values. PCM identity hashes include the PCM words, sample rate, channel layout,
bit depth and frame count, ignoring unrelated RIFF chunks. File hashes still bind
the exact container bytes independently. This prevents replacing a source with
same-length different audio while reusing its annotations, and detects duplicate
PCM even when WAV container metadata differs.

```sh
python3 scripts/evaluation.py corpus-init --directory evaluation/pr-02/intake
python3 scripts/evaluation.py corpus-validate evaluation/pr-02/intake/corpus.json
```

An empty intake is **pending**, exit status 2, not a passed vocal corpus. To start,
the user only needs to place permitted dry mono WAVs there and identify which may
be used. Preferred source is 24-bit/48 kHz; mono PCM16/24/32 at 44.1/48 kHz is
accepted. No automatic downmix, resampling, tuning, compression, denoising or
recording is performed. Float/compressed/stereo WAVs require a separately agreed
conversion; never quietly change them. Initial recordings can be a small development
pilot; they do not satisfy the six-singer holdout/listener requirements.

The corpus manifest has schema `voxide.corpus.v1`, an opaque `id`, a
`split_approved` boolean, `reviewers` and `sources` arrays. A reviewer is:

```json
{"id":"person-a","independent":true,"roles":["annotator","listener","singer"]}
```

Permitted roles are `annotator`, `listener`, `singer`, `engineer_producer`.
Independence and consent are human declarations, not facts software can authenticate.
Keep actual identities/consent documents private; `consent_id` is only an opaque
reference to permission the administrator has checked. A source entry is:

```json
{
  "id":"vocal-001","speaker_id":"singer-a","split":"development",
  "origin":"recording","purpose":"corpus_excerpt",
  "rights":{"local_evaluation_permitted":true,"consent_id":"permission-a"},
  "sample_rate":48000,"channels":1,"bits":24,"frames":576000,
  "audio":{"path":"vocal-001.wav","sha256":"REPLACE_WITH_EXACT_SHA256"},
  "coverage_tags":["low-register","legato","sibilants"],
  "annotations":[
    {"path":"vocal-001-person-a.json","sha256":"REPLACE_WITH_EXACT_SHA256"},
    {"path":"vocal-001-person-b.json","sha256":"REPLACE_WITH_EXACT_SHA256"}
  ]
}
```

`purpose` is `corpus_excerpt` or `user_session`; `split` is `development` or
`holdout`. A singer may occur in only one split. Duplicate source IDs or audio bytes
are rejected, including across splits. Corpus readiness requires 24 excerpts and two
user passages, six singers, both splits, 10–15-second excerpts, coverage tags, two
distinct registered/completed human annotations per source, no unadjudicated
disagreement, and explicit split approval. It also checks the planned six listeners,
four independent, two singer listeners and two engineers/producers. These counts
alone do not prove coverage: the administrator must approve range/articulation
coverage in **both** splits and not use stress material to imply ordinary support.

### Annotation instructions

```sh
python3 scripts/evaluation.py annotation-template \
  --audio evaluation/pr-02/intake/vocal-001.wav \
  --source-id vocal-001 --annotator-id person-a \
  --output evaluation/pr-02/intake/vocal-001-person-a.json
```

Templates embed the source PCM digest and are drafts with **every frame uncertain**,
not fake annotations. Two
people annotate independently before comparing results; do not hand one annotator's
answers to the other. Use a free tool such as Praat if already available; it is not
a build dependency or an unquestionable oracle. Do not certify Voxide using its
own eventual tracker. Complete the shared 10 ms grid without deleting uncertain
frames. Each frame has:

```json
{"sample":4800,"voiced":true,"f0_hz":220.0,"stable":true,"uncertain":false}
```

Unvoiced frames use `f0_hz: null`; uncertain frames are explicitly marked. F0 is
positive and below Nyquist. `sample` is an integer source-frame index. An annotation
contains schema `voxide.annotation.v2`, `source_id`, `source_pcm_sha256`, `annotator_id`, `origin: human`,
`review_status: completed`, source `sample_rate`/`frames`, `grid`, and `landmarks`:

```json
{"id":"onset-a","kind":"onset","sample":4320,"uncertainty_samples":240}
```

Landmark kinds: onset, transition, consonant, ending. Mark the first source-active
sample for onset and the first change for transitions, not the time an analysis
tool finally recognizes it. Mark ambiguous boundaries with uncertainty intervals.
Exclude ±50 ms around voiced/phonetic boundaries from stable-frame accuracy;
retain those regions for separate onset/consonant/response analysis. Continuous
vibrato and scoops need their own expression policy before judging note decisions.

```sh
python3 scripts/evaluation.py annotations-compare \
  evaluation/pr-02/intake/vocal-001-person-a.json \
  evaluation/pr-02/intake/vocal-001-person-b.json
```

The comparison reports voicing/stability disagreements, >25-cent F0 differences,
landmark disagreement beyond the combined uncertainty intervals, comparable and
uncertain counts. Agreement is not ground truth. Discuss disagreements, retain the
original versions, record adjudication rationale privately, and publish **new**
reviewed annotation versions/hashes. Keep genuinely ambiguous regions uncertain
rather than forcing agreement. At least one jointly certain stable voiced frame
must exist; software never treats an entirely uncertain corpus as qualified.

### Seal holdout only after settings and references are frozen

```sh
python3 scripts/evaluation.py corpus-select evaluation/pr-02/intake/corpus.json
python3 scripts/evaluation.py corpus-seal evaluation/pr-02/intake/corpus.json \
  --settings evaluation/pr-02/frozen-settings-001.json \
  --output evaluation/pr-02/holdout-seal-001.json
python3 scripts/evaluation.py corpus-select evaluation/pr-02/intake/corpus.json \
  --split holdout --allow-holdout --settings evaluation/pr-02/frozen-settings-001.json \
  --seal evaluation/pr-02/holdout-seal-001.json
```

Settings schema `voxide.frozen-settings.v1` needs an opaque `id`,
`approved_for_holdout: true`, the current `contract_sha256`, and
`candidate: {id, revision, parameters}` with the exact nonempty candidate/build/
configuration/analysis parameters being frozen. Musical-policy approval in the
contract must be completed first. Numerical, musical, measurement-protocol,
listening-protocol and resource approvals are checked by **both sealing and
selection**, not inferred from a structurally valid corpus or settings approval.
The current pending contract cannot seal or open a real holdout. Sealing refuses an
incomplete corpus and captures byte hashes of manifest, audio, annotations and settings.
Later changes, including contract changes, invalidate the seal. Selection defaults to development and requires
explicit opt-in for holdout. This is a reproducibility/workflow guard, **not** an
OS sandbox: arbitrary file tools can still read files. Metadata/reference QA is
allowed while curating the corpus; candidate tuning/evaluation on holdout is not.

## Measurement definitions and limits

All grading entry points share `evaluation_contract.py`, reject revoked numerical
approval and invalid/unsupported policies, derive timing/tolerances from the loaded
contract and report its exact hash. The repository contract is the default; an
explicit reviewed alternative can be selected **before** a scoring subcommand with
`--contract /path/to/contract.json`. A valid revision is applied, not silently scored
against old constants. `check` always uses the repository contract. Sample intervals
are rounded to integer samples at the actual rate, including annotation grids.

Control references use **`voxide.controls.v2`** with `source_id`,
`source_pcm_sha256`, `sample_rate`, `frames` and `events`. The renderer checks them
against the actual WAV. The application scorer takes its clock/range from that
independent reference and rejects mismatching application rate, duration, ID or PCM
digest. Legacy unbound v1 controls/annotations are rejected, not guessed/migrated.
All 28 fixture WAVs remain byte-identical across this explicit v2 metadata revision.
Noise-burst onset is now its actual first nonzero sample; silence has no onset.

- `measure --kind pitch --audio <wav> --start <sample> --frames <count>` uses an
  independent offline FFT-normalized-autocorrelation estimator. It is calibrated
  on sines, missing fundamentals and the two-octave output endpoints. Silence/noise
  return uncertain/no F0. It has access to the whole window: **no live response or
  production tracking claim follows**. Difficult vocal estimates require human review.
- `measure --kind resonances` uses a Welch/Hann spectrum and fixed bands
  300–900 / 900–1,700 / 1,800–3,300 Hz. Known-noise resonators calibrate it; it is
  **not** a general vocal formant estimator or a trustworthy high-F0 vocal reference.
- `score-pitch --reference <annotation> --observations <json>` compares identical
  sample grids. Observation schema `voxide.pitch-observations.v2` contains source
  identity/timebase, the source `source_pcm_sha256`, exact `reference_sha256`, `producer: {id, revision}`, and
  `grid` with `{sample,f0_hz}`.
  Encode unavailable/uncertain output F0 as null. Missing voiced estimates remain
  in the denominator, not silently dropped. Uncertain/nonstable reference frames
  are excluded and counted. Unvoiced false positives are separate. Reports include
  counts, octave errors (any nonzero integer octave multiple), nearest-rank P95 and Wilson 95%
  intervals; correlated frames mean those intervals are descriptive, not independent
  population confidence. No denominator means pending, not pass. Report per-source,
  singer/register and shift tier before pooling; a pooled pass cannot hide a failed tier.
- `score-response --reference <json> --decisions <json>` uses reference schema
  `voxide.response-reference.v1` with source identity/rate and events
  `{id,kind: cold_onset|transition,sample,target_hz}`. Decisions schema
  `voxide.decisions.v1` includes `reference_sha256`, uses the same source clock
  and grid `{sample,f0_hz}` where
  sample is **decision arrival time**, not a backdated source-window center. A correct
  decision must persist for a 20 ms dwell with no gap over 10 ms; settling time is
  when that dwell **finishes**. Cold/continuous and below/above 150 Hz groups are
  separate; missing decisions fail, missing groups remain pending. Do not combine
  these acquisition times with audio delay by blindly adding overlapping budgets.
- `score-controls --reference <controls> --applications <json>` matches each event
  ID/order to its observed application sample. Schema `voxide.control-applications.v2`
  includes `reference_sha256`, `source_id`, `source_pcm_sha256`, sample rate, frame
  count, `control_interval_samples`, and events
  `{id,sample}`. Missing/reordered/early applications are rejected. The screen requires
  response within one control interval **and** the 5 ms target. It says nothing
  about MIDI hardware delivery or audible settling. Application samples must be
  nondecreasing in the declared event order; ties preserve that order. A correct
  ID list cannot hide timestamps reporting the later event applied first.
- Unity/null checks include exact expected leading zeros and duration/tail. Maximum
  error is ≤1e-6 and RMS ≤1e-7. Do not optimize away a one-sample error by realigning
  after specifying the expected delay. Shifted signals use separate pitch/formant
  metrics, not deterministic unity tolerances.

### Listening packet and rating contract (human acceptance pending)

The administrator retains the private condition identity key. Trial IDs, source IDs,
listener IDs and session IDs are opaque; no personal names in shareable reports.
Randomize/counterbalance opaque conditions in balanced subsets across two approximately
45-minute sessions. Include exposed individual harmonies, the three-voice sum and
one fixed representative mix, hidden duplicates and a degraded anchor. There is no
perfect transformed reference and this is not formal MUSHRA.

The proposed exact level recipe is source RMS −24 dBFS, dry lead 0 dB and each harmony
−9.542425 dB (one-third amplitude), with ≤0.2 dB condition-level matching. Apply one
common condition gain to all stems together, never independently normalize harmony
stems or repair/limit/EQ defects. If headroom is insufficient, reduce the whole trial
equally and record the change; do not clip or secretly compress. This is an RMS-based
draft protocol, **not LUFS loudness certification**; approve it with listeners before
actual candidate comparisons. Optional backing is identical for all conditions and
never masks a failed exposed stem. Native timing is retained for response tests;
overall delay may be aligned for timbre-only comparisons and must be recorded.

Use a private JSON rating manifest with schema `voxide.listening-ratings.v1`,
`protocol_id`, `protocol_sha256`, `trial_manifest_sha256`, `listener_id`,
`session_id`, `environment` (headphone path and playback level, no serial/hostname),
and `ratings`. Each rating contains `trial_id`, context (`stem`, `sum`, `fixed_mix`),
integer 1–5 naturalness/articulation/stability/usability, `usable_without_repair`
boolean, and timestamped defects `{sample,severity,description}`. Retain blind label
maps separately; missing ratings, listeners, duplicate checks or contexts are pending,
not perfect scores. Critical/major/minor definitions and the numerical listening
gates live in the contract. Critical defects require independent confirmation by
two people; do not manufacture it from repeated ratings by the implementer.

These are schemas/instructions for later real trials, **not completed listening
packets, a listening application, ratings validator, or fabricated human results**.
No independent listeners have been identified to the agent yet.
