# PR 02 validation record

Branch: `pr-02-evaluation-foundation`, based on PR 01 commit `22f16c3`.
No AU implementation, component identity, bus routing, parameter, state or product
DSP changes. PR 01's host observations and limitations remain unchanged.

## Evidence boundaries

| Area | Status |
| --- | --- |
| Numerical baseline | User approved plan targets, extending shifts to ±24 semitones |
| Synthetic asset generation/integrity | 28 original PCM24 WAVs with sample-indexed analytic/control JSON, 44.1/48 kHz |
| Focused post-review regression tests | 37 passed in the fingerprinted evaluation run |
| Post-review engineering check and calibration report | Passed; `build/evaluation-checks/20261021T183802Z-23a2dc5c/report.json` |
| Post-review native Debug/Release/ASan/TSan regressions | Passed; `build/checks/20261021T183812Z-afea1991/environment.json` |
| Actual permitted vocal corpus | Three permitted pilot recordings prepared; full qualified corpus and source-condition confirmation pending |
| Real two-annotator agreement/adjudication | Not performed |
| Human listener availability/results and split approval | Pending |
| Musical/source policy and new protocol approval | Pending; no implied approval from numerical targets |
| Product pitch/harmony quality or monitoring latency | Not measured by this PR |

Final post-review `make evaluation-check` passed 37 tests and 14 calibration
measurements with stable source fingerprints. The full offline run passed all 12
steps: Debug/Release 5/5 suites each and focused native ASan/TSan 2/2 each. Source,
asset, contract and binary hashes are retained in the linked reports; only
documentation changed afterward. Later authorized pilot artifacts remain private
and do not change tested code or expected assets. Human acceptance remains pending.

Pre-review `make evaluation-check` passed 26 tests with a stable source fingerprint and 14 calibrated
measurements across the two rates. Maximum static-probe pitch error was approximately
0.323 cents; maximum baseline synthetic-resonance error was approximately 1.451%.
The report retains individual measurements, confidence/window metadata and deliberate
fault results. These are properties of the measurement tools on the specified
analytic probes, **not** the harmonizer's tracking, pitch shifting or formant quality.
That historical run is retained at `build/evaluation-checks/20261021T170656Z-9bfd4cae/`.
It does not qualify the subsequently changed source or revised fixture metadata.

Pre-review `python3 scripts/check.py --full --offline` passed all 12 configure/build/test steps
with a stable source fingerprint: Debug and Release each passed 5/5 suites (including
the expanded Python tooling suite), and ASan/TSan each passed 2/2 focused native
suites. Logs and source/binary/environment hashes are retained in the directory
`build/checks/20261021T170736Z-7efa8d9e/`. ASan retains the existing documented
leak-detection exclusion; Python tools are not sanitizer-instrumented. Review fixes
require new qualification rather than silently substituting these older results.

At engineering qualification, follow-up resource questions were interrupted and
no paths, permission references or reviewer IDs had been provided. The agent
continued with engineering/synthetic work only. The later explicitly authorized
pilot intake is recorded below; it does not retroactively change those test runs
or waive the plan's human gates. No unrelated audio library was searched.

## Software checks and actual scope

- Generate the same 28 assets into temporary directories and compare their file
  hashes/catalog to committed expectations. The expected directory is read-only
  to ordinary checks. Explicit generation refuses an existing destination.
- Inspect exact WAV payload lengths, rates, mono layout and PCM width. Preserve
  PCM16/24/32 words through delayed lead-copy render and null-check decoded output.
- Reject malformed MIDI note/channel/velocity/sample values, unsorted events and
  invalid block partitions; preserve same-sample ordering across 32/64/128/257/512/
  1024 and mixed block sizes. This is offline scheduling, not AU MIDI delivery.
- Calibrate offline independent autocorrelation on low/mid/high source sines,
  missing fundamentals and 20.60/4,186.01 Hz output extremes at both rates.
- Recover deliberate ±24/+12/+1-semitone probe shifts, detect octave errors and
  missing estimates without excluding them from stable voiced denominators.
- Calibrate fixed-band spectral resonance measurement at 650/1,100/2,450 Hz using
  broadband resonators; detect a deliberate 15% resonance shift beyond the 10% gate.
  This is not a qualified real-singer formant measurement.
- Recover a known 137-sample delay; fixed-delay null tests reject off-by-one, gain
  and duration/tail errors. Unity correlation is not shifted-audio latency evidence.
- Check response settling confirms at the **end** of the 20 ms dwell, resets after
  missing/incorrect observations, separates cold/transition/register groups and
  keeps absent cases pending. Control response rejects early, missing or reordered
  applications and reports late applications as failures.
- Require complete shared human annotation grids, distinguish draft templates from
  completed reviews, report disagreement/uncertainty and reject invalid timestamps/F0.
- Reject corpus permission omissions, hash/metadata errors, duplicate IDs/audio,
  singer leakage, unsafe paths and unregistered/repeated annotators. Missing people,
  passages, annotations or approval remain pending rather than passing.
- Holdout selection defaults to development. Require a complete corpus, numerical,
  musical, measurement/listening protocol and resource approvals, approved settings and a matching seal for
  holdout access. Changed settings, annotations or contract invalidate it.
- Strict JSON rejects duplicate keys, non-finite constants and exponent overflow; evidence writes
  refuse overwrite. Corpus/annotation references reject traversal and symlinks.

Corpus validator positive controls use temporary **synthetic test-only stand-ins**
with deliberately fake test IDs/consent metadata. They exercise structural validation
only, do not appear as qualified corpus entries, and are deleted with test temp roots.
No participant availability, consent authenticity or vocal truth can be established
by a parser, matching hashes, a test-only declaration or two agreeing algorithms.

## Independent PR 02 review and fixes

The existing right-hand Herdr `voxide-review` agent independently reviewed all
uncommitted PR 02 sources, tests, schemas, fixtures and docs using reads/searches
only. It reported seven P2 issues; no commands, private recordings or device
operations were involved. The implementing agent verified and addressed each:

1. **Unanchored control timebase:** v2 controls bind source ID, actual PCM digest,
   rate and duration. Application metadata must match the independent reference.
   The 224-sample/44.1 kHz case cannot pass by claiming 48 kHz.
2. **Application chronology:** timestamps must be nondecreasing in declared ID
   order, with stable ties. The a@135/b@23 failure now rejects even when IDs match.
3. **Unbound annotations:** v2 annotations embed the source PCM/timebase digest.
   Replacing same-duration audio and updating its manifest cannot reuse old references.
   Duplicate PCM with differing RIFF metadata is also rejected.
4. **Missing holdout approval gates:** sealing and selection use the same explicit
   approval checks. Musical approval alone cannot bypass pending measurement,
   listening or resource approval. No actual pending approval was changed to approved.
5. **Contract bypass/stale constants:** shared validated policy supplies score/null/
   response limits, dwell/hop, annotation grid and corpus requirements; outputs bind
   its hash. Revoked approval blocks scoring; reviewed alternative limits are applied.
6. **Incorrect frozen onset truth:** explicit analytic generator v2 corrects burst
   onset (3675/4000 samples at 44.1/48 kHz) and removes silence onset. Tests compare
   landmarks with decoded signal activity independently of regeneration.
7. **Numeric overflow:** strict parsing now rejects nested positive/negative
   exponent overflow as well as literal NaN/Infinity; huge integer F0 is rejected
   cleanly rather than raising an uncontrolled conversion error.

Additional implementing-agent regression: sparse ±3/±4-octave faults could previously
meet the 99% accuracy threshold while evading the octave counter. All nonzero
integer octave multiples now count; extreme finite pitch errors use log differences
to avoid ratio underflow/overflow.

The v1 analytic baseline is preserved privately in
`evaluation/pr-02/fixture-history/pr02-v1/`, and all 86 original fixture-file hashes
were verified against the pre-review qualification before revision. **All 28 WAV
files remain byte-identical**; only catalog/reference/control metadata and its README
changed. This was a reviewed oracle/schema correction, not regeneration from any
candidate's output. Catalog hashes:

- v1: `bdac87a03fea51f9e2e2d739059f55857fae31f7facb037ab41816b2df838b82`
- v2: `bd2c93f2aae5a4f972243bc1fd626e619d0bedc70786ba200f2a14b3ace31ca2`

`pr02-contract-002` preserves the approved numerical targets and adds enforceable
pending protocol/resource approval state. The same independent reviewer then read
the focused fixes and targeted regressions and reported **no remaining concrete
issues**. That was a file-read review only; the final post-review qualification
above was run separately by the implementing agent. Full PR 02 human/resource
acceptance remains pending.

## Completion policy and next input

**User-approved sequencing change — 2026-10-22:** commit/merge PR 02 as an
engineering milestone and defer detailed manual annotations to actual tracker
development. PR 03 implementation may proceed under this explicit change; no human
gate, musical policy, numerical target or final quality requirement is waived.
The strict holdout/approval guards and pending contract states remain unchanged.

Post-review engineering qualification passed the reruns above. Full PR 02
acceptance still requires the complete permitted vocal corpus,
two actual annotators, listener availability, approved split/protocol and remaining
musical semantics. No holdout/candidate go-gate is unlocked by synthetic calibration.

The initial intake and same-singer development registration are complete with the
three permitted pilots below. The next engineering milestone is the actual tracker
and note selector after confirming remaining musical behavior. Detailed references
and independent review remain deferred validation work, not completed observations;
keep dry status provisional until confirmed before timbre qualification.
This is **not** the complete six-singer qualification corpus. Do not immediately
ask for many decisions or imply completed annotation/listening is needed before
the pilot software can be exercised.

## Authorized private pilot intake — 2026-10-21

The user supplied three AIFF files in the designated intake directory and explicitly
approved local evaluation plus separate mono copies/excerpts, with no uploads.
Read-only format inspection found stereo PCM24/48 kHz at approximately 25.96,
27.32 and 17.76 seconds; all left/right channel words were bit-identical.

Private preparation output:
`evaluation/pr-02/pilot-20261021T190851Z-2c1c71d8/` contains full-length mono copies,
three 12-second literal excerpts, six unassigned annotation drafts,
`intake-report.json` and `pilot-validation.json`. The reproducible one-off intake
script is private under `evaluation/pr-02/tools/`; this does not add a new product
importer or claim the standard WAV validator accepts AIFF natively.

- Every original AIFF hash remained unchanged.
- Direct integer comparisons verified every full-copy sample equals its original
  channel value after endian conversion. Excerpts exactly match source PCM slices.
  There was no downmix gain, resampling, normalization, fade or effects processing.
- Native `afinfo` independently confirms three mono PCM24/48 kHz, 12-second WAVs.
- All recordings and excerpts had zero exact full-scale samples. This is not proof
  they were never clipped, limited or otherwise processed upstream.
- Excerpts begin approximately 0.47/2.65/0.83 seconds into their originals. The
  deterministic activity heuristic and slice indices are recorded privately; these
  are not manually annotated onsets or approved musical/phonetic boundaries.
- All 1,200 frames in each draft are uncertain, and no reviewer is assigned. Draft
  comparison correctly returns `needs_review`, not annotation agreement.
- At preparation time, source conditions and same-singer identity were unconfirmed;
  no singer IDs or completed reviews were invented. Later user confirmation and
  development-only registration are recorded below. These files do not constitute
  the six-singer development/holdout corpus or a listening qualification.

All recordings, derived audio, permission details, preparation code and pilot reports
remain ignored/private. No playback, microphone access, DAW operation, installations
or upload occurred. Only documentation changed in the reviewed codebase.

### Pilot source confirmation and registration

The user subsequently confirmed the same singer across all three recordings,
definitely solo and untuned, with dry conditions described as "should be dry".
That supports one opaque speaker ID, not three singers. Dry status stays provisional;
compression/reverb/other processing has not been independently established.

The private pilot directory now also contains `corpus.json` and
`registration-report.json`: three excerpts, one user-confirmed speaker, all in
development, no holdout, no assigned reviewers and no completed annotations. The
draft annotation templates are kept separately from accepted annotation references.
The validator correctly reports **pending**, not a qualified corpus. All original
and excerpt hashes were rechecked during registration; no audio was changed.

### First user source-audio check

The user listened to the three pilot excerpts and reported they all sounded good.
This is a completed single-reviewer **source-audio suitability check**, not pitch
annotation, confirmation of absent compression/reverb, blind listening, independent
agreement or product quality. The private `source-qc-review.json` binds that report
to the exact excerpt hashes. Actual reference annotation files remain unassigned,
all-uncertain drafts, and the corpus remains pending.

The next pilot step is a separately labeled automated pitch proposal for coarse
user review. Such proposals are not human ground truth and must not be copied
into completed human references or used to close the two-annotator/25-cent gates.

### Provisional offline pitch-review packet

Private proposals/review artifacts were prepared in
`evaluation/pr-02/pilot-20261021T190851Z-2c1c71d8/pitch-review-20261021T212526Z-779aee48/`;
friendly listening copies are under `evaluation/pr-02/listen-pitch-001/`.
Each 38-second review file contains voice alone (0–12 s), voice plus quiet sine
guide (13–25 s), and guide alone (26–38 s), separated by one-second gaps. Voice
in these **comparison copies** is scaled by 0.5 and the guide has maximum amplitude
0.08 with gate fades. Canonical excerpts/originals remain unchanged.

The guide follows independent offline normalized-autocorrelation proposals, not
Voxide DSP: 4,096-sample centered windows, 480-sample hop, 50–1,600 Hz search,
confidence ≥0.90 and window RMS ≥−55 dBFS. Centered windows use future samples;
there is no live-response claim. Estimates can contain wrong notes/octaves and
gaps; consonants/breaths need not have a pitch. All 1,200 proposals per clip remain
explicitly human-unconfirmed. Separate draft schemas prevent mistaking them for
completed human reference annotations. Raw proposals, code/configuration hashes,
human source-QC linkage and artifact-integrity checks are retained privately.

Artifact checks confirmed valid 38-second PCM24/48 kHz review files, safe digital
headroom, matching recorded hashes and unchanged source excerpts. This is not
pitch accuracy, voiced-reference coverage, harmony quality, independent agreement
or a 25-cent annotation pass.

### First coarse pitch-guide feedback

The user reports a and b sound "perfect", while c is less steady and may include
unintended notes. Record a/b as satisfactory **single-user coarse guide checks**,
not numerical accuracy or completed human references. C remains `needs_review`:
issue times and whether the variation belongs to the vocal, estimator, guide
gating or their combination have not yet been established.

Private `first-pitch-review-feedback.json` binds the exact user report to review
audio/proposal hashes. Read-only curve diagnostics were saved separately, without
altering sources, guides, proposals, thresholds or annotation references. Brief
guide bursts and pitch movements exist, but their presence alone does not establish
wrong intended notes. Keep c as a development challenge case; do not drop it or
smooth away genuine expression to manufacture a pass. Next localize c's reported
issue and distinguish original-voice movement from guide-only error. Full reference
and product qualification remain pending.

### C clarification: rhythmic singing and deliberate bends

The user clarifies that the questionable notes are in the **whistle guide**, with
gaps and timing mismatch making precise judgment difficult. C deliberately contains
rhythmic singing and pitch bending. Keep this as required expressive development
material, not an excluded outlier or evidence that the performance needs tuning.

The original guide uses approximately 85 ms centered windows and a hard ≥0.90
confidence cutoff. Those choices can average rapid changes and interrupt guide
audibility; they are a review-aid limitation, not an observed Voxide render/PDC
failure. Actual vocal F0 and intended-note reference truth are still unconfirmed.
Do not fix the comparison by quantizing the singer's bends or filling genuinely
unpitched gaps. A bounded shorter-window/soft-gating comparison was prepared,
with the original source, guide, proposals and failed observations retained. Any
analytic diagnostic concerns that aid only, not real-vocal or live product accuracy.

### Bounded C review-aid comparison — not promoted as a fix

Private evidence is under
`evaluation/pr-02/pilot-20261021T190851Z-2c1c71d8/c-review-002-20261022T175013Z-d6692c10/`.
`corpus-v002.json` retains all three development sources and tags C's user-confirmed
rhythm/bends, with unchanged source hashes and no holdout or completed references.

The comparison used 2,048-sample centered windows/240-sample hop, soft confidence/
RMS guide gain, and no gap filling or fixed-note snapping. The original aid uses
4,096/480 and a hard confidence gate. A private analytic rhythmic-bend/noise probe
compared those configurations and a conservative short-window gate. Raw results
at each configuration's grid are preserved; `common-grid-diagnostics.json` also
uses identical source sampling positions/denominators. These diagnostic statistics
include transitions and must not be substituted for the frozen stable-frame or
live timing gates. Sampling phase affects boundary/voicing statistics.

The softer aid retained more estimates but exposed suspicious pitch excursions on
actual C, including an approximately 4,307-cent adjacent estimate jump around
excerpt time 2.635 s at confidence approximately 0.76. This is not a verified
intended vocal note. Conservative gating reduced such output but retained a
timing/gap tradeoff. The candidate is explicitly **not promoted as a fix**; all
observations/variants remain private and unchanged for diagnosis. No further user
listening is requested on these unreliable guides. Parameter fitting or snapping
bends cannot replace independent/manual reference annotation for this case.

Original source audio, prior guides, all-uncertain human drafts, approved numerical
targets, repository implementation and synthetic expected assets are unchanged.
Only C's role/limitations and private diagnostic evidence were extended. Actual
reference pitch, expression-policy approval and all full human/product gates remain
pending; C is retained as required expressive material, not excluded to claim a pass.
