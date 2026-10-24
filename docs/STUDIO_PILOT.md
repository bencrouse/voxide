# PR06A — studio listening pilot preparation

**Status: a and the approved half-level c comparison have user feedback; both
yield only a small/non-decisive Rubber Band preference. No distracting artifacts
were reported on a; c was not separately rated for artifacts/bends. Signalsmith
is the provisional engineering lead. Formal qualification/selection stay pending.**
This is the execution/protocol note for `PROJECT_PLAN.md` PR06A, not a second
implementation plan. The versioned proposal JSON remains unchanged; a private,
hash-bound approval receipt authorizes only this trial, not formal qualification.

## Versioned scope and gate mapping

- `evidence/pr-06a/studio-scope.json` (`pr06a-studio-001`) records the confirmed
  studio/scale/±12/three-voice direction and retained technical gates. Historical
  PR02/03/05 contracts/protocols are bound by hash, not overwritten or regraded.
- `evidence/pr-06a/listening-protocol.json` (`pr06a-listening-001`) proposes one
  small, local, development-only comparison. Its original proposal status is frozen;
  the separate private receipt now records explicit approval of this exact trial.
- Correct pitches/expression, finite output, gain/headroom, duration, lead null,
  source-time alignment, reset/repeatability and the eventual callback/host gates
  remain. The complete declared studio delay remains ≤100 ms with accurate PDC.
- Live/MIDI/±24 qualification is deferred, not passed. The initial native-rate
  listen does not qualify both rates or the full E2–C6/±12 envelope.
- Human pitch truth, independent listening, recorded-onset/transition acceptance
  and a final processed-character/formant rubric remain pending. Old response
  targets and formant diagnostics stay visible; no replacement numerical threshold
  is approved. Informal preference is not a reference annotation or product score.

## Why these two candidates?

| Candidate | Reason to include | Why it is not already qualified |
| --- | --- | --- |
| Signalsmith 2048/512, existing Accelerate backend | Largest already-tested window; the retained native-consonant/scale/mix upper/lower subset delivered on the fixed 100 ms timeline at both rates with lead-null/tail/allocation checks passing | Pitch/formant and other quality observations remain negative or unresolved; actual-vocal timbre and general native repeatability remain unqualified |
| Rubber Band R3 short, existing settings | The same four-case scale subset delivered on the 100 ms timeline with lead-null/tail checks passing; an independently implemented timbral comparator | All those cases allocated on callbacks; reset and quality failures remain. Use fresh graphs, not the disqualified priming workaround. Offline preview is not AU acceptance |

Evidence is the corrected PR05 report
`build/interaction-research/20261023T160456Z-ffcc2998/report.json`:
Signalsmith cases 0136/0137/0396/0397 and Rubber Band cases 0188/0189/0448/0449.
Each candidate has four native-policy, scale-mode, 100 ms, upper/lower cases across
44.1/48 kHz. All four delivery/null/tail checks passed; **all four still have
sparse pitch misses**. These synthetic observations motivate a listen, not a
claim that the studio scope cures defects. The proposal archives the exact report
hash and all selected gate/pitch results, including failures.

No new window, FFT choice, dependency, upstream patch or consonant/formant ablation
is proposed. Rubber Band standard is not selected because its tracked 100 ms
delivery failures would confound the first comparison. Small live-oriented
Signalsmith presets are not selected to chase a latency requirement now deferred.

## Proposed first listen

- One existing, explicitly permitted **12-second development excerpt a**, native
  48 kHz, same source/time span for both engines. Consent/audio identity is bound
  privately; dryness remains provisional, no source repair/tuning/denoising.
- **C major diagnostic, explicitly selected by the user.** Do not infer the source
  key or claim this setting fits the performance or the Eno recording.
- The already-approved third/fifth/octave-above voicing: degrees `[2,4,0]`, octaves
  `[0,0,1]`, preserving continuous source deviation and disabling out-of-±12 targets.
  Native consonant treatment, existing formant preservation, no extra effects.
  Uncertain/unvoiced pitched targets must follow PR03's inactive-target policy.
- One attenuation-only source-derived scalar toward −24 dBFS RMS, never boosting
  a quieter source, identical for both candidates/dry/stems; lead unity and each
  harmony at 1/3. Preserve and null-check the lead against that scaled source.
- Aligned lead/three stems/complete sum and dry comparison; disclose exact 100 ms
  reserve and retain a 0.6-second supplied zero tail plus finish diagnostics.
  No per-candidate gain fitting, normalization, limiter, EQ or masking effect.
- Export playable files only after finite/lead-null/duration/provenance checks,
  no missing/late primary delivery and a conservative **0.5 peak ceiling** across
  intended previews. This is an additional preview guard, not a relaxed product
  threshold or a promise of headphone safety. Unsafe output is retained privately
  as a failure, not clipped into a playable success. Playback is never automatic.
- Ask preference/usefulness and timestamped articulation/stability/bend/rhythm
  defects. “Neither” is valid; no blind-study or independent-listener claim.
  User judgments do not produce F0 truth. Required c and both-rate boundary/control
  checks must follow under approval before progressing, with at most one diagnosed
  correction/retest. No holdout access or tuning sweep.

## Approval boundary and implementation gaps

Existing development excerpts have zero registered completed human annotations.
The old formal private evaluators therefore remain blocked, correctly. The pilot
uses an explicitly labeled **listening-only exception**: no formal pitch grade,
no fake oracle, exact permission/hash/protocol/trial binding, private evidence only.
**User approval was obtained before implementing the separate render route.**
It does not relax the existing preflight or unlock independent/holdout qualification.

Approval must name the source proposal, both candidates, settings, chosen key/scale
and the listening-only annotation exception. Approving preparation or liking the
album reference is not sufficient. It authorizes neither playback, AU installation,
Logic/device use nor a purchase/commit/merge/push.

The wrapper now exposes explicit shift-limit and inactive-uncertain controls;
historical defaults remain ±24/PR05-ablation behavior. The approved pilot selects
±12 and inactive uncertain targets, with native and transport boundary tests.
`--describe` attests current compiled identity/profile/capabilities before selected
audio access. `studio_listening.py` keeps this new route separate from formal
preflight and verifies fixed delivery, controls, lead null, tails, finite output,
fixed summing and peaks before any playable file is exported. Known callback
allocation/reset discrepancies stay failed product gates, not preview blockers
that are falsely marked passed. A single-use render claim prevents silent retries.

The private receipt is
`evaluation/pr-06a/proposal-20261024T143509Z-3ba459d6/approval.json`; it binds the
original proposal/public scope/protocol hashes, excerpt a, both candidates and
**C major diagnostic**. It grants no approval for c, other sources, another key,
automatic playback, installation or formal accuracy. Retain the proposal's earlier
pending flags as historical preparation, not the current receipt's approval state.

## Metadata-only preparation command

```sh
python3 scripts/studio_pilot.py \
  --development-corpus evaluation/your-existing-development-corpus/corpus.json \
  --source-index 0
```

Use only the specifically approved existing manifest, not a library search.
`studio_pilot.py` has **no render or playback command**. It validates public protocol
bindings, reads registered metadata and retained synthetic reports only, checks
development status/declared permission/contained path existence, and writes a new
private `evaluation/pr-06a/proposal-*/proposal.json`. It does **not** read/hash/decode
the audio payload or call the corpus-wide audio validator. The separate approved
render route performs source/hash/header checks at execution. Names/consent/source hashes remain in
the private proposal; stdout contains only its ignored path and approval status.

No preparation output may claim audio identity verified, an annotation exception
approved, a source key detected, a render authorized or product acceptance passed.

## Approved render command (never playback)

```sh
python3 scripts/studio_listening.py \
  --approval evaluation/pr-06a/proposal-20261024T143509Z-3ba459d6/approval.json
```

Run only after native Release/safety qualification. This consumes one explicit
initial-comparison claim; it is not a loop over recordings/settings. It preserves
raw failures privately and withholds the comparison if either candidate fails
export checks. Formal quality and callback/host acceptance remain separate.

## Preparation record — 2026-10-24

Historical pre-approval state; the approved render record below supersedes its
pending trial status, without rewriting those original artifacts.

- Metadata proposal: ignored
  `evaluation/pr-06a/proposal-20261024T143509Z-3ba459d6/proposal.json`.
  Scope/protocol hashes verified; source payload unread, declared identity not yet
  verified, zero registered annotations, key/scale and trial exception pending.
- All **126 Python regressions**, including six new preparation/privacy/protocol
  controls, passed with stable source at
  `build/studio-pilot-checks/20261024T143812Z-97f6080f/report.json`.
  This is not a native render, headphone-safety or product qualification check.
- Historical contracts and formal private evaluators are unchanged. No private
  render, audio playback, upload, host/device operation, installation or commit.

## Approved initial render — 2026-10-24

The user explicitly approved the listening-only annotation exception and selected
**C major diagnostic** before implementation/use. This is not the recording's
verified key, an annotation, independent listening or a new product go-decision.
The earlier proposal/preparation artifacts above remain unchanged.

- Full product Debug/Release/ASan/TSan regressions passed with stable source:
  `build/checks/20261024T151422Z-4b56080d/environment.json`. **131 Python tests**,
  including six preparation and five approved-render/export regression tests, pass.
- Isolated studio guard/safety qualification passed with stable source:
  `build/studio-native-checks/20261024T151422Z-d822e13c/report.json`.
  All seven native tests pass in Debug/Release/ASan/TSan, plus **16** synthetic
  native runs over both candidates, both rates and all profiles, exercising E2/C6,
  ±12/zero octave controls, uncertainty, and mixed callback partitions. Sanitized
  runs are safety checks, not native performance or pitch-quality qualification.
- Approved private comparison and full source/binary/build provenance:
  `evaluation/pr-06a/listening-20261024T151731Z-aecf92a7/report.json` and
  `provenance.json`. The exact selected source/header/hash and registered permission
  were revalidated. Only excerpt a was read/rendered; no other source or holdout.
  A post-render `archive-integrity.json` binds 246 retained artifacts, including
  the original corpus metadata snapshot; no extra audio rendering was performed.
- Both candidates passed export checks: finite output, exact duration, unchanged
  scaled lead null, fixed summing, declared controls, 100 ms fixed delivery with
  no missing/late primary samples, tail/metadata checks and the fixed preview peak
  ceiling. Neither candidate needed output fitting, limiting or a corrective rerun.
- **Nine local float WAVs** are indexed/hashes verified under that run's
  `previews/index.json`: one identical unprocessed aligned comparison, two complete
  blends, and three mix-gain harmony stems per engine. Each file is **12.6 seconds**,
  including 100 ms leading alignment and the supplied tail. No automatic playback.
- Signalsmith's captured callback allocation screen passed for this one render;
  Rubber Band's failed and remains explicitly failed. Actual-excerpt repeatability,
  source/target accuracy, full support, independent listening, Logic/PDC and the
  eventual callback/host qualification are **not** established by export checks.
  Dryness remains provisional as registered; the comparison is the supplied source,
  not a certified dry/studio-clean recording or a repaired one.

### User listening step

Open the **local** `previews/` directory above manually. Start with low headphone/
interface volume; passing digital peak checks is not a hearing-safety guarantee.
Listen first to `00-dry.wav`, then:

1. `signalsmith-2048-512-mix.wav`
2. `rubberband-r3-short-mix.wav`

The three `*-harmony-1/2/3.wav` stems are optional diagnostics at their fixed mix
gains, not separately normalized showcases. The common lead is not pitch-shifted.
No one has claimed the result matches “Bottomliners”; the assistant has not
auditioned these files or that reference passage. Report **which processed
character is useful, or neither**, plus rough timestamps of articulation, rhythm/
bend or unwanted note/stability problems. This is subjective development feedback,
not a formal pitch grade. Clip c, extra sources/settings and formal PR06B work remain
blocked on their respective approvals/evidence; do not silently extend this receipt.

Only documentation is updated after this source-stable qualification/render. No
new commit, merge, push, purchase, AU installation, Logic/device operation, capture
or playback occurred. The underlying PR05 defaults and historical evidence remain
intact; the new studio controls are explicit, not a hidden quality switch.

## Initial user feedback — 2026-10-24

In response to the presented comparison, the user preferred Rubber Band, described
the difference in terms interpreted as small/not decision-worthy, reported no
distracting artifacts and said the result sounds really good. Preserve the original
wording rather than inventing a numerical margin or rating: it is in the private
`user-feedback-001.json` beside the run report, bound to that report/index/mix hashes.
No defect timestamps, independent ratings, pitch truth, source-key verification or
explicit claim of matching the album passage were supplied. The archived run,
previews and original integrity manifest are unchanged; feedback is append-only.

**Interpretation:** the processed-character concept has a positive initial user
signal on this one excerpt. Treat Rubber Band as the current listening preference,
not an accepted engine. If the small difference is non-decisive, do not spend the
pilot's correction allowance manufacturing a more dramatic A/B or tuning away a
defect the user did not report. Earlier synthetic/live-scope failures do not mean
these previews necessarily sound bad for the newly chosen artistic objective.
Conversely, one favorable listen does not negate those measured failures.

The next decision should emphasize **engineering suitability**: callback/CPU
headroom, fresh/reset/repeat behavior, correct recorded-vocal timing/PDC and robust
±12 behavior on harder material, rather than an unneeded fine-grained preference
ranking. Known Rubber Band allocations and reset discrepancies remain blockers;
Signalsmith is still eligible for comparison if it offers a more reliable/lighter
implementation with acceptable sound. No winner or technical waiver is inferred.
Clip c/other sources and any new private render remain outside the consumed
excerpt-a receipt. Obtain explicit approval before extending the listening set;
PR06B and AU integration stay blocked on their actual requirements.

## Engineering suitability follow-up — fixed synthetic protocol

The user requested continuation of CPU/repeatability/reset comparison after the
positive listen. `evidence/pr-06a/engineering-protocol.json` freezes the bounded
comparison: only the same two configurations, both rates, callbacks 128/512,
two fresh processes per point, three captures/process (cold, stopped reconstruction,
warm-process fresh graph). The **16 invocations / 48 captures / 60 waveform
comparisons** are a synthetic engineering study, not another private listening set.

`scripts/studio_engineering.py` uses the isolated native `--engineering` probe.
That probe generates a fixed five-second harmonic/register/bend/noise workload plus
a supplied 0.6-second zero tail; **it accepts no input audio path**. It captures all
ten raw channels, input/control hashes, startup/body/tail callback metrics and
stopped setup/reset costs. Callback timing includes actual tracking/selection,
three shifters, bounded adaptation, preallocated capture and audit/hash overhead;
consumer formatting/files are outside the timed path. All cold/outlier callbacks
remain in the whole-run gates. Formal CPU measurements require optimized audited
Release and no concurrent qualification builds/profilers; they are not a Logic soak.

The stopped reset test uses the current wrapper's **graph reconstruction**, not
Rubber Band's already-failing native reset or a priming workaround. It compares
eventful output, not silence alone, and verifies finalized-stream restart rejection.
Off-render construction allocations/cost are recorded separately, never presented
as callback work or as an implemented audio-thread state-handoff solution. Any
actual AU transport/seek/reset handoff still needs its own design/qualification.

The comparison retains failures at every buffer/rate point. A failed smaller buffer
does not erase a passing larger one; no point certifies every host workload. Native
hashes must match before attributing differences to engine/state behavior, with
the original max 1e-6/RMS 1e-7 waveform limits and exact duration. No thresholds,
presets, FFT choices, engine sources or private approvals are changed.

Prior listening-run metadata is reviewed only in its ignored directory via
`retained-engineering-review-001.json`, without reading private audio. The existing
preview/source/approval artifacts remain unchanged. The native identity changes
for this added diagnostic code, not the historical archived preview/build identity.
Results and the bounded engineering recommendation follow below; no new private
render, clip-c access, playback, installation or final engine selection is implied.

### Engineering results — 2026-10-24

**Recommendation: advance Signalsmith 2048/512 as the provisional engineering
front-runner for the next approved harder-material test; retain Rubber Band as the
listening reference.** The user found both acceptable on excerpt a with a small
Rubber Band preference. Signalsmith's lower callback cost and zero observed
callback allocations now provide a stronger practical discriminator than further
fine-grained timbre ranking. This is not final selection or a PR06B/product go.

Final evidence:
- Product Debug/Release/ASan/TSan and **136 Python regressions**, including five
  new engineering result/negative-control tests, pass with stable source:
  `build/checks/20261024T173235Z-bc6e8e1b/environment.json`.
- Isolated safety qualification passes with stable source:
  `build/studio-engineering-checks/20261024T173235Z-93c09625/report.json`.
  Seven native tests/profile plus the new probe on both candidates in all four
  profiles exercise eventful reconstruction, fresh graphs and restart rejection.
  Debug/sanitized timing is not used as performance evidence.
- After those builds/tests finished, the sequential optimized audited Release
  comparison completed at `build/studio-engineering/20261024T173710Z-7dee2ad8/report.json`.
  **16/16 invocations, 48/48 captures, 60/60 waveform comparisons** completed;
  source/build identity stayed unchanged. `provenance.json` archives exact
  source/binaries/runtime/build metadata and canonical dependency identities;
  `artifacts.json` binds all retained raw outputs, telemetry and analyses.

Each table cell is the **worst per-capture p99.9 callback occupancy** across both
processes and cold/reconstructed/warm-fresh captures. This is a fraction of each
virtual callback's deadline, including the declared instrumentation—not overall
Logic CPU usage, an algorithmic latency measurement or universal realtime proof.

| Engine / samples | Rate | Callback | Worst p99.9 occupancy | Callback allocations across six captures |
| --- | ---: | ---: | ---: | ---: |
| Signalsmith 2048/512 | 44.1 kHz | 128 | 9.64% | 0 |
| Signalsmith 2048/512 | 44.1 kHz | 512 | 5.26% | 0 |
| Signalsmith 2048/512 | 48 kHz | 128 | 9.38% | 0 |
| Signalsmith 2048/512 | 48 kHz | 512 | 3.64% | 0 |
| Rubber Band R3 short | 44.1 kHz | 128 | 16.73% | 630 |
| Rubber Band R3 short | 44.1 kHz | 512 | 9.20% | 630 |
| Rubber Band R3 short | 48 kHz | 128 | 19.77% | 618 |
| Rubber Band R3 short | 48 kHz | 512 | 9.11% | 618 |

- Both candidates meet the provisional occupancy/zero-overdue screen **on this
  workload/run**. Largest individual occupancies are approximately 12.85%
  Signalsmith / 21.23% Rubber Band. No overdue callback was observed.
- Signalsmith has **zero callback allocations in all 24 captures**. Rubber Band
  allocates in **all 24**, 103–105 calls/capture, **2,496 total**: 2,436 during the
  declared startup interval and 60 in the voiced body. Silence/tail has none.
  Thus merely excluding initialization observations would still hide dynamic
  allocations; none are discarded or reclassified as a pass.
- Each candidate passes **30/30** waveform comparisons: stopped reconstruction,
  warm-process fresh construction, reconstructed-vs-fresh, independent process,
  and 128/512 callback partition comparisons. All ten channels are **exactly equal**
  in this set (maximum and RMS differences zero), with matching native input/control
  hashes and complete durations. Delivery, lead-null, tail and uncertainty/range
  telemetry checks pass for all 48 captures.
- All 16 attempted post-finalization cold-graph restarts are rejected. Stopped reconstruction is
  intentionally allocating: Signalsmith 316 calls and approximately 0.637–0.698 ms;
  Rubber Band 4,360–4,726 calls and approximately 0.914–0.972 ms across these trials.
  These are **off-render** operations, not zero-allocation reset or a demonstrated
  realtime host state-handoff solution.

**Important reset distinction:** both engines are reliable here under **fresh
graph reconstruction**. This does not fix/qualify Rubber Band's native `reset()`.
Historical direct-native dynamic reset observations remain retained (including
Rubber Band overlap errors), with the documented old-wrapper diagnostic-I/O caveat
on its timing/allocation metrics. Do not conflate a passing wrapper lifecycle with
a repaired upstream reset, or continue calling the current stopped policy a failed
reset solely because the unused native API failed earlier.

Exploratory helper validation before qualification is retained at
`build/studio-engineering-smoke/20261024T172904Z-db2bda8a/`; it is not substituted
for the declared Release matrix. No corrective/tuning cycle or private render was
performed in this follow-up. Historical pilot previews, approvals, feedback and
their archived source/binary identities remain unchanged.

At the engineering checkpoint, the next step was explicit permission for clip c's
expressive/recorded-vocal check. That permission has subsequently been obtained
as recorded below. The consumed a-only receipt still cannot authorize it.
Actual-vocal repeatability/full ±12 coverage, formal reference/listening criteria,
audio-thread transport/reset handling, Logic/PDC/bounce and a representative soak
remain pending. Source code has been self-reviewed/automatically checked, not
independently code-reviewed; only completion documentation changes after the run.

## Clip-c follow-up — approval and source boundary

On 2026-10-24 the user explicitly approved the requested follow-up: **clip c, both
existing candidates, unchanged diagnostic C-major/third-fifth-octave settings,
listening-only without pitch annotations or automatic playback**. This checks
the required rhythmic/bending challenge without flattening it; it is not another
configuration search, numerical F0 truth or a final engine/PR06B decision.

`evidence/pr-06a/clip-c-protocol.json` (`pr06a-clip-c-001`) is an additive extension
bound to the original scope/protocol hashes. Those files, the a approval/claim,
previews and feedback are unchanged. A separately bound **approval.v2** receipt
under ignored `evaluation/pr-06a/proposal-20261024T175942Z-f54d123d/approval.json`
authorizes only registered development source index 2. An approval.v1 receipt
continues to authorize only a; changing an index or reusing a consumed claim is
rejected before audio access. Other sources, keys, voicings and holdout remain
unapproved. This changes only source authorization, not DSP/gains/safety limits.

The new private proposal was prepared from metadata only, after verifying the
original corpus identity and c's registered rhythmic/pitch-bend tags. Actual source
payload/hash/header checks occur only in the approved render route. Regression
tests cover the version/source boundary, extension binding and consumed receipts.
The authorization-only change passes the full source-stable product qualification
at `build/checks/20261024T180129Z-236f32fa/environment.json`, including **139 Python
tests** and three new source/version/single-use receipt regressions. All seven
Release native tests pass; native binaries are byte-identical to the previously
qualified four-profile engineering build. No DSP/gain/configuration change.

### Initial clip-c render withheld — 2026-10-24

The approved comparison ran once at ignored
`evaluation/pr-06a/listening-20261024T180305Z-d5b0ddb2/report.json`, with source/build
provenance verified before/after. Both native renders complete with finite outputs
and no missing/late delivery, invalid controls, lost telemetry or nonzero finish
tail. Signalsmith passes all preview checks. Rubber Band's **complete blend exceeds
the predeclared 0.5 preview-peak ceiling**, so the two-candidate preview package is
withheld. No preview directory is published and nothing is played automatically.

Retained-output inspection confirms no digital full-scale overs in the intended
dry/mix/mix-gain-stem previews. The stricter ceiling is an additional playback
margin; crossing it is **not evidence of clipping or an artistic failure**. Exact
source-derived peaks stay privately in `export-diagnostics.json`; do not normalize
Rubber Band alone or classify an unheard artifact as confirmed. The original
report/raw outputs, corpus snapshot and 243 artifact hashes are preserved unchanged
in `archive-integrity.json`. No correction/re-render or output-gain modification.

The next approval choice offered was a fixed common **0.5 playback scalar** applied equally to
dry, both blends and all stems from the retained outputs (no DSP re-render, limiter,
per-candidate normalization or altered relative mix), or an explicitly partial
Signalsmith-only export, or continued withholding. The user selected the common
half-level option, as recorded below; the original blocked comparison stays blocked.
At that checkpoint clip-c preference/defect feedback and formal qualification
remained pending; subsequent feedback is recorded below.

### Approved retained-output half-level export — 2026-10-24

The user explicitly chose **“Half-level export (Recommended)”**: retained dry, both
mixes and all stems at one fixed common **0.5 playback scalar**, with no DSP rerender,
limiter, per-engine normalization or changed relative mix. The additive
`evidence/pr-06a/half-level-export-protocol.json` and private receipt
`evaluation/pr-06a/playback-approval-20261024T183423Z-5262510a/approval.json` bind this
amendment to the original clip-c report, 243-artifact archive and consumed render claim.
No original authorization, claim, report, raw output or protocol is rewritten.

`scripts/studio_playback_export.py` accepts only this fixed playback export and has
no native execution or playback path. It checks the complete bound archive,
historical source/binary snapshots and compiled identity (not today's source
identity), archived source/consent and exact source attenuation. It rechecks all
ten channels, controls, delivery, duration, aligned lead null, fixed mix and finish
tail before either candidate is exported. Untrimmed intended previews must remain
strictly below full scale; the common half-level previews must meet the unchanged
**0.5** peak ceiling. Raw native stems remain non-playable research outputs.

The separate exclusive export claim is keyed by original report plus amendment,
so copying the receipt elsewhere cannot authorize another export. Claims are
consumed before audio reads and preserved even on failure. Regression tests cover
common attenuation, original failure retention, full-scale/nonfinite/delivery and
fixed-sum rejection, arbitrary/per-candidate gains, artifact/receipt tampering,
single-use/copied receipts, all-or-nothing publication and a synthetic complete
export that rejects any attempt to execute DSP. No new source rendering or
automatic playback is authorized.

**Completed:** the source-stable full product Debug/Release/ASan/TSan checks pass at
`build/checks/20261024T183649Z-e1476dbc/environment.json`, including **148 Python
tests** (nine new playback-export regressions). Native DSP binaries remain
byte-identical to the previously four-profile-qualified engineering build.

The single-use retained-output export completed at ignored
`evaluation/pr-06a/playback-half-20261024T183809Z-647c08bb/`:
- `previews/index.json` identifies **nine** hash-verified IEEE-float mono 48 kHz
  WAVs: one shared aligned dry, two mixes and six mix-gain harmony stems.
  Every file is **604,800 frames / 12.6 seconds**, including the original tail.
- `export-validation.json` verifies every sample against the retained output at
  exactly the same common **0.5** playback factor. All samples are finite, all
  intended previews meet the unchanged 0.5 ceiling, and the post-trim fixed mix
  still equals dry plus the three harmony stems within the original tolerance.
  Original aligned-lead null, native controls/delivery and tail checks pass for
  both candidates. Exact source-derived peaks remain private.
- All **243 original artifact hashes**, the original archive/report and consumed
  render claim verify unchanged; no `previews/` was added to the withheld run.
  `raw-identities.json`, the archived export implementation/tests/amendment,
  qualification bindings and `package-integrity.json` retain the additive chain.
  The separate export claim is consumed; no DSP was rerun or audio played.
- This is a safe-export result only. Rubber Band callback allocations remain a
  failed engineering gate; pitch accuracy, artistic preference, independent/formal
  listening, actual-vocal repeatability and Logic/PDC/bounce are not newly passed.

For **manual low-volume** listening, open the new `previews/` folder, starting with
`00-dry.wav`, then `signalsmith-2048-512-mix.wav` and
`rubberband-r3-short-mix.wav`. These mixes have the **same** playback trim; do not
normalize them independently. Listen for rhythmic articulation, retained bends,
wrong/unstable notes and distracting texture; report candidate preference (or
neither), usefulness and timestamps of defects. Subsequent user feedback follows;
the assistant has not auditioned these files. No commit/merge/push or product go.

### Clip-c user feedback — 2026-10-24

The user again tentatively prefers **Rubber Band**, but explicitly calls the sonic
difference **minimal** and does not care which engine is chosen from a subjective
sound standpoint. Record this as a **non-decisive preference**, not a reason for
further fine-grained A/B tuning or a mandate to choose Rubber Band. The private
append-only `user-feedback-001.json` beside the half-level package binds the exact
statement to its report, preview index, package integrity and both mix hashes.
All existing package and original-run artifacts remain unchanged.

This statement does not separately rate artifacts, note accuracy, articulation or
preserved bends; no timestamps/numeric ratings were supplied. Do not carry the
excerpt-a “no distracting artifacts” report forward as a new clip-c assertion.
The listener is the user, unblinded and not independent; no formal pitch/timbre
acceptance is inferred.

**Engineering implication:** sound does not discriminate strongly enough here to
override Signalsmith's lower measured callback cost and zero observed callback
allocations. Keep Signalsmith 2048/512 as the provisional engineering front-runner
and Rubber Band as the sonic reference; final selection and PR06B go remain open.
The next work should consolidate remaining ±12/support/timing, repeatability and
host qualification gaps and a bounded verification proposal, not another tiny
preference comparison. Any additional private render needs its own authorization;
this feedback authorizes no automatic rerender, tuning, install or integration.

### Next verification proposal — 2026-10-24

The user asked to continue **defining** the bounded tests. The retained-evidence
gap review and staged proposal are in [STUDIO_VERIFICATION.md](STUDIO_VERIFICATION.md)
and `evidence/pr-06a/signalsmith-verification-proposal.json`. This is planning,
not an execution receipt or product/host authorization.

The first blocker is pitch-error attribution: all 12 voice/case groups in the four
historical Signalsmith scale/mix cases miss the sparse stable-pitch target, despite
passing delivery. Their observer/short-region and historical-guard limitations
remain explicit; they are neither regraded as current studio failures nor erased.
Proposed Stage A calibrates the meter before matching analytic prescribed versus
tracked output, then checks eventful delivery: **36 measurement fixtures and at
most 88 native captures**, no tuning or private audio. Separate stages propose
source-bound actual-vocal repeatability and a separately authorized evaluation-host
route, without unblocking product integration. No new DSP/private renders, playback,
installation, source searches or Logic operation occurred in this planning step.

### Independent tooling review — 2026-10-24

After the user approved synthetic-only execution, it was paused for a fresh-agent
review in the requested bottom-right Herdr pane. The
[review record](evidence/pr-06a/review-001.md) lists five independently reproduced
tooling defects: listening-receipt replay, proposal-output symlink containment,
telemetry completeness, self-declared engineering duration and unchecked fixed
sums. These must be repaired/regressed and the fixes reviewed before Stage A.
The reviewer ran 28 existing studio tests successfully; their missing negative
cases explain why passing tests did not reveal these defects. Neither reviewer nor
main agent accessed private audio, ran native DSP or changed implementation files.
No retained-audio corruption, audible defect or engine-selection reversal is
established. Historical evidence/approvals remain unchanged; no fixes applied yet.

### Tooling repair closure — 2026-10-24

The user requested repairs. All five findings, including follow-up legacy-relocation
and backdated-packet edge cases, are now regressed and closed by the read-only
reviewer. The [repair record](evidence/pr-06a/review-fixes-001.md) documents the
implementation and limits. **45 studio tests / 165 Python tests** and full product
Debug/Release/ASan/TSan pass at `build/checks/20261024T194129Z-dff8fbbe/environment.json`.
Retained synthetic revalidation passes new checks for 48 captures/four guard
timelines; original synthetic evidence and Rubber Band allocation failures stay
unchanged. Final evidence/code snapshots are under
`build/studio-review-fixes/20261024T194145Z-23a3bc59/`. No engine DSP/parameter change,
private payload read, rerender, playback or host operation occurred. The existing
synthetic-only Stage A approval can now be used for its bounded implementation and
calibration; no Stage A execution, final engine selection or PR06B go yet.
