# Voxide decisions

## PR 00

- **Budget/license:** user explicitly chose local-only use for now in the licensing
  clarification. Use JUCE's AGPLv3 option; do not buy a license or publish binaries/
  source. Revisit obligations before sharing. No broad Voxide publication license
  is declared by this bootstrap.
- **Profile:** native arm64, macOS 15 deployment, C++20, CMake 3.24+, JUCE 8.0.15
  matching the inspected Nitride pin. This is a build profile, not certification
  that macOS 15 or all Apple Silicon devices have been tested.
- **Identity:** product `voxide`, version `0.0.1`, bundle `com.voxide.audio.voxide`,
  AU type `aumf`, subtype `Vx00`, manufacturer `Vxid`. Not Nitride's identity.
- **Signal contract:** default mono main input, optional disabled-by-default
  mono/stereo sidechain, stereo output. Stereo main input is also accepted for host
  compatibility. Explicit `sourceBus` choice selects Main input (default) or Sidechain;
  channel 1 is the mono source in normal and bypass processing. Do not infer a
  connection from enablement or signal level: AU enables every bus. Explicit
  zero-latency pass-through; no harmony generation or MIDI response yet.
- **State:** shell-v2 persists the routing choice; the previous stateless shell-v1
  restores the safe Main input default. Unknown/malformed state leaves the current
  choice unchanged. Parameter ID `sourceBus`, version hint 1, values Main/Sidechain
  (normalized 0/1); installed AU reported numeric ID `449045605`. Retain its meaning
  in later product work.
- **Targets:** AU product shell, development Standalone, independent DSP target,
  shared actual processor tests. No installed-host or Logic behavior inferred from
  processor tests; Logic proof belongs to PR 01.
- **Dependencies:** own verified archive cache plus explicit clean checkout option.
  Extracted source must match an archive-derived content manifest on every configure;
  mismatches preserve local edits and require a fresh tree. No sibling dependency
  discovery. Python evaluation packages and DSP engines are
  deferred to their scoped PRs; standard-library scripts need no package lockfile.
- **Safety:** no install/device access in ordinary checks. Explicit installer
  requires matching identity/ownership, refuses edited bundles/symlinks, preserves
  previous owned builds, revalidates after signing, and uses Darwin exclusive renames.
  Conflicting external changes are preserved rather than deleted during rollback.
  No paid signing/notarization. Standalone microphone privacy metadata supports a
  future explicit/manual capture test; no device is opened by ordinary checks.
- **Scope:** use Nitride as a read-only reference, not copied code. Minimal editor
  labels the build as a shell and exposes only the necessary routing choice; no
  new musical features or harmonizer claims.

## PR 01

- **Workflow:** user approved ending scripted Logic UI operation. Native built-AU
  and production-processor tests are the development loop; a reusable human Logic
  checklist is separate acceptance. No automatic project generation, DAW launch,
  recording, UI permission changes, or actual hardware input in ordinary checks.
- **Diagnostics:** version 0.1.0 / routing-003, fixed 2,048-record SPSC queue and at
  most 64 inspected MIDI records/three bytes each per callback. Consumer-side JSONL
  writing is opt-in, local/ignored, stops on editor close, and is never persisted.
  Retain original sample offsets (including invalid values) rather than normalize
  bad host data into apparently valid evidence. Loss/unknown note state is explicit.
- **Identity/state:** `sourceBus` and shell-v2 persistence remain unchanged. Render
  epochs reset on prepare/reset; observed held-key diagnostics also clear on
  stop/seek discontinuities. UUID identifies
  the current processor instance and is not serialized. No harmony synthesis added.
- **Evidence:** actual AU tests can assert buffer routing, host-callback use,
  fresh-instance state and MIDI API acceptance. Exact delivered MIDI offsets are
  asserted in the production processor, not falsely reported as observed inside
  the opaque native AU. Logic delivery still needs a real capture.
- **Host gates:** the agent's abandoned automation reached only an unsaved empty
  project's New Track sheet and performed no capture/monitoring. Subsequent user
  testing supports direct physical-input monitoring with Low Latency Mode off/on
  and save/quit/reopen; the track-fed mode limitation and remaining checks are in
  `docs/ROUTING_VALIDATION.md`. No external-controller qualification is claimed.
- **Discovery:** initial `auval` returned success while reporting cached 0.0.1 for
  the installed 0.1.0 bundle. This is not a discovery pass; validation now checks
  the reported version. No broad cache reset/registrar kill is permitted.
- **Review hardening:** stage MIDI only on the consumer until its matching audio
  summary; report/discard a partial tail at capture stop. Use checked unbuffered
  JSONL writes to detect short writes. Include prior truncation counts in MIDI
  records. Analysis has explicit note-pair and final-release requirements rather
  than treating arbitrary MIDI traffic as evidence of note-on/off delivery.

## PR 02

- **Numerical contract:** user accepted the plan's numerical targets on 2026-10-21,
  requesting **±24 semitones**, not the original ±12. E2–C6 input, 44.1/48 kHz and
  all three harmony voices remain required. Mathematical output endpoints are
  approximately 20.60–4,186.01 Hz. No automatic reduction if engines fail; no claim
  of achieved performance. Contract and reports are versioned/hashed.
- **Boundary:** only offline evaluation tooling, analytic assets and protocols;
  no production tracking, musical mapping, harmony synthesis or engine integration.
  Musical/source behavior and new listening/protocol details remain unapproved.
- **Dependencies/privacy:** standard-library Python only. No package installation,
  download, audio-library scan, recording, AU install or DAW automation. Private
  recordings/consent/reviewer identities never enter Git. The user offered resources
  but had not supplied locations, usage references or reviewer IDs at engineering
  qualification. Subsequently the user supplied three private AIFF pilots and
  explicitly approved local mono copies/excerpts. Original hashes and PCM samples
  are preserved. The user confirms one singer, solo and untuned; dry status remains
  provisional and actual reviewer IDs remain pending. See the private pilot intake
  record in `docs/EVALUATION_VALIDATION.md`.
- **Evidence:** candidate-independent analytic references; ordinary tests never
  rewrite them. Positive controls and deliberate pitch/octave/resonance/delay faults
  exercise measurements. PCM output is decoded before null comparison. Missing
  observations, all-uncertain references, missing listeners or corpus inputs cannot
  become a pass. Offline autocorrelation is not a live tracker or human pitch truth.
- **Holdout:** singer-separated splits, exact source/annotation/settings hashes,
  explicit complete-corpus/settings approval and opt-in access. Metadata QA is not
  candidate tuning; this is a workflow guard rather than file access security.
- **Independent review hardening:** v2 control/annotation metadata binds the source
  PCM/timebase; all 28 WAV bytes remain unchanged. Analytic burst/silence onset
  references were explicitly corrected under generator v2, not regenerated from
  candidate output. Shared contract policy governs grading and all holdout approval
  prerequisites; `pr02-contract-002` changes no approved numerical targets and
  leaves all outstanding protocol/resource approvals pending. See the review
  record and final qualification in `docs/EVALUATION_VALIDATION.md`.
- **Sequencing revision (2026-10-22):** user approved committing/merging PR 02's
  reviewed engineering foundation and deferring detailed manual annotations to
  actual tracker development. This explicitly permits PR 03 implementation without
  pretending the human gates passed. Numerical targets, independent reference/
  listening requirements, holdout locks and final qualification gates are unchanged;
  remaining musical semantics are not implicitly approved by this merge.

## PR 03

- **Approved musical defaults (2026-10-22):** user accepted scale third/fifth/octave
  defaults, continuous scale-source expression with hysteresis, absolute MIDI
  newest-three/stable-slot targets with repeat counts/sustain, inactive uncertain
  targets, unchanged lead and disabling rather than clamping out-of-range shifts.
  User additionally requested broad exotic scales. Implemented 41 built-in 12-TET
  sets plus any custom pitch-class set and all roots; do not claim microtonal/raga/
  maqam completeness. Octaves are independent of degree cardinality. See the
  versioned `docs/evidence/pr-03/musical-contract.json` and `docs/TRACKING.md`.
- **Algorithm boundary:** fixed-storage causal YIN baseline and bounded
  multi-candidate variant; no offline Viterbi, future context or correction of lead.
  Thresholds/hysteresis/window constants are engineering choices, not perceptually
  approved numbers. Multi-candidate is an experimental default, not a proven winner.
- **Research versus acceptance:** final candidate analytic stable-frame results do
  not establish actual vocal accuracy. Recognition timing misses remain architecture
  blockers. All permitted development vocals, including rhythmic/bending c, remain
  required and ungraded without human reference truth; no holdout or live-quality
  gate is unlocked. No new dependencies, purchase, install, recording or Logic use.
- **Engineering/research merge approval (2026-10-22):** after independent review,
  fixes, rereviews and full qualification, the user approved a local commit and
  merge of PR 03. Recognition timing misses and deferred reference/listening/Logic
  gates remain open; this is not architecture or product acceptance. Nothing is
  pushed or installed, and private evaluation data remains excluded from Git.

## Studio-first direction — user clarification, 2026-10-24

This is a **product-priority and artistic-direction decision**, not a new engine
selection, passing qualification report or authorization to execute audio/host work.
The implementation checklist remains `docs/PROJECT_PLAN.md`; this entry records
why that checklist changes rather than creating a competing plan.

### Confirmed in conversation

- **First useful workflow:** processing recorded vocals is a higher priority than
  harmonies while singing live. Live remains a later goal, not a solved or cancelled
  requirement. A clearly labeled studio milestone may now be pursued separately
  from the original combined live/mixing brief.
- **First musical mode:** scale mode, with user-selected key/scale. MIDI mode is
  deferred for the first milestone; retain its existing implementation/state and
  evidence, without promising it is qualified or deleting compatibility.
- **Minimum shift range:** inclusive **−12 to +12 semitones per harmony**; a smaller
  supported range is unacceptable. Prior ±24 coverage becomes deferred rather
  than silently inherited as achieved support. Input E2–C6, 44.1/48 kHz, exactly
  three available generated voices and an unchanged original lead are retained.
  For ±12, mathematical output endpoints are approximately 41.2–2093 Hz.
- **Artistic reference:** Brian Eno, *Another Day on Earth*, “Bottomliners,”
  approximately **1:30–2:00**. The user primarily values the **processed vocal
  character**, rather than the particular harmony note choices. The user's
  association with the DigiTech Vocalist is context, not independently verified
  gear provenance or an algorithm-recreation requirement. The assistant has not
  auditioned or analyzed the cited passage; do not invent its voicings/settings.
- **Timbre goal:** an appealing, intentional electronic harmony texture is welcome;
  three indistinguishable human backing singers are not the first objective.
  This does not authorize wrong pitches, flattened intentional bends, damaged
  articulation, clicks, bursts, unstable output or nonfinite samples. It does not
  authorize processing/tuning the original lead or adding a masking effects suite.
- **Next milestone:** a small studio-first listening prototype before further
  product features or a large new matrix. Compare actual sound and objective
  diagnostics, not synthetic scores alone. A preferred demonstration is not
  formal acceptance or an automatic go for AU integration.

### Retained boundaries and unresolved protocol work

- Zero spend, existing pinned engine families, privacy/consent, no automatic key
  detection, explicit source-time alignment, controlled gain/headroom and honest
  evidence remain. No new engine, upstream patch, package, purchase or install is
  authorized by this clarification.
- Retain the existing **≤100 ms complete studio processing ceiling and accurate
  PDC** as the planning budget; no greater delay is approved. This is not permission
  to conceal late/wrong notes or imply an acceptable physical monitoring route.
  Live processing/monitoring and MIDI response gates are deferred, not passed.
  Recorded-vocal onset/transition correctness still needs explicit assessment;
  do not silently replace the original response thresholds with new ones.
- The original PR02 contract, PR03 musical contract, frozen fixtures, protocols
  and all PR03–05/architecture results remain immutable historical baselines.
  Existing tools still grade their original contract. They do **not** implement
  or certify the revised studio scope merely because this decision is documented.
- Before a new trial, PR06A must version the studio scope and declare which gates
  are unchanged, deferred, or pending protocol approval. Pitch/correctness, safety,
  repeatability, host and callback requirements are not waived. Naturalness and
  strict formant-preservation scoring must be reviewed explicitly for this artistic
  target; no new numerical timbre threshold or formant-changing algorithm is
  approved here, and coloration cannot be used to excuse a defective shift.
- A **development listening-only** route without completed pitch annotations is a
  proposed protocol, not an implemented exception to existing private preflight.
  Approve its source selection, permission/hash binding, safe playback preparation
  and evidence labels before any private render or playback. Such preferences
  would not provide F0 truth, independent ratings or holdout acceptance. Formal
  pitch claims still require trustworthy references; missing references stay pending.
- Required expressive/rhythmic clip c remains in development assessment once the
  relevant protocol is approved; do not exclude it, flatten bends, invent annotations
  or open the holdout for the pilot. All private derivatives remain under ignored
  `evaluation/`. No commercial reference audio is to be copied into the repository.

### Consequence for sequencing

Keep PRs 00–05 and the bounded architecture investigation as research milestones
with their negative results intact. Split PR06 into **06A studio timbre/feasibility
pilot** and **06B versioned studio qualification/architecture decision**. PR07 AU
integration stays blocked until 06B's explicit user-approved studio go. PR08–10
then qualify and label the recorded-vocal scale workflow, not the full original
live/MIDI/±24 product. No engine or treatment has been selected, no prototype has
been heard, and no new acceptance, implementation or commit is implied by this
documentation update.

### PR06A preparation — proposed, not yet approved or rendered

On 2026-10-24, prepared versioned `pr06a-studio-001` / `pr06a-listening-001`
proposals under `docs/evidence/pr-06a/`. Candidate proposal: existing Signalsmith
2048/512 and Rubber Band R3 short, native consonant handling and unchanged formant
settings, 100 ms aligned reserve and the approved third/fifth/octave voicing.
Both have retained 100 ms scale-subset delivery passes **and** quality failures;
Rubber Band callback allocations/reset issues remain blockers, not exceptions.

Initial source proposal is the existing permitted 12-second development excerpt a
at native 48 kHz; exact identity/consent/hash and retained evidence are in ignored
`evaluation/pr-06a/proposal-*/proposal.json`, not public JSON. Key/scale is still
user-selected/pending. Preparation reads corpus metadata and synthetic reports
only, not the audio payload or annotation templates. No source identity has been
verified by decoding, no listening-only exception is approved, and no renderer,
playback or formal vocal grade is implemented by that proposal. Current formal
preflight and all historical contracts stay unchanged. See `docs/STUDIO_PILOT.md`.

**Subsequent explicit approval (2026-10-24):** in the interactive trial question,
the user chose “Approve pilot” and “C major diagnostic.” This authorizes the
exact excerpt-a/two-candidate/100 ms/three-harmony listening-only comparison,
including unannotated preference rendering, **after** implementation/safety checks.
The receipt under ignored `evaluation/pr-06a/proposal-20261024T143509Z-3ba459d6/`
binds proposal/scope/protocol hashes and the diagnostic key. It is not a claim that
C major matches the recording. No other source (including c), playback, installation,
holdout use, formal accuracy or product go is authorized. The proposal JSON remains
immutable; the separate receipt records approval. Existing formal preflight is unchanged.

**Initial comparison executed after safety checks:** both candidates produced
previews passing finite/level/null/control/delivery/tail export checks at ignored
`evaluation/pr-06a/listening-20261024T151731Z-aecf92a7/`. No corrective private
rerender, automatic playback or other source access occurred. The nine preview
files are for manual development preference only; no human F0 grade, independent
listening or actual-excerpt repeatability is claimed. Rubber Band callback
allocations remain failed, not waived by the file preview. User feedback, c,
complete range/formal qualification and product go remain pending. Full validation
and reproduction notes are in `docs/STUDIO_PILOT.md`.

**Initial subjective feedback (2026-10-24):** the user prefers Rubber Band, with
wording interpreted as a small/non-decisive difference, reports no distracting
artifacts on this comparison, and says the result sounds really good. The exact
wording is preserved privately with report/preview bindings; no numeric rating or
defect timestamps are invented. Both the positive artistic signal and the known
technical failures stand. Do not spend more effort exaggerating a small sonic
difference; prioritize engineering suitability before selecting an engine. This
is not independent qualification, a technical waiver, approval for c/other renders
or a go for AU integration.

**Bounded engineering follow-up (2026-10-24):** user requested continuation of CPU,
repeatability and reset assessment. The fixed synthetic comparison at
`build/studio-engineering/20261024T173710Z-7dee2ad8/report.json` completes 16
invocations/48 captures/60 exact waveform comparisons. Both pass the observed
callback-budget and stopped-reconstruction/repeat screens, with no overdue callback.
Signalsmith 2048/512 has zero callback allocations and lower observed callback cost;
Rubber Band R3 short allocates in every capture (2,496 calls total). This supports
**Signalsmith as a provisional engineering front-runner for further tests**, not a
final engine or PR06B go. Keep Rubber Band as the user's listening preference/reference.
Passing stopped graph reconstruction does not repair or qualify native `reset()`
or audio-thread host handoff. No sound tuning, extra private audio access/render,
clip-c permission, install, playback, upstream patch or commit is inferred. Seek
explicit clip-c approval before the next listening step. Full methods, caveats,
qualification paths and per-point CPU results are in `docs/STUDIO_PILOT.md`.

**Clip-c follow-up approval (2026-10-24):** after reviewing the synthetic engineering
results, the user explicitly said yes to the same two-candidate comparison on
clip c, diagnostic C major, listening-only without annotations or automatic playback.
The additive `pr06a-clip-c-001` protocol and a new private approval.v2 receipt bind
the original settings plus registered development source index 2. Original a
artifacts/consumed claim and public scope/protocol are immutable; the v1 receipt
does not acquire permission for c. Formal F0/independent listening and engine go
remain pending. No additional sources, key detection, DSP/preset change, flattened
bends, playback, installation, holdout, commit/merge/push or acceptance is implied.

**Clip-c initial execution:** both native runs complete with finite output and
intact delivery/provenance, but the Rubber Band mix exceeds the conservative 0.5
preview ceiling. No intended preview reaches digital full scale; this is not a
confirmed clipping/artifact defect. The package is withheld and the original
source-specific report, raw outputs and diagnostics stay unchanged under ignored
`evaluation/pr-06a/listening-20261024T180305Z-d5b0ddb2/`. No output repair, gain change,
private rerender or automatic playback occurred. A common fixed half-level export
or partial Signalsmith-only export requires the next explicit user approval;
formal quality/engine selection is not inferred from this guard outcome.

**Clip-c playback-export amendment (2026-10-24):** the user selected **Half-level
export (Recommended)**: apply exactly one common 0.5 playback scalar to retained
dry, both complete mixes and all mix-gain harmony stems. No DSP rerender, limiter,
per-engine normalization, altered relative mix or changed 0.5 preview ceiling.
`pr06a-clip-c-half-level-001` and a separate private hash-bound approval authorize
only an additive retained-output package; the original failed export result,
raws, consumed render claim and historical protocols remain unchanged. Preserve
nonfinite/full-scale/delivery/provenance failures; the amendment is not a formal
quality or engineering waiver. No automatic playback, new sources, commit or go.

**Half-level export completed:** the separate retained-output package at ignored
`evaluation/pr-06a/playback-half-20261024T183809Z-647c08bb/` contains nine verified
12.6-second previews at the identical common 0.5 playback scalar. Both candidates
pass the export guards at this playback level; the original withheld run and all
243 original artifact hashes are unchanged. Full checks/148 Python tests pass;
native binaries are unchanged. No DSP rerender, automatic playback or independent
listening occurred. Next is manual clip-c user feedback, not a new rendering loop
or product go. Rubber Band callback allocations and all pending formal/host gates
remain separately failed/pending.

**Clip-c subjective feedback (2026-10-24):** the user tentatively prefers Rubber
Band again, but explicitly considers the difference minimal and does not care
which engine is selected from a subjective sound standpoint. The preference is
non-decisive; do not manufacture a stronger ranking or continue tiny A/B tuning.
Signalsmith remains the provisional engineering front-runner on lower measured
callback cost/zero observed callback allocations, with Rubber Band retained as the
sonic reference. This statement supplies no independent listening, artifact/bend
rating, pitch truth, final selection or PR06B approval. Exact feedback is bound
privately to the common-half-level package; all prior evidence stays unchanged.
Further private renders, DSP tuning, product integration and commits are not
authorized by this feedback.

**Bounded verification planning (2026-10-24):** the user authorized continuation of
defining the next checks. `docs/STUDIO_VERIFICATION.md` and
`pr06a-signalsmith-verification-001` now separate (A) synthetic meter/pitch attribution
and eventful delivery, (B) newly authorized source-bound vocal repeats, and (C) an
explicitly approved evaluation-only host route. A is proposed at 36 measurement
fixtures and at most 88 native captures, with no correction or parameter sweep;
none of these proposed runs is executed or approved by the planning artifact.
Retained historical scale/mix pitch misses stay visible despite passing delivery;
current guard/observer differences prevent simply regrading them as studio passes.
No new numerical onset/formant thresholds, private exception, consumed-receipt reuse,
AU install/Logic operation or product integration is authorized. Full-support,
independent human and host gates remain open; explicit PR06B go is still required.

**Synthetic execution approval and review pause (2026-10-24):** the user approved
synthetic-only tests, conditional on stopping for review if needed. A fresh
read-only reviewer in the requested bottom-right Herdr pane then found five
tooling bugs, all independently reproduced by the main agent with synthetic
fixtures. `docs/evidence/pr-06a/review-001.md` records receipt replay, proposal
containment, telemetry completeness, duration and fixed-sum validation findings.
Stage A stays paused for repairs/regressions and review of the fixes. No fixes,
new native runs or private payload access occurred. These findings do not prove
retained-audio corruption or change the provisional engine lead; private replay,
host operation, product integration and commit/merge/push remain unapproved.

**Tooling repairs accepted (2026-10-24):** on the user's fix request, all five
review findings were repaired with negative regressions and closed by follow-up
read-only review, including relocated legacy proposals and forged/backdated output
packets. Full four-profile product qualification and **165 Python tests** pass;
45 studio tests now cover the original failures and follow-up edge cases. Additive
revalidation of retained synthetic artifacts passes the new checks without changing
old results or waiving Rubber Band allocations. See
`docs/evidence/pr-06a/review-fixes-001.md`. Engine DSP/parameters/binaries, private
recordings/outputs/claims and historical contracts remain unchanged. No Stage A
or new candidate render has executed. Next is the already approved synthetic-only
Stage A implementation/calibration, not renewed permission for that same scope.
New private replay, host operation, product go and commit/merge/push remain separate.

**Local research commit/merge authorization (2026-10-24):** after the tooling fixes,
165 Python/full-product checks and independent review closure, the user explicitly
requested commit and merge. This authorizes committing the current architecture /
studio-pilot tooling and locally merging `research-architecture-feasibility` into
`main`, including its previously branch-only PR05 dependency `dda47a7`. It preserves
the negative research results and pending studio gates; it is not final engine
selection, a PR06B product go, AU integration/installation, new private rendering,
playback or host operation. The existing synthetic-only Stage A approval remains
separate from the merge. No push or remote publication is authorized.

**PR06A completion stop (2026-10-24):** the user requested completion after identifying
that the prior merge was only a partial milestone. On `pr-06a-completion`, frozen
A1 calibration passes 36/36 fixtures and A2 executes 72 matched generated-source
cases. Source/target/control/safety checks pass, but output pitch fails 34/72
cases: the same 17 conditions in each mode. A3 is not executed; reserved captures
are not repurposed for tuning. See `docs/STUDIO_VERIFICATION_RESULTS.md` for evidence
and limits. No tracker-only explanation, musical pass, engine choice or PR06B go
is inferred. PR06A is explicitly **BLOCKED**, not quietly marked complete to align
labels. A diagnosed bounded correction/retest requires a new decision; none was
attempted. Independent completion review remains before merge. No private payload
read, preview repeat, new engine/backend, threshold relaxation, AU/Logic operation,
commit/merge/push or historical-result change occurred in this attempt.

**Bounded correction approval and audit outcome (2026-10-24):** the user accepted
the recommendation to investigate wrapper/configuration, not the tracker, permit
one evidence-backed correction and regression, preserve requirements and stop if
failures persist. This approval was granted; it is not still awaiting a decision.
The subsequent [wrapper audit](evidence/pr-06a/wrapper-audit-001.md) found no
demonstrated integration defect or justified replacement configuration. API units,
transpose direction, formant compensation and streaming clocks match the pinned
implementation. Larger presets violate the complete latency ceiling; a manually
changed window/hop remains an unproven hypothesis, not a diagnosed correction.
Stop/reject the current 2048/512 configuration on its existing failed evidence.
No correction or regression was executed and no allowance/claim was consumed.
This does not establish impossibility for every configuration or select another
engine. PR06A remains blocked, A3/PR06B remain stopped, and independent completion
review remains outstanding. No private/host permission or automatic merge follows.

**Rubber Band allocation diagnosis authorization (2026-10-24):** after asking how
to resume the plan, the user requested continuation of the recommended next task:
diagnose the existing Rubber Band callback allocations within PR06A feasibility,
without changing requirements or advancing integration. Existing stacks already
identify lazy FFT setup and resampler state creation; repeating that finding alone
would not be a new fix. A separate synthetic-only diagnostic tests one source-backed
silence-only stopped-preparation hypothesis, not the previously rejected audio
priming strategy. The [frozen eight-capture protocol](evidence/pr-06a/rubberband-allocation-diagnosis-001.json)
compares fresh/prepared graphs at both rates under static/changing controls, counts
startup/body/tail/finish allocations separately and requires identical input/control/
metadata plus the retained output-difference limits. There is no product-wrapper
change, upstream edit, backend change, private read or timing claim from stack
capture. Failure rejects this preparation without tuning/retry. Any surviving
diagnostic is not pitch/full-support/host qualification or permission to integrate.

**Rubber Band diagnosis result (2026-10-24):** all eight fixed captures executed
once. Silent stopped preparation reduces observed callback/finish allocations to
zero, but all four paired comparisons fail native output lengths and common-body
waveforms. Reject it without retries or product-wrapper changes. The
[result/attribution](evidence/pr-06a/rubberband-allocation-diagnosis-001.md) identifies
FFT initialization, resampler buffer creation and 44.1 kHz phase-table growth.
One additional fresh-capture allocation came from a probe retrieval warning;
original counts/logs remain unchanged. That diagnostic bug is repaired with a
bounded-drain control, not rerun or misrepresented as a product fix. Both current
direct-callback configurations remain blocked. A worker-owned rendering prototype
is the next proposed architecture investigation, **not yet approved or executed**;
the complete 100 ms/PDC, callback safety, musical and source-permission gates stand.

**Worker feasibility authorization (2026-10-25):** after clarification in plain
language, the user explicitly approved testing background processing and resolving
the allocation blocker while keeping sound requirements and the 100 ms ceiling.
Implement an isolated worker-owned Rubber Band prototype, not AU integration.
The [frozen protocol](evidence/pr-06a/worker-feasibility-001.json) bounds six native
processes / 14 captures: synchronous references, wall-clock-paced workers and
coordinated offline workers at both rates/128–512 callbacks, plus two deliberate
200 ms worker-stall negatives. Native engines remain pristine, with no warmup,
upstream/backend change or native reset workaround. Fixed SPSC queues carry the
same source/control stream; callback paths may not wait, lock, allocate, call
native engines or join threads. Keep all original failures, worker allocations
and misses visible. This approval is not a private replay, host operation, final
engine choice, PR06B go or automatic commit/merge/push.

**Worker feasibility result (2026-10-25):** all six fixed native processes / 14
captures completed once. Every normal rate/buffer point passes: eight worker
captures have zero callback allocations, no delivery misses and exactly unchanged
audio/control streams at the original 100 ms software alignment. All 14 waveform/
partition comparisons are exactly equal. Native allocation is moved to workers,
not eliminated; all worker counts remain recorded. Both 200 ms stall negatives
expose missed delivery and fail closed without altering the lead. **The overall
screen still fails:** the first callback of the 48 kHz negative begins 3.917375 ms
late and misses its scheduled end by 1.252751 ms, before the injected worker fault.
Do not waive that observation, shift the epoch retrospectively or rerun `001`.
See [results and clocks](evidence/pr-06a/worker-feasibility-001.md). This demonstrates
normal callback isolation and meaningful technical progress, not complete timing,
pitch/support/host qualification or PR06A/PR06B acceptance. All 199 Python tests
and Release/ASan/TSan worker contracts pass. No product integration/merge occurred.

**Incomplete checkpoint and prototype-branch authorization (2026-10-25):** the user
requested faster progress toward a usable evaluation-only AU rather than more
engine research. They then explicitly authorized the proposed handling of current
changes: review and commit them as an **incomplete PR06A checkpoint**, preserve
failures, **do not merge**, and branch evaluation-AU work from that checkpoint.
The [checkpoint review/handoff](evidence/pr-06a/checkpoint-review-001.md) is a
self-review, not independent acceptance. Preserve `pr-06a-completion`; create
`evaluation-au-prototype` from the resulting local commit. No push, private replay,
new native matrix, AU installation/Logic operation or automatic qualification/go
is authorized by this checkpoint operation. Prototype implementation is the next
task; this commit does not claim the AU exists or that PR06A passed.

**Evaluation-only PR06B approval (2026-10-25):** after asking which PR contains the
prototype and whether it is preferable to premature PR07 integration, the user
explicitly requested PR06B on a branch. This authorizes the
[minimal separate evaluation AU](PR06B_EVALUATION_AU.md) on
`pr-06b-evaluation-au` from checkpoint `8f3a982`, as a sequencing exception while
PR06A remains incomplete. Freeze engine research; reuse the existing Rubber Band
worker direction, key/scale selection, three harmonies and unchanged aligned lead.
Preserve all qualification gates and original failures. Build and focused
synthetic/device-free tests are in scope; installation, actual Logic/device
operation, private-source reads, full formal qualification, PR07 integration,
commit/merge/push and final engine/distribution approval are not inferred.

**Evaluation-AU implementation result (2026-10-25):** the separate prototype now
builds, with explicit key/scale, three fixed scale-derived voices, unchanged
100 ms-aligned lead, global harmony trim/enable, parameter state and visible fault/
restart status. Pristine spare graphs swap on render boundaries; native work and
old-graph reclamation stay off callback. An AU-only compile switch disables worker
test instrumentation without linking its malloc interposer into the host; default
research instrumentation remains available. Original captured binaries/source/
reports are preserved, not regraded against this integration change.

All four Release functional tests, ASan/TSan fake-engine processor contracts and
204 Python tests pass; the exact built AU's impulse delay/property is 100 ms at
both rates. See `docs/PR06B_EVALUATION_AU.md`. This is real-time-only evaluation:
offline/unsupported-rate renders are explicitly lead-only, not qualified harmony
bounces. No installation, Logic/device operation, private replay, commit/merge/
push, final engine choice or formal PR06B acceptance is claimed. The next practical
step is a separately coordinated Logic audition, while all outstanding gates stand.

**Prototype delivery hardening (2026-10-25):** the worker proxy now preserves a
finite packet already advertised when its worker fails between availability and
retrieval. This avoids a callback exception/allocation race; session health still
immediately mutes all audible wet output. New processor and audited-worker
regressions cover it. Five Release checks, both ASan/TSan fake-engine contract
suites and 204 Python tests pass. The final preserved component and source/test
manifest are under `build/pr-06b-artifacts/ready-20261025-01/`. Intermediate exports
and all original PR06A reports remain unchanged. No installation, Logic operation,
formal qualification/go or automatic commit/merge/push follows from delivery.

**Evaluation-AU implementation closeout authorization (2026-10-25):** the user
requested closing out this PR after delivery. Review and commit the scoped
evaluation-AU implementation locally on `pr-06b-evaluation-au`, preserving known
failures and remaining gates. The [closeout](evidence/pr-06b/closeout-001.md) closes
the implementation task, not PR06B formal studio qualification or PR07 product go.
Independent review remains pending before merge/promotion. No main merge, push,
installation, Logic/device operation, playback or private replay is inferred.

**Independent prototype review/fix authorization (2026-10-25):** the user requested
an OpenCode reviewer in the bottom-right Herdr pane, followed by implementation of
fixes/improvements. Reviewer `pr06b-review` examined `8f3a982..358b0fb` read-only and
returned five actionable runtime/test findings, preserved in
`docs/evidence/pr-06b/review-001.md`. The scoped fixes and subsequent verification
are recorded in `docs/evidence/pr-06b/review-fixes-001.md`; a new artifact preserves
the original delivery. Musical/timing failures and formal qualification gates are
not changed. No merge, push, installation, Logic/device operation or private replay
is authorized by this request.

## PR07 sequencing approval and manual Logic acceptance (2026-10-25)

The user reports the evaluation AU works in Logic, including the discussed timing,
loop/seek, recall and musical listening checks, and explicitly asks not to repeat
those manual checks. These are **user-reported manual acceptance**, not invented
sample measurements, full-range annotations, stress reports or independent grades.
Logic version, source, project settings and measured tolerances were not supplied.
The assistant did not operate Logic, read recordings or perform the audition.

After being asked whether to start PR07 while explicitly deferring formal measured
qualification and preserving existing failures/accuracy requirements, the user
answered: **“yes, please implement pr 7 to completion on a branch.”** This is an
explicit sequencing exception permitting product implementation from `fb233d8` on
`pr-07-product-integration`, using the already-auditioned Rubber Band worker path.
It does not declare PR06A/PR06B qualification passed, rehabilitate Signalsmith,
waive the worker startup miss, select an alternative engine, or authorize private
reads/renders, installation, Logic/device/playback operation, merge, push or spend.
Implementation and focused regression evidence are separate from deferred formal
accuracy, expressive challenge c, native performance, host and licensing gates.

**PR07 implementation outcome:** product processor/native controls/state are complete
on `pr-07-product-integration`. Product identity and the first 23 parameters remain;
seven hint-3 mixer parameters and dry-safe v4 migration are frozen. Debug/Release
eight-check suites (209 Python tests each) and ASan/TSan four-check focused suites
pass. New signed product/source/log artifact:
`build/pr-07-artifacts/ready-20261025-01/`; scope, self-review and development
corrections are in `docs/evidence/pr-07/implementation-001.md`. No independent PR07
review or new product Logic operation is claimed. Deferred qualification and
historical failures remain unchanged; nothing is merged, pushed or installed.

**PR07 review/fix authorization and outcome:** the user requested a separate
OpenCode review in the bottom-right Herdr pane, then explicitly requested fixes.
Reviewer `pr07-review` examined `fb233d8..330fe8f` read-only and found three P2
state/preparation/recovery defects plus test gaps. Original findings and fix
verification are preserved in `docs/evidence/pr-07/review-001.md` and
`review-fixes-001.md`. The same reviewer confirmed the production fixes and
strengthened fixture gaps addressed at source level, without executing tests.
Parent Debug/Release eight-check and ASan/TSan four-check suites pass, including
209 Python tests per tooling run. Delivery `build/pr-07-artifacts/ready-20261025-02/`
is separate from the unchanged original. No host IDs, ranges/defaults, v4 state
bytes, backend or qualification requirements change. Formal measured qualification
stays deferred; no merge, push, installation or private replay is authorized.

## PR08 implementation authorization (2026-10-26)

After merging PR07 locally, the user requested completing PR08 implementation on
a branch. Branch `pr-08-host-bounce-integration` starts at `f36e5d8`. Implement the
offline bounce path, synthetic exact-AU/recall tests, opt-in installed checks and a
concrete user-session handoff. This is not authority to install, invoke installed
`auval`, operate Logic/devices, play audio or read private recordings automatically.
Existing manual evaluation-AU acceptance remains accepted without demanding the
same audition again; it is not transferred as measured evidence for product 0.3.0.

Offline coordination uses the same native engine/command/source clock, allowing
bounded waits only when the host explicitly marks non-realtime. No backend,
quality mode, musical/accuracy gate or persisted parameter/state meaning changes.
Actual installed/Logic/recorded-vocal acceptance stays pending until coordinated;
native checks cannot close those gates. Prior failures and consumed claims remain
unchanged. Scope and handoff: `docs/PR08_HOST_INTEGRATION.md`.

## PR08 user acceptance and merge authorization (2026-10-26)

After the reviewed fixes and host-checklist handoff, the user reported testing
"all of it," declined to fill `worksheet.json`, declared a pass and explicitly
requested commit and merge. Accept this user-reported product-host acceptance
without requiring the worksheet or repeating the tests. Commit the acceptance
record and merge PR08 locally; no push or further host/private operations.

No raw numerical results, exports, setup details or project/binary hashes were
supplied, so none are fabricated or claimed independently verified. The prior
artifacts and generated worksheet retain their historical pending records; the
new user decision supersedes them for PR08 acceptance and merge, not formal
measured accuracy/full-support, challenge c, performance/soak or licensing gates.
Record: `docs/evidence/pr-08/user-acceptance-001.md`.

## PR09 branch implementation authorization (2026-10-26)

After local PR08 merge `8aa76c6`, the user requested completing PR09 on a branch.
`pr-09-studio-session-qualification` implements an opt-in metadata-only processor
capture, synthetic exact-AU Release timing/allocation screen and strict local
analysis/handoff. Version 0.4.0 identifies the instrumented candidate; musical DSP,
30 parameter meanings, v4 state, native engine/profile and 100 ms PDC are unchanged.

No automatic installation, installed `auval`, Logic/device/playback operation,
private-source reading/rendering, new corpus sweep or consumed-claim reuse is
authorized. PR08 user acceptance stands without another worksheet. PR09 actual
30-minute session observations and independent final listening cannot be invented
from it. The purported approved PR06B revised listening rubric remains pending in
the underlying protocol records. Missing resources/observations require an explicit
incomplete/negative qualification result, not a success claim or lowered gates.
Scope and operator steps: `docs/PR09_STUDIO_SESSION.md`.

## PR09 local merge authorization (2026-10-26)

After implementation `4de958d`, reviewed fixes `45a34ab` and explicit notice that
the original variable-block audio failure remains unresolved, the user requested
"ok please commit and merge". Record the approval and merge PR09 locally as an
**engineering / negative-qualification milestone**, not a qualified studio pass.

No new host/soak/listening results or requirement revisions were supplied. The
failed screen, missing actual Logic/whole-host evidence, independent listening/
rubric, formal full-support/challenge-c/licensing gates remain open. Prior artifact
reports are historical and are not rewritten or regraded. This authorizes no push,
additional installation/host/device/playback operation or private-source access.

## PR10 local handoff authorization (2026-10-26)

After local PR09 merge `ef80f07`, the user requested implementing PR10 to completion.
Branch `pr-10-local-handoff` delivers setup/use/evidence instructions, reversible
owned-product uninstall, cache-only clean-local-clone checks, and an explicit
negative qualification report. Product stays 0.4.0; musical DSP, 30 host parameters,
v4 state, pinned dependencies, 100 ms alignment and all frozen gates are unchanged.

Uninstall requires explicit execution/approval and retains the component and exact
ownership receipt outside AU discovery. No recursive deletion, broad cache reset,
automatic old-version restoration or unrelated plug-in modification is allowed.
Clean reproduction uses local committed Git objects and existing verified archives;
no downloads, purchases, package installs, engine search or upstream patching.

Implementation completion is not final user acceptance, independent review, merge
or push authorization. Real installed-AU/auval/Logic/device/playback operations and
private recording access remain separately coordinated. PR08's reported pass is
accepted without another worksheet; PR09's failure is not rerun or regraded.
The outcome is a **studio-first scale-mode engineering handoff, NOT qualified**;
full-support/challenge-c, independent listening/rubric, actual Logic/whole-host/soak,
final studio acceptance and distribution/license clearance remain open.

## PR10 local merge authorization (2026-10-27)

After the independent reviewer closed both P2 findings, all repaired four-profile
checks passed and the explicit no-go was reiterated, the user requested
"ok please merge". Merge `pr-10-local-handoff` locally into `main` as a reviewed
**engineering / negative-qualification handoff**, not a qualified studio pass.

The authorization accepts that limited merge outcome; it does not pass missing
installed-AU/user-workflow, actual Logic/whole-host/soak, independent listening/
rubric, full-support/challenge-c, final studio or licensing/distribution gates.
Preserve the original failure and all artifact histories. No push, installation,
host/device/playback operation, private-source access or new research is authorized.

## Original / harmonies mix follow-up (2026-10-27)

The user reports that harmonies are too quiet relative to the original and asks
for a mix-style UI. On `fix-harmony-mix`, add a prominent, genuine automatable
Original ↔ Harmonies balance while retaining existing per-voice/original trims.
Use centre-unity attenuation: 50% retains the exact old sound; turning right
reduces the original rather than boosting the wet sum. Keep the one-third voice
gain and 10 ms smoothing; add no limiter/normalization or extra latency.

Version 0.5.0 appends `harmonyMix` after the existing 30 parameters (new version
hint 4) and writes v5 state. V4 loads at centre; older dry-only migrations remain.
No old host parameter meaning/order/range/default changes. This authorizes the
declared mixing/UI change, not changes to pitch/worker architecture or frozen
qualification gates, installation/Logic/device/playback/private-source operations,
new dependencies, historical timing/research reruns, merge or push.

## Harmony Mix and AU reload local merge authorization (2026-10-27)

After implementation of the 0.5.0 Mix control and the timestamp/registry-wait
reload repair, the user requested "ok please commit and merge". Commit
`fix-harmony-mix` and merge it locally into `main`; no push or additional installed
operations. Mix passed Release/Debug 11/11 and ASan/TSan 4/4 each; the subsequent
Python-only reload repair passed all 295 Python tests and uninstalled-copy
signature preservation checks. Evidence lives under `docs/evidence/harmony-mix/`.

No new successful actual registry/Logic result was supplied, so none is inferred
from this merge approval. Existing PR08 acceptance stands; PR09's variable-block
failure and remaining formal studio/host/listening/licensing gates stay open.
