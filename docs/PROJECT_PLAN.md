# voxide — zero-spend project plan

Status: PR 00 through PR 02 are merged locally. PR 02 engineering and review fixes
are complete and automatically qualified. The user approved its merge and deferral
of detailed annotations until tracker development; full corpus, human-review and
remaining policy-approval gates stay pending.
PR 03 causal tracking and target selection are implemented, independently reviewed
and automatically qualified on `pr-03-causal-tracking-selection`. The user approved
its local engineering/research commit and merge; no audible harmonies. Timing misses
and deferred human/host gates still block architecture/product qualification.
PR 04 is merged locally at `997e884` as a reviewed engineering/research milestone,
retaining candidate-engine failures. PR 05 interaction engineering implementation
and automated qualification are complete on `pr-05-three-voice-interaction` at
`dda47a7` as a negative research milestone, initially committed branch-only. It is
now merged locally with research/tooling commit `534f6e5`. No engine/architecture
is selected; quality/timing and human/host
gates remain open.
The authorized bounded architecture investigation is complete on
`research-architecture-feasibility`, locally merged as `534f6e5`
with the reviewed PR06A tooling. It corrects overly broad timing
interpretations but finds no technical survivor for the tested combined live/mixing
scope. See `docs/ARCHITECTURE_INVESTIGATION.md`; its results remain unchanged.
**Current direction (user clarification, 2026-10-24): studio-first, scale-first,
three harmony voices, minimum ±12 semitones, intentionally processed vocal character.**
**Sequencing exception approved 2026-10-25:** implement only PR06B's separate
evaluation AU on `pr-06b-evaluation-au` from incomplete checkpoint `8f3a982`.
PR06A's failed/pending gates remain visible; formal qualification, product go and
PR07 integration remain blocked. See `docs/PR06B_EVALUATION_AU.md`.
PR06A's approved excerpt-a/C-major listening-only comparison is rendered. The user
reports good sound, a Rubber Band preference with a seemingly small difference,
and no distracting artifacts on this example. The earlier bounded engineering comparison
favored Signalsmith 2048/512: zero callback allocations and lower callback cost;
both candidates pass stopped-reconstruction/repeat checks in this synthetic set.
The separately approved clip-c trial ran under unchanged diagnostic C-major
settings. Signalsmith passes export checks; Rubber Band exceeds the conservative
preview-level ceiling (no observed digital full-scale overs). The user explicitly
approved a separate common 0.5 playback export from retained outputs; its nine
validated previews have received user feedback: a tentative Rubber Band preference,
but a minimal, explicitly non-decisive sound difference. Engineering suitability
therefore remains the practical discriminator. The original withheld run stays
unchanged; that provisional preference is superseded by the subsequent pitch
failure below. No final engine or product go is selected.
The bounded verification in `docs/STUDIO_VERIFICATION.md` has reached its required
stop: **A1 passes 36/36; A2 fails output-pitch gates in 34/72 cases; A3 is not
executed.** Separate private-replay and host approvals remain untouched.
The user has approved synthetic-only execution. Five PR06A tooling review defects
are now repaired, regressed and independently closed; 165 Python/full-product
checks passed for that tooling milestone. See `docs/evidence/pr-06a/review-fixes-001.md`.
The merged `534f6e5` was a **partial research/tooling milestone, not PR06A closure**.
The `pr-06a-completion` checkpoint preserves the approved bounded synthetic work
and records its negative result. **PR06A is BLOCKED at technical feasibility, not
accepted/complete; formal PR06B/product go remains blocked.** All 72 A2 source/control/safety checks
pass, but prescribed and tracked paths fail the same 17 conditions per mode.
See `docs/STUDIO_VERIFICATION_RESULTS.md`. Driver qualification passes 186 Python
tests/full product checks; that does not override the failing DSP experiments.
The subsequently approved bounded wrapper/configuration audit found no justified
correction; stop/reject the current configuration without speculative retries.
See `docs/evidence/pr-06a/wrapper-audit-001.md`. No extra merge is authorized.
The subsequently authorized Rubber Band allocation diagnosis also completed:
silence-only preparation removes measured callback allocations but changes every
paired output's native length/waveform, so it is rejected. Both current direct-
callback configurations remain blocked. See
`docs/evidence/pr-06a/rubberband-allocation-diagnosis-001.md`. The user subsequently
approved the isolated worker-owned feasibility prototype on 2026-10-25, not
further preset tuning or PR06B integration. Its fixed 14-capture protocol is at
`docs/evidence/pr-06a/worker-feasibility-001.json`; implementation and all 14
captures are complete. **Normal worker callback isolation passes all four points**:
zero callback allocations, no delivery misses, exact reference audio/controls and
unchanged 100 ms software alignment. **The overall screen remains failed** due to
one first-callback scheduled-finish miss in a deliberate-stall case. No retry or
waiver occurred. See `docs/evidence/pr-06a/worker-feasibility-001.md`. All 199 Python
tests and Release/ASan/TSan worker contracts pass; musical/host qualification and
independent completion review remain pending. This is a working normal-case
architecture, not permission to close PR06A or start product integration.
PR06B must still establish a studio go-decision. Live, MIDI-first and
±24 coverage are deferred, not qualified. See the decision below and
`docs/DECISIONS.md` for approval/protocol boundaries.
User testing supports direct-input monitoring with Low Latency Mode off/on and
project recall; remaining host checks and the track-fed mode limitation are recorded
below. No harmonizer quality or measured monitoring-latency qualification yet.
Created 2026-10-20.

## 1. Brief and hard boundaries

Build a vocal harmonizer for Logic Pro: **one unchanged original lead plus exactly
three available generated harmony voices**. The first useful milestone prioritizes
**recorded vocals, user-selected key/scale, inclusive ±12-semitone support and an
appealing deliberately processed harmony character**. MIDI mode, live use and
±24-semitone coverage remain later goals. The original combined brief and earlier
qualification results are historical evidence, not claims that this studio milestone
already works or completes every original requirement.

- **No money may be spent.** No commercial SDK purchase, paid evaluation, paid
  plug-in, subscription, signing membership, cloud service, hardware purchase, or
  paid participant is a dependency. Use existing equipment/Logic and free tools.
- A free product is not necessarily unrestricted. Confirm dependency terms before
  adopting or distributing code. Do not assume the user wants to publish source.
- Keep the feature scope fixed. No automatic key/chord discovery, lead tuning,
  voice cloning, extra voices, reverb/effects suite, preset marketplace, ARA,
  additional DAWs/formats, or custom production pitch-shifter research program.
- Start with native Apple Silicon/macOS and AU, following Nitride's conventions.
  Proposed baseline: arm64, macOS 15+, C++20, CMake 3.24+. Confirm the actual Mac
  before freezing this support profile. Standalone/headless targets are development
  and evaluation tools, not additional product promises.
- A clearly labeled studio-first result can satisfy the newly prioritized milestone,
  **not** the full original live/MIDI/±24 brief. This user-approved sequencing/range
  revision does not allow further silent narrowing, extra latency, fewer voices,
  unsafe output or weaker pitch correctness to manufacture a pass.

### Current milestone and artistic reference — 2026-10-24

The user selected scale mode over MIDI-first, identified recorded-vocal processing
as higher priority than live singing, and made ±12 semitones the minimum acceptable
range. They cited Brian Eno's *Another Day on Earth*, **“Bottomliners,” 1:30–2:00**,
primarily for its **processed vocal character**, not specific harmony note choices.
The reference has not been auditioned/analyzed by the assistant; no exact voicing,
effect chain or DigiTech algorithm/provenance has been established. It is an
artistic reference, not a request to copy the recording or recreate hardware.

| First milestone: retained | Deferred, not passed | Still needs explicit protocol/qualification |
| --- | --- | --- |
| Unchanged lead + three available harmonies; E2–C6; 44.1/48 kHz | ±24 coverage beyond the required inclusive ±12 | Versioned studio contract/tool support; no edits to historical baselines |
| User-selected key/scale; existing expression/range-handling semantics | MIDI-first UI/control qualification; existing state/IDs retained | Pilot root/scale/voicing and safe uncertain-source behavior |
| Recorded-vocal processing; ≤100 ms complete studio delay with accurate PDC | Live processing/monitoring and MIDI-response go-gates | Recorded onset/transition and first-syllable/tail correctness; no newly approved response threshold |
| Intended notes, intelligibility, bends/rhythm, finite safe output, headroom and reproducibility | A requirement to make three indistinguishable human singers | Deliberate electronic character versus unwanted artifacts; revised timbre/formant/listening rubric |
| Zero spend, existing engine families, privacy and approval boundaries | Product integration until PR06B's studio go | Development listening-only protocol/source approval; formal references/listeners/host evidence |

No new engine, configuration winner, effect, private rendering/playback exception,
purchase, installation or code change is authorized by this documentation request.
The immediate deliverable is a bounded pilot plan (PR06A), followed by separate
formal studio qualification (PR06B). `docs/DECISIONS.md` records the conversation
and distinguishes confirmed direction from proposed trial details.

### Repository and Nitride reference

This project lives in `/Users/bencrouse/Code/voxide`. Use the sibling
`../nitride` as a **read-only engineering reference**, not a runtime/build dependency
and not a destination for Voxide changes. At planning time Voxide was empty and
not a Git repository. Nitride reported HEAD
`30dd71e0dbce87eb7370661ac288c1aea1e2a57a`; its working tree was not certified clean.

Useful Nitride material inspected:

- `../nitride/cmake/JuceDependency.cmake`: checksum-pinned dependency and explicit
  local override rather than implicitly finding a sibling build.
- `../nitride/CMakeLists.txt`, `CMakePresets.json`, `Makefile`: C++20, separate DSP,
  AU/Standalone, local Debug/Release/ASan/TSan workflows.
- `../nitride/scripts/check.py`, `docs/HARDENING.md`: immutable regression inputs,
  allocation-audit self-test, local ad-hoc signing, GUI-context AU validation.
- `../nitride/docs/RELEASE_QUALIFICATION.md`: measured evidence is distinct from
  manual Logic observations; missing hardware results remain pending.
- `../nitride/CONTRIBUTING.md`: processor/editor separation and stable host IDs.

Reuse patterns selectively after establishing permission to reuse code; no project
license was found at Nitride's root. Do not copy its synth engine, identity,
presets, private evaluation recordings, measurements, or instrument-only settings.
In particular, Voxide is an **AU music effect (`aumf`)**, not Nitride's AU instrument
(`aumu`). Existing Nitride success is not evidence that Voxide works.

## 2. Quality contract and open user decisions

The original PR02 numerical contract was approved on 2026-10-21 with ±24-semitone
shifts. Preserve it and all reports against it. The 2026-10-24 studio-first decision
changes the first milestone to inclusive ±12 and defers live/MIDI-first/±24 gates;
it is not an automatic revision of executable contracts or a passing qualification.
PR06A must version the new scope/protocol before rendering. Unchanged numerical
correctness/safety requirements remain; revised timbre scoring and any studio-specific
response criteria require explicit approval rather than a silent threshold edit.

### Listening standard

- Correct intended notes with no octave jumps, semitone chatter, unintended voice
  reassignment, or lingering wrong notes.
- For the studio pilot, seek a musically useful **intentional processed vocal
  character**. Electronic coloration alone is not a defect or proof of success;
  evaluate consistency, vowel/articulation readability and the user's reference
  preference. The former naturalness-first prohibition on conspicuous metallic/
  buzzy/phasey coloration is not an absolute artistic rule for this milestone.
  Original numerical formant/listening scores remain historical until a revised
  rubric is explicitly approved; no formant processing change is implied here.
- Consistent expression policy for vibrato, scoops, dynamics, and endings.
- Intelligible consonants/breaths without chirps, smeared attacks, missing syllables,
  or exaggerated stacked sibilance.
- Three simultaneous harmonies remain clear during changing notes, without clicks,
  bursts, warbling, or timing flams. Test mono as well as stereo presentation.
- Original lead is unshifted and otherwise unprocessed except explicit gain and
  documented alignment delay. Verify it separately by a delayed unity null test.
- Exposed harmonies and a fixed representative mix are usable without repair or
  masking processing failures with other effects.

The first target is deliberately processed harmonies, not three independently
performed or indistinguishable human singers. The lead remains unchanged; do not
apply processing to it merely because an album passage is the timbral reference.

### First studio milestone support envelope (historical PR02 contract preserved)

| Item | Requirement to qualify |
| --- | --- |
| Source | Dry, mono, one singer; no pre-existing harmonies |
| Input F0 | E2–C6, approximately 82–1,047 Hz |
| Shift per voice | Inclusive −12 to +12 semitones, including dynamic changes; smaller support is unacceptable |
| Mathematical output extremes | Approximately 41.2–2,093 Hz for this milestone; qualify these endpoints too |
| Project rates | 44.1 and 48 kHz |
| Required articulation | Normal voiced singing, breathiness, vibrato, register transitions, consonants |
| Stress material | Fry, growls, whispers, clipping, accompaniment bleed: safe/graceful behavior, with reliable pitch guarantees explicitly decided |

Report common shifts within ±7 separately from octave shifts through ±12. Passing
±7 does not qualify this milestone. Earlier two-octave/±24 results remain available
and are not regraded or promoted; ±24 support is deferred, not achieved. Note names
use C4 = MIDI 60 regardless of Logic's configurable octave display.

### Separate timing budgets

The existing numerical budgets below remain the **historical original targets**.
The first studio milestone retains the ≤100 ms complete processing ceiling with
accurate PDC. Live input/monitoring and MIDI response are deferred for its go-gate,
not marked passed. Recognition and first-correct-output clocks must still be
reported; a studio-specific timing/measurement rubric is pending PR06A approval.
Do not hide wrong note transitions by subtracting analysis/observer delay, and do
not assume compensation repairs missing syllables or makes live audio faster.

| Quantity | Definition | Approved numerical gate |
| --- | --- | --- |
| Processing delay | Complete plug-in audio delay including engine, adaptation buffers, and intentional lookahead/alignment | Live goal ≤10 ms, ceiling 15 ms; mixing ≤100 ms with accurate PDC |
| Note recognition | Voiced onset/pitch transition to correct stable tracker/selector decision | P95 ≤30 ms above 150 Hz, ≤50 ms below; cold onset and continuous transitions reported separately |
| MIDI control response | Timestamped event at plug-in input to applied control state | ≤one control interval, target ≤5 ms; audible settling measured separately |
| Total monitoring | Analog input to headphone output through interface, Logic, and complete route | Goal ≤15 ms, ceiling 25 ms |
| First correct audible harmony | Source onset/transition to correct output including acquisition/audio path | P95 ≤75 ms low-register cold onset, ≤50 ms established voiced transition |

One E2 period is about 12 ms. A small host callback does not imply fast pitch
recognition. Analysis and buffered synthesis can overlap: derive actual scheduling
and measure it rather than blindly adding all budget entries. Separately log MIDI
device-to-host delay when measuring the physical keyboard experience.

### User decisions to close in PR 02

- [ ] Confirm Mac/chip/RAM, macOS, Logic, interface/driver, MIDI controller,
  headphone path, sample rates, normal buffer sizes, and representative session.
- [x] Original numerical approval: E2–C6 input, ±24 shifts, 44.1/48 kHz. User later
  set inclusive ±12 as the first milestone minimum; E2–C6 and both rates remain.
- [ ] Confirm stress-source guarantees; 96 kHz remains outside the support envelope.
- [x] Approve the plan's numerical latency ceilings and quality thresholds.
- [ ] Confirm whether lead monitoring must be entirely in software or normally
  uses the interface's direct path. Direct lead monitoring
  does not make delayed harmonies low-latency.
- [x] Approve starter mapping/expression/uncertainty/range policies and broad scale
  coverage in PR03 (2026-10-22); retain those semantics for scale-first work.
  Stress-source guarantees and the new studio listening protocol remain pending.
- [x] User confirmed local-only use for now under JUCE's AGPLv3 option. Revisit
  source/notice obligations before sharing; no paid license fallback is assumed.
- [ ] Confirm no-cost recordings and independent listeners available. Missing
  resources remain blocked gates, not permission to invent results.
- [x] Select studio-first recorded-vocal processing and scale-first mode; identify
  “Bottomliners,” 1:30–2:00, as a processed-character reference (2026-10-24).
- [ ] Approve the versioned studio pilot/listening rubric and exact source handling
  before private rendering; this documentation does not bypass current preflight.

## 3. Architecture evidence and zero-cost shortlist

Maintain four explicit evidence classes in reports:

1. **Documented/source-supported:** observed API or inspected implementation.
2. **Vendor claim:** advertised quality/performance not independently verified.
3. **Engineering hypothesis:** a reason for an experiment, not a result.
4. **Measured:** an actually executed, reproducible test with raw evidence.

At plan creation, only documentation/selected source inspection has occurred.
No engine has been built, benchmarked, or auditioned here. No Logic/hardware
validation has occurred. No recordings or SDK access have been supplied.

### Active candidates

**Signalsmith Stretch — primary no-cost candidate.** MIT-licensed C++ source with
configurable windows, dynamic ratios, and formant compensation. Inspected header
reported 1.3.2. Its default/cheaper analysis windows are 120/100 ms, not measured
audio latencies; do not use defaults as evidence of live suitability. The README
cautions that formant correction is less sharp than monophonic approaches such as
PSOLA. Inspect its FFT dependency license too. Its rough internal formant F0
estimate is not a qualified harmony tracker. Compare tracked and internal formant
estimates with correct timestamps. Audit allocation paths and peak computation.

**Rubber Band 4 LiveShifter — no-cost evaluation/mixing comparator.** Public source
is GPL-2.0-or-later, not permissively licensed. Keep it in a separate evaluation
executable initially; assess compatibility before linking/distributing anything.
Its API documents 50 ms or more delay, so it is not a likely live candidate under
the proposed ceiling. Inspected source uses 512-frame blocks and pitch-dependent
start-delay calculations. Measure adapter delay and changing-ratio behavior.
Commercial licensing is outside the zero-spend plan.

Do not expand the active comparison beyond these two engines during this study.
If neither qualifies, produce an evidence-backed no-go or ask for a new bounded
requirement/research decision. A from-scratch PSOLA engine is not an automatic PR.

**Studio-first follow-up:** PR06A may propose a small comparison of the existing
slower/mixing configurations under the revised first-milestone priorities. They
are candidates, not accepted fixes: common-shift quality, allocations/reset and
repeatability failures are not erased by deferring live use or ±24. No new engine,
upstream patch or open-ended preset/algorithm search is approved. The actual
PR04/05 Rubber Band comparator is pinned R3 `RubberBandStretcher`; the earlier
LiveShifter discussion above is source context, not permission to switch APIs.

### Commercial material retained only as context

- ZTX PRO was the commercial candidate because its documented edition supports
  seamless dynamic pitch changes; LE/STUDIO do not. Core's formant capabilities
  and FX's speed claims cannot be combined into an assumed configuration. No
  paid SDK work or vendor quote is a dependency now.
- INTONE's public v1.4.0 API disables global offset in low-latency mode, exposes
  pitch-class selection rather than arbitrary absolute target-note control, and
  defines zero latency as no leading zero samples, excluding buffer accumulation.
  Its marketing is not proof of live three-voice suitability. No integration planned.
- Waves Harmony and Melodyne can be optional references **only if already owned**.
  Do not buy them or depend on expiring trials. Their absence does not block the
  free comparison and must be disclosed in the final evidence.

### Baseline processing structure

```text
mono source ───────────────────────── original lead (explicit gain/alignment)
     ├─ timestamped F0 + voicing/confidence
     │       └─ scale-degree mapping OR absolute MIDI targets (three slots)
     └─ three independent formant-preserving shifters
             └─ consonant/transition handling, alignment, controlled summing
```

Share tracking/selection, not shifter state. Multichannel processing is not the
same as three independently pitched voices. For each voice use target/source F0
at the appropriate source-audio timestamp. MIDI supplies targets, not source F0.
Test stale analysis, ratio ramps, and octave errors at boundaries. Begin with
three instances rather than speculative shared-spectrum optimization.

Investigate a causal YIN-family tracker with (a) framewise candidates plus bounded
smoothing/hysteresis and (b) multiple candidates with causal temporal selection.
pYIN motivates alternative candidates, but its published 46.4 ms frames, 5.8 ms
hops, Viterbi decoding, and synthesized-singing results do not establish our live
response. Offline pYIN is an annotation aid, not ground truth.

Compare engine-native consonant behavior against one shared confidence/voicing-aware
policy with smooth transitions. Mixed voiced/unvoiced sounds require testing;
binary gates can damage breathy vowels and voiced consonants. Three unshifted
copies of a consonant can reinforce, so assess sibilant level in the complete sum.

## 4. Evidence, validation, and merge rules

### Common rules for every PR

- [ ] Limit changes to the named scope and list prerequisites; no unrequested work
  in Nitride, no unrelated code cleanup or dependency upgrades.
- [ ] Run existing checks plus the PR-specific checks below. Retain command, exit
  status, build hash, dependency hashes, settings, and environment metadata.
- [ ] Keep expected audio/annotations immutable in normal tests. A baseline change
  needs an explicit review explaining the sound/contract change; do not regenerate
  expected output from the candidate and call that validation.
- [ ] Label evidence accurately. A test script existing is not a test passing;
  `auval` passing is not Logic passing; offline speed is not dropout-free monitoring.
- [ ] Use `pass`, `fail`, `pending`, or `not applicable with reason` per gate.
  Missing required observations block merge of that PR. Research PRs may merge a
  reproducible negative result, but cannot claim product acceptance or unlock a
  downstream go-gate they failed.
- [ ] Update this plan's PR handoff section with decisions, learnings, reflections,
  evidence paths, unresolved problems, and the next exact action. Do not infer
  permission to launch subagents merely from the existence of a handoff section.
- [ ] No purchases, automatic uploads, DAW termination, broad AU-cache resets,
  microphone capture, device-setting changes, or installs during ordinary tests.
  Live capture and installation are explicit user-coordinated steps.

### Evidence layout to establish

- `Source/DSP/`, `Source/Tests/`, `cmake/`, `scripts/`: implementation and tooling.
- `Source/Tests/Fixtures/`: small redistributable synthetic/approved test assets.
- `evaluation/`: ignored private recordings, Logic projects, immutable per-run
  renders, annotations, raw ratings, failures, and machine measurement reports.
- `docs/evidence/`: shareable manifests/summaries and reproduction instructions;
  private sources are identified by opaque IDs and hashes, not copied into Git.
- `docs/DECISIONS.md`, `docs/VALIDATION.md`, `THIRD_PARTY_NOTICES.md`: decisions,
  actual commands/contracts, dependency provenance/terms. Create during relevant PRs.

No new plan documents should compete with this checklist. Code/document paths and
commands below are proposed deliverables, not files/tools already available.

### Reproducible corpus and listening method

**Two stages, not a replacement of human evidence:** PR06A's small development
preference pilot comes first; the corpus/reference and independent-listener work
below remains formal PR06B qualification work, not a prerequisite for merely
documenting the direction. A listening-only private-render route without pitch
annotations needs its own explicitly approved protocol before implementation or
use. Current preflight still requires completed human references. Do not fabricate
them, treat informal preference as pitch truth, silently bypass the preflight, or
consume holdout material for the pilot. Missing formal resources stay pending.

Target 24 dry 10–15-second excerpts from six volunteer singers plus two user-session
passages, preferably mono 24-bit/48 kHz without tuning/compression/reverb/denoising.
Cover registers, vowels, legato, leaps, fast syllables, scoops/vibrato, breathiness,
falsetto/register breaks, plosives/sibilants, and quiet endings. Preserve metadata
and consent/usage rights. Use a singer-separated development/holdout split retaining
range coverage; keep holdout sealed until settings are frozen.

Two annotators mark voiced regions, F0/note transitions, intended notes, consonants,
and uncertainty. Adjudicate disagreement. Synthetic fixtures provide exact F0 and
formants: sines, harmonic complexes, missing fundamentals, pitch steps/glides/vibrato,
source-filter vowels with known resonances, noise bursts, silence/level changes,
and controlled noise/bleed. Real high-F0 formant estimates are not unquestionable truth.

Recruit six volunteer listeners including two vocal engineers/producers and two
singers; at least four independent of implementation. Use anonymous randomized
labels, hidden duplicates, a degraded anchor, matched loudness, exposed stems,
three-voice sums, and one fixed mix. Align overall delay only for timbre tests;
retain native timing for response tests. Collect 1–5 naturalness, articulation,
stability, usability scores and timestamped defects. Use balanced subsets in two
approximately 45-minute sessions. An administrator retains the identity key.
This is not formal MUSHRA: no perfect unprocessed transformed performance exists.
Follow with randomized live trials by the user and another singer, if available.

The preceding naturalness-first scoring/session design is the original proposal.
PR06A must propose a studio rubric for intended processed character, articulation,
pitch/expression stability and usefulness; PR06B freezes/approves it before formal
listening. Reference affinity is not permission to omit critical defect checks,
weaken numerical pitch targets, or claim the reference's exact sound was recreated.
Live trials are deferred beyond the first studio milestone.

Use free Python/NumPy/SciPy, Praat, Instruments, AU tools, and independently checked
output-pitch analysis. Do not certify output with Voxide's own tracker alone.

### Numerical final pass gates approved in PR 02

This table preserves the original baseline, not a new executable studio contract.
Correctness/safety/lead/headroom/reproducibility requirements are retained. PR06A
must explicitly map each gate to unchanged, deferred or pending studio-protocol
approval; naturalness/formant scoring cannot be silently relabeled as passed.
The studio go-gate does not require deferred live/MIDI/±24 qualification, but still
requires the full declared ±12 scope and all approved studio gates. A pilot liking
does not waive callbacks, host behavior, formal references or independent listening.

| Gate | Requirement |
| --- | --- |
| Tracking | ≥99% stable annotated voiced frames within 25 cents; octave errors <0.1%; per-singer/register results as well as pooled |
| Selection | 100% expected mapping on synthetic/MIDI fixtures; no reproducible wrong-note holdout event >50 ms |
| Unvoiced material | No sustained false pitched harmony on consonant-only/silence fixtures; no audible chirps or clipped syllables |
| Formants | Synthetic resonances: median error ≤5%, P95 ≤10%; independent real-vocal listening also passes |
| Listening | Median ≥4/5 for each main attribute, ≥80% usable-without-repair judgments on required holdout cases; no critical defect confirmed independently by two listeners |
| Timing | Approved processing, note-recognition, MIDI, monitoring, and audible-response budgets all met |
| Real-time | Three voices; P99.9 callback occupancy <50% of deadline as a provisional controlled-hardware screen; zero observed overdue callbacks in that run; zero observed dropouts in 30-minute representative Logic session |
| Lead/PDC | Unity-gain delayed lead null and deterministic compensation reference within agreed numerical tolerance; no duplicate lead |
| Host/state | Required routing/MIDI/transport/recall/offline-bounce cases pass |
| Cost/license | Zero required expenditure and documented permitted use/distribution |

Freeze numerical null/block-comparison tolerances in PR 02 (starting proposal:
maximum sample error 1e-6, RMS 1e-7 for unity/deterministic paths). Separate those
from perceptual tolerances on transformed audio. Report uncertainty, counts,
denominators, worst cases, and confidence intervals. A small corpus supports a
bounded decision, not universal professional-quality certification.

## 5. PR-by-PR implementation checklist

### PR 00 — Repository, dependencies, configuration, and check skeleton

Depends on: this plan; user licensing/support-profile clarification as needed.

**Scope / TODO**
- [x] Initialize Voxide's Git repository if still absent; do not initialize/copy
  Nitride's history or create a remote without asking.
- [x] Add minimal README, contributing instructions, scoped ignores, directory
  layout, CMake/CTest, Debug/Release/ASan/TSan presets, and local check entrypoints.
- [x] Audit exact pinned JUCE terms: Nitride's 8.0.15 revision
  `91ad83ae34a81e0833b1a2b0866f54846370ae53` uses **AGPLv3 or commercial licensing**.
  Confirm a no-cost compliant path; no assumed commercial entitlement. If the
  user's distribution/source preferences conflict, stop before adopting JUCE.
- [x] Pin approved dependencies by revision and archive checksum; document licenses
  and transitive dependencies. Keep Rubber Band in an optional isolated evaluator.
  Pin free Python evaluation dependencies separately; no global package mutation.
  PR 00 adopts JUCE only; Python is standard-library-only. Engine evaluators and
  Python evaluation packages are intentionally deferred to their scoped PRs.
- [x] Build minimal shared DSP/test target and AU music-effect shell with unique
  Voxide bundle/manufacturer/subtype IDs, MIDI input, correct input/sidechain buses,
  and mono-source/stereo-output layout. No synth flags copied from Nitride.
- [x] Add explicit local ad-hoc sign/install/`auval` helpers and build metadata.
  Ordinary `make check` must not install anything. No paid Developer ID/notarization.

**Validation required to merge**
- [x] Clean Debug and Release configure/build/tests succeed without Nitride present
  as a dependency; repeat with an approved dependency cache/offline mode after fetch.
- [x] Checksum mismatch and wrong/dirty explicit dependency override are rejected.
- [x] Focused sanitizer smoke tests run; metadata/logs identify actual compiler/SDK.
- [x] `codesign` verification and explicit `auval -v aumf <subtype> <manufacturer>`
  succeed in the logged-in GUI context on the installed Voxide shell.
- [x] Identity does not collide with/replace Nitride; install helper only touches
  Voxide-owned paths, and tests use temporary roots.
- [x] License decision and zero-cost setup instructions reviewed. Shell is explicitly
  described as pass-through scaffolding, not a working harmonizer.

**Agent handoff — update before merge**
- Major decisions: local-only AGPLv3 use explicitly approved by user. Pinned JUCE
  8.0.15; arm64/macOS 15 deployment; identity `aumf / Vx00 / Vxid`, bundle
  `com.voxide.audio.voxide`. Mono/stereo main input, optional mono/stereo sidechain,
  stereo output; explicit `sourceBus` Main input/Sidechain choice (default Main)
  routes channel 1 to both outputs in normal and bypass processing. AU bus
  enablement cannot indicate an actual source connection. The routing choice is
  host-automatable and persisted as shell-v2; preserve its ID/meaning in later PRs.
  See `docs/DECISIONS.md` and `THIRD_PARTY_NOTICES.md`.
- Learnings/evidence: post-review fresh cached/offline Debug/Release each pass 5
  CTest suites, and ASan/TSan each pass 2 focused
  suites. Independent review found five gaps plus a follow-up rollback race, all
  addressed; see `docs/CODE_REVIEW.md`. Validation now includes 96 native device-free
  AU cases, generated privacy metadata, 20 Python tooling cases, extracted-source
  integrity guards, and deterministic installer collision/rollback regressions.
  Actual Release AU ad-hoc signing and GUI-context `auval` passed. Exact commands,
  run paths, environment, initial diagnostic failure, and limits are in
  `docs/VALIDATION.md`; the updated stable-input fresh offline run and installed-AU
  validation passed. Nitride stayed read-only and is not a build dependency.
- Reflections/next-agent cautions: shell only, MIDI intentionally ignored; no
  harmonizer/listening/Logic claims. Preserve prior owned AU bundles outside AU
  discovery, not as duplicate identities under Components. Keep installation
  separate from checks, retain logs, and never regenerate expected audio implicitly.
  Next action is PR 01's actual Logic routing proof, not engine selection.

### PR 01 — Automated routing diagnostics and manual Logic acceptance

Depends on: PR 00 and user Logic session.

**User-approved workflow revision:** stop scripted Logic UI operation. Complete
the engineering PR using the actual built AU in a device-free native host and
production-processor tests. Supply one human-operated Logic checklist/test kit.
Software merge readiness and actual Logic acceptance are separate; native results
must not close the manual host gates or justify advancing to engine selection.

**Scope / TODO**
- [x] Add diagnostic pass-through and bounded timestamped MIDI/audio logging outside
  the audio callback (fixed-capacity telemetry, no console/file writes in render).
- [x] Prepare reusable fixtures and instructions for a human-created disposable
  Logic project: AU MIDI-controlled effect on an instrument track, recorded vocal
  via sidechain, MIDI region and live input. Do not generate a fictitious `.logicx`.
- [x] Document proposed recorded-source and physical-input routes, exactly one audible lead,
  input monitoring, record-enable, source output suppression, and direct-monitor split.
  These instructions are not observations that the routes work in Logic.
- [x] Record the actual hardware/software environment without serials or hostname.
  CoreAudio defaults/installed Logic version are recorded; actual Logic-selected
  devices and monitoring configuration remain manual acceptance items.

**Validation required to merge**
- [x] Automated native-AU and production-processor routing/MIDI/transport/state
  tests pass with a machine-readable report and explicit coverage boundaries.
- [x] Diagnostic queue/logging, overflow/stale handling, parser negative controls,
  and existing Debug/Release/sanitizer regression checks pass.
- [x] Publish the human checklist and evidence boundaries; manual gates below stay
  pending until observed, even if the engineering PR is merged.

**Manual Logic acceptance — not inferred from software checks**
- [x] User-operated Logic captures identify routing-003 and show recorded-source
  audio on Main plus MIDI at the same instance, including within-block offsets.
- [ ] User-coordinated physical input test works while stopped and during recording;
  focus/record-enable/mute/solo behavior is documented, not assumed from `auval`.
- [ ] No doubled lead, feedback route, stale telemetry, or stuck diagnostic notes.
- [x] User comparison documents direct physical-input monitoring working with
  Low Latency Mode off/on; the recorded track-fed route goes silent in that mode.
  This is a route-specific observation, not resolution of the track-fed failure.
- [x] User reports save/quit/reopen preserves the working direct-input setup.
- [ ] Capture fresh audio/MIDI telemetry after recall, including release to zero;
  this is not established by the general project-reopen report.

**Agent handoff — update before merge**
- Major decisions: user approved stopping scripted Logic UI operation. Use the exact
  built AU in the native host plus production-processor tests, then one reusable
  human checklist. Source parameter/state identities are unchanged; no harmony DSP.
  Only the opt-in editor consumer writes metadata logs, never PCM or render-thread I/O.
- Learnings/evidence: see `docs/LOGIC_ROUTING.md` and `docs/ROUTING_VALIDATION.md`.
  Native tests include time-varying samples, transport/reset, fresh-instance state
  and MIDI API acceptance; delivered MIDI offsets are asserted separately at the
  processor layer. Initial `auval` success had a stale version, now explicitly rejected.
  Independent right-pane review found three diagnostic reliability/counter issues;
  all were fixed with regressions and the focused rereview found no remaining
  concrete issues. Final post-review offline qualification passed Debug/Release
  (5/5 suites each) and focused ASan/TSan (2/2 each); evidence:
  `build/checks/20261020T210313Z-fc7eb798/`. See the review record in
  `docs/ROUTING_VALIDATION.md`; current diagnostic build is routing-003.
- Reflections/next-agent cautions: the user subsequently tested their own audio/MIDI
  in Logic. A capture confirms Main-bus audio plus MIDI delivery, but ends with two
  diagnostic held keys. The user reports Low Latency Mode silences the route and a
  track-fed live-source recording produces no visible Voxide signal. The user then
  confirmed direct physical-input selection works and records. A follow-up log
  shows continuing callbacks with silent input/output during the reported Low
  Latency Mode test, but does not identify the upstream cause or toggle timing.
  The user subsequently confirmed direct physical-input monitoring through Voxide
  works with Low Latency Mode off/on, with the Live Source track at No Output.
  The user also confirmed save/quit/reopen works for that setup. This is the
  working live route; the track-fed mode failure, complete monitoring state matrix,
  single-lead isolation and fresh post-recall MIDI/release telemetry remain open. Do not
  mark these gates passed from native tests or resume brittle UI automation. The
  user has a microphone, not an external MIDI controller; Musical Typing is a labeled
  manual alternative. Logging stops when its editor closes and is not persisted.

### PR 02 — Freeze requirements, corpus, fixtures, and measurement protocol

Depends on: PR 01 and available recordings/listeners.

**User-approved sequencing revision (2026-10-22):** merge the reviewed/tested PR 02
engineering foundation now and defer detailed manual annotations to actual tracker
development. PR 03 development may proceed under that explicit deferral, not a
claim that the human gates passed. Numerical targets, required expressive cases,
independent review, holdout safeguards and final quality requirements are unchanged.
Remaining musical semantics must still be approved before freezing note-selection
behavior. Full tracking/architecture/product qualification still needs trustworthy
references; do not use the failed C whistle guide as ground truth.

**Scope / TODO**
- [x] Freeze the user-approved numerical targets, extending shifts to ±24 semitones,
  in `docs/evidence/pr-02/contract.json`; do not claim an engine meets them.
- [ ] Close remaining musical/source/listening decisions before tuning or holdout use.
- [ ] Gather/annotate the no-cost corpus and seal the holdout split; retain rights.
- [x] Generate known-F0/resonance/noise fixtures from versioned scripts/seeds.
- [x] Define JSON manifests for sources, sample-indexed targets/MIDI, configurations,
  metrics, raw reports, listener IDs, and environment/build identities.
- [x] Implement basic WAV/control rendering and independent metric/annotation tools;
  specify uncertainty rules, stable-frame regions, voiced-boundary exclusions,
  recognition settling criterion, and onset timestamp definitions.
- [x] Document exact proposed RMS/mix levels, comparison tolerance, listener-session
  design, uncertainty rules and defect severity definitions. No per-engine masking EQ.
- [ ] Approve the proposed listening/annotation procedure with actual reviewers.

**Engineering validation required to merge — under the approved sequencing revision**
- [x] Re-running fixture generation with the same seed produces identical hashes;
  ordinary checks never regenerate expected results.
- [x] Scripted validators reject missing files, bad hashes, invalid note ranges,
  inconsistent timestamps, unsafe holdout access and unapproved grading contracts.
- [x] Known synthetic pitch/delay/resonance errors are recovered by measurement tools;
  deliberate off-by-one and wrong-octave controls are detected.
- [x] Independent code review fixes are re-reviewed and all automated regressions pass.

**Deferred human/qualification gates — remain required, not marked passed**
- [ ] Two annotators review actual vocal agreement and uncertain regions.
- [ ] Development/holdout separation and the full budget/criteria have explicit
  approval; unavailable singers/listeners are recorded as blockers, not waived silently.

**Agent handoff — update before merge**
- Major decisions: numerical plan targets approved, with ±24-semitone shifts at
  the user's request. Other musical semantics remain open. No DSP/engine/product
  changes; Python tooling is standard-library-only, offline and does not access
  devices, install packages, discover recordings or operate Logic. See `docs/EVALUATION.md`.
  User approved engineering merge and deferring detailed annotations to tracker
  development; this changes sequencing, not targets or final acceptance requirements.
- Learnings/evidence: 28 versioned mono PCM24 analytic probes span both rates,
  including two-octave output extremes, exact controls and oracle references.
  Post-review `make evaluation-check` passed 37 tests and 14 calibration measurements
  with stable source fingerprints; evidence: `build/evaluation-checks/20261021T183802Z-23a2dc5c/`.
  Post-review offline Debug/Release (5/5 each) and ASan/TSan (2/2 each) passed; evidence:
  `build/checks/20261021T183812Z-afea1991/`. See `docs/EVALUATION_VALIDATION.md`.
  Independent review found seven tooling/schema issues; fixes include bound PCM/
  timebase metadata, application chronology, shared contract enforcement, complete
  holdout approval checks and corrected analytic onset references. Additional
  multi-octave/overflow guards were added. Generator v2 changes no WAV bytes and
  preserves the original baseline privately. Independent focused rereview found no
  remaining concrete issues; all final post-review reruns passed.
  The user subsequently supplied three AIFF pilots and explicitly permitted local
  mono copies/excerpts. Lossless conversion and three 12-second slices passed
  sample-identity/format checks; all originals remain unchanged. The user confirms
  solo, untuned recordings of one singer; dry status stays provisional. Three
  development-only sources are registered privately, with no holdout, actual
  annotation-reviewer assignments or completed annotations. The user passed the
  initial source-audio listening check for all three; automated pitch proposals
  remain separate, unverified annotation aids, not reference truth or product tests.
  A private voice-plus-whistle packet is ready at `evaluation/pr-02/listen-pitch-001/`
  for coarse single-user review. The user reports a/b satisfactory and c less steady
  with possible unintended notes. C needs issue localization/attribution; retain it
  as a challenge case. No proposal has been accepted as human reference truth.
  The user clarifies C's issue is in the gappy/off-timed whistle, and the singing
  intentionally includes rhythm and bends. Treat C as required expressive input,
  not an excluded bad take. The offline review aid needs a cleaner comparison;
  this is not an established Voxide render/latency failure or a reason to snap bends.
  A bounded shorter-window/gating comparison exposed remaining false-tone versus
  gap/timing tradeoffs and was not promoted as a fix. No more user listening on
  that guide is requested. Manual/independent references remain needed for C;
  preserve the source and failed diagnostics rather than tuning away expression.
  Do not infer permission to inspect
  unrelated audio libraries.
- Reflections/next-agent cautions: engineering test success does not complete the
  PR's human/approval gates or unlock engine selection. Annotation agreement is not
  truth, uncertain frames are excluded rather than counted correct, and missing
  estimates remain failures in the denominator. Holdout is singer-separated and
  requires a complete corpus, explicit settings approval and an unchanged seal;
  this is a workflow guard, not an OS sandbox. Never tune on repeatedly opened holdout.

### PR 03 — Causal F0/voicing tracking and deterministic harmony selection

Depends on: PR 02 engineering foundation. Detailed vocal references are deferred
into tracker development by the user-approved PR 02 sequencing revision, but remain
required before claiming actual vocal accuracy or closing qualification go-gates.

**Scope / TODO**
- [x] Implement a bounded causal YIN-family baseline and one multi-candidate causal
  variant; document window/hop, history, smoothing, and any lookahead separately.
- [x] Produce timestamped F0/confidence/voicing, with defined low-confidence behavior.
- [x] Implement scale-degree offsets and absolute MIDI targets for three slots;
  deterministic allocation, duplicate notes, note-off, overflow, and >3-held-note policy.
- [x] Define vibrato/scoop handling, scale-boundary hysteresis, and silence/seek/reset
  behavior without processing the original lead.

**Validation required to merge**
- [x] Exact expected-note tests cover approved scales/roots, accidentals, ties,
  limits, rapid changes, duplicate/overlapping MIDI, event ordering, and releases.
- [x] Cold/continuous response, F0/octave/voicing/false-trigger metrics per register
  on analytic development material, both compiled variants; approved private vocals
  produce ungraded causal traces only, never fabricated reference truth.
- [ ] Trustworthy real-vocal per-register accuracy/response and independent human
  expression/listening qualification (explicitly deferred, not claimed passed).
- [x] Boundary-vibrato no-chatter and immediate deliberate anchor-change tests;
  analytic rhythmic bends/missing fundamentals retained. Tracker response lag and
  offset voicing hangover are measured failures, not smoothed away or hidden.
- [x] Block partitions 32/64/128/257/512/1024 and varying sequences preserve event
  semantics; reset/seek does not use future samples or stale history.
- [x] Allocation-audit self-test detects deliberate render allocations, then reports
  none in exercised tracker/selector callbacks; sanitizer tests pass.
- [x] Report any target misses honestly. A reproducible research result may merge,
  but unresolved required tracking failures block the architecture go-decision.

**Agent handoff — update before merge**
- Major decisions: approved musical defaults with broad 12-TET/custom scales;
  independent degree/octave controls; fixed-storage YIN and multi-candidate variants,
  2-sample preprocessing, newest-anchored 512-sample comparisons and ~5 ms hop.
  Engineering constants, reset/overflow/state/telemetry details and exact semantics
  are documented in `docs/TRACKING.md` and the PR 03 musical contract.
- Learnings/evidence: compiled analytic per-register research is reproducible with
  `make tracking-check`, full native checks with `python3 scripts/check.py --full
  --offline`. Cold recognition dwell completion ~60–69.84 ms misses requirements;
  stable-frame accuracy excludes transitions and cannot establish expressive/live
  quality. Earlier exploratory failures and all private c traces are retained.
  AU remains dry, zero added audio delay; decision delay is not PDC. No commit,
  merge, push, install or Logic operation is implied by implementation completion.
  Pre-review native qualification: `build/checks/20261022T184815Z-2f9d18f8/environment.json`
  (Debug/Release 5/5 each, focused ASan/TSan 2/2 each, stable source snapshot).
  Compiled research: `build/tracking-checks/20261022T184949Z-1d67e5d9/report.json`;
  140 analytic case/variant runs, six private ungraded vocal traces, no holdout use.
  PR 02 regression/calibration: `build/evaluation-checks/20261022T184819Z-52b195b6/report.json`.
  Independent Herdr review subsequently found six concrete issues, all implemented
  with targeted regressions; see `docs/PR03_CODE_REVIEW.md`. Revised metrics also fix
  stale/dropped decisions, byte binding and the analytic generator's unclipped bends/
  integer onsets. Focused rereviews found no remaining concrete issues. Final
  post-fix native qualification passed at
  `build/checks/20261022T191729Z-d1d453c9/environment.json` (Debug/Release 5/5 each,
  ASan/TSan 2/2 each, 83 Python tests, stable source). Compiled research:
  `build/tracking-checks/20261022T191837Z-e08aa2c3/report.json` (140 case/variant
  runs, six private ungraded traces, corrected register-boundary requirements).
  PR 02 calibration/regression also passed at
  `build/evaluation-checks/20261022T191732Z-b5c88f9d/report.json`.
  Numerical recognition misses and deferred human/Logic gates remain open.
  User approved local commit/merge as an engineering/research milestone on
  2026-10-22, explicitly retaining these limitations. No push, AU install or Logic
  operation is authorized by that approval.
- Reflections/next-agent cautions: MIDI does not eliminate source-pitch tracking;
  offline Viterbi accuracy is not live causal performance.

### PR 04 — Isolated engine comparison with oracle controls

Depends on: PR 02; may proceed independently of PR 03 once fixtures are ready.

Engineering implementation is on `pr-04-isolated-engine-comparison`, based on the
merged PR 03 `510f556`. This is isolated research, not integration or architecture
acceptance. Existing deferred human-reference/listening/host gates remain open;
the actual-vocal part is not invented from old whistle guides or tracker output.

**Scope / TODO**
- [x] Build separate Signalsmith and Rubber Band evaluators using the same source,
  sample-indexed reference F0/targets, output format, and measurement schema.
- [x] Signalsmith: implement 512/128, 1024/256, 2048/512 window/hop at 48 kHz;
  document corresponding 44.1 kHz choices. Enable formant compensation explicitly.
- [x] Rubber Band: short/standard (medium comparator), formant preservation, fixed-block adapter;
  query start delay with initial ratio set. Keep its dependency out of the product.
- [x] Implement the complete 930-case static/dynamic 0/±3/±7/±12/±24 matrix, one and
  three instances, time ratio 1, with independent analytic truth/instrument controls.
- [x] Implement permission/hash-bound private development support requiring two
  completed, registered, agreeing human F0 annotations; keep missing references pending.
- [ ] Obtain actual reviewed real-vocal references/listening evidence (still deferred;
  required expressive/rhythmic c is retained, not tuned or declared unsupported).
- [x] Implement queried/actual delay, ratio-change settling, synthetic formants, artifact proxies,
  peak callback cost, state reset, and output duration/tail behavior.

**Validation required to merge**
- [x] Unity/control delay and synthetic output pitch/formants match independently
  calculated expectations or are explicitly recorded as candidate failures.
- [x] Repeat renders identify native determinism failures; deterministic transport,
  varying block lengths, native input/control chronology and FIFO wrap pass without
  dropping/repeating samples. Native waveform/reset failures remain explicitly open.
- [ ] Native repeatability/reset and complete quality/timing gates pass; intermittent
  Signalsmith fresh-instance variation and Rubber Band dynamic reset differences remain
  failed candidate gates, not adapter passes or approved architecture decisions.
- [x] Impulse tests are used at unity; non-unity timing uses suitable envelopes/
  known transitions rather than invalid raw-waveform correlation assumptions.
- [x] Optimized Release measurements retain raw timings and failed cases; source
  inspection/allocation tests identify callback hazards. Do not time sanitizer builds.
- [x] Report evidence by configuration. Discarding an engine requires a reproducible
  failure or documented incompatible delay, not a name/marketing preference.

**Agent handoff — update before merge**
- Major decisions: separate evaluator CMake project; no engine linked to AU/Standalone.
  Signalsmith Stretch 1.4.0 tag/Linear 0.6.4, Rubber Band 4.0.0 R3 short/standard,
  explicit formant preservation, source/processing/output/availability clocks distinct.
  No product engine selected; see `docs/ENGINE_EVALUATION.md` and the versioned
  `docs/evidence/pr-04/protocol.json` for exact scope and licensing/evidence boundaries.
- Learnings/evidence: engineering implementation/review/qualification completed
  2026-10-23. Independent read-only OpenCode review in the bottom-right Herdr pane
  found seven defects plus a follow-up test race; all eight were fixed and verified
  by re-review with no remaining concrete blockers. Twenty Python regressions and
  concurrent Release native/negative-control tests pass. Full stable-source product
  and engine Debug/Release/ASan/TSan checks pass at
  `build/checks/20261023T134518Z-016aaf92/environment.json` and
  `build/engine-checks/20261023T134622Z-40c258f2/report.json`.
  Corrected 930-case research completed with zero native render errors and 60/60
  instrument calibrations at `build/engine-research/20261023T134741Z-81ad9ed5/report.json`.
  Per-configuration failures, unresolved observers and raw evidence are preserved;
  see `docs/ENGINE_EVALUATION.md` for the full table and limitations. No candidate
  passes all numerical gates. Native reset differences affect overlapping audio,
  not just padding. PR 02 regression/calibration also passed at
  `build/evaluation-checks/20261023T135351Z-65e2904e/report.json`.
  Private preflight retains three sources pending actual human references under
  ignored `evaluation/pr-04/20261023T135351Z-84ae23f2/`, with complete build provenance.
  Product source, fixtures and approved contracts are unchanged. User approved local
  commit/merge on 2026-10-23 as an engineering/research milestone, retaining all
  negative candidate results and deferred human/Logic gates. No push, installation,
  host acceptance or engine selection is authorized by that approval.
- Reflections/next-agent cautions: defaults are not low-latency proof; Rubber Band
  is a quality comparator, not a presumed live solution; oracle tests bypass real tracking.

### PR 05 — Complete three-voice interaction and consonant treatment

Depends on: PRs 03–04.

Research integration remains separate from the AU/Standalone until the later
architecture go-decision. Existing tracker/engine/human/host failures remain gates,
not assumptions that can be inherited as passes. No commit/merge/push or installation
is authorized by the implementation request.

**Scope / TODO**
- [x] Integrate shared tracking/selection with three independent shifting states,
  explicit source-time alignment, bounded ratio transitions, and controlled summing.
- [x] Implement and render engine-native versus one common confidence/voicing-aware consonant
  treatment; crossfade mixed boundaries and control reinforced consonants.
- [x] Log source timestamp, F0/confidence, target, applied ratio/time, voicing state,
  and output alignment into bounded non-render-consumed telemetry.
- [x] Run oracle F0 + prescribed targets; live F0 + prescribed targets; and complete
  scale/MIDI modes. Render upper/lower/mixed three-voice voicings and exposed stems.
- [x] Define explicit 15/100 ms fixed reserves and lead alignment/latency reporting;
  make configuration changes explicit/stopped, persist settings and qualify both
  as experiments, retaining failures. No hidden offline-bounce quality switch.
- [ ] Accept a live/mix configuration or consonant policy. No tested complete live
  path qualifies; the policy comparison is not an accepted consonant workaround.

**Validation required to merge**
- [x] Execute transition/source-time/three-voice assignment tests and expose missed
  deadlines, slow MIDI application and native repeatability failures explicitly.
- [ ] All three voices meet complete quality/response gates without unwanted
  clicks/bursts/flams or assignments; analytical failures and listening gates remain.
- [x] Check analytic breathy/z/s/sh/plosive/silence/phrase-tail/noise/bleed cases in
  native/treated stems and both complete sums; retain raw and proxy evidence.
- [ ] Actual-vocal articulation/listening qualifies the complete blend; no common
  consonant copying/gating treatment is accepted from synthetic proxies alone.
- [x] Lead unity/null test passes with documented delay; summed output is finite
  and respects fixed gain/headroom without adding a masking limiter.
- [x] Three-voice delay/response/CPU and correctness tables are produced for all
  retained configurations; direct-lead and software-aligned routes are distinguished.
- [x] ASan/TSan, deterministic adapter allocation controls, malformed automation,
  stopped reconstruction and concurrent handoff tests pass. Native callback
  allocation failures are separate, retained candidate gates—not zero-allocation passes.
- [ ] Native processing meets zero-allocation and complete performance/quality
  requirements; all 208 Rubber Band cases still allocate on callbacks after the
  retrieval-caller logging correction. Logic/device acceptance remains pending.

**Agent handoff — update before merge**
- Major decisions: separate `InteractionEvaluation/` project using unchanged PR03
  tracker/selector and PR04 adapters/pins; exactly three independent instances.
  Explicit source anchor, analysis reserve, fixed 15/100 ms total delivery presets,
  bounded log-ratio transitions, unity direct/aligned lead and controlled sums.
  One common 10 ms confidence/voicing crossfade policy is an ablation, not an
  accepted consonant workaround. Stopped reset reconstructs graphs rather than
  trusting PR04's failed dynamic native reset. See `docs/INTERACTION_EVALUATION.md`
  and `docs/evidence/pr-05/protocol.json` for precise clock/gain/lifecycle scope.
- Learnings/evidence: final full source-stable product/interaction Debug/Release/
  ASan/TSan qualification passed at `build/checks/20261023T160144Z-90bc0fa8/environment.json`
  and `build/interaction-checks/20261023T160242Z-0053b0ee/report.json`. 112 Python
  regressions (nine PR05), seven native tests/profile and concurrent Release native
  tests pass. Corrected full matrix: **520/520 renders**, 60/60 instrument calibration
  at `build/interaction-research/20261023T160456Z-ffcc2998/report.json`.
  All lead/null/headroom/tail/control-chronology checks pass, but 280 delivery cases,
  208 allocation cases and all 120 complete MIDI response cases fail; all 480
  non-impulse cases have sparse stable-pitch misses. Six native-repeat comparisons
  fail with identical native input/control hashes. Shared consonant treatment can
  reinforce s/sh relative to native treatment and is not selected. No range, voice
  count or numerical target was reduced. PR02 regression/calibration passed at
  `build/evaluation-checks/20261023T163326Z-66004dd1/report.json`.
  Private preflight at ignored `evaluation/pr-05/20261023T163326Z-a32800d3/` retains
  three sources pending actual human references, including c, with full provenance.
  See `docs/INTERACTION_EVALUATION.md` for tables, superseded snapshots, corrected
  sparse-dwell observer and retrieval-availability fix. That caller fix removes
  Rubber Band diagnostic I/O; prior PR04 callback evidence has a documented caveat,
  not a silent engine attribution. No independent PR05 review has occurred.
  Implementation/automated validation are complete as negative research; no engine
  or policy acceptance, merge/push, AU install, Logic/device operation or downstream
  architecture go-decision is implied. User subsequently approved a branch-only
  commit on 2026-10-23 to preserve the negative research milestone before a bounded
  architecture investigation; no merge to main is authorized.
- Reflections/next-agent cautions: acceptable individual voices may fail as a sum;
  bypassing consonants and delaying a lead are audible architecture decisions.

### Architecture follow-up — bounded investigation completed, no go to integration

Historical conclusion for the original combined live/mixing brief. The later
2026-10-24 studio-first decision permits the separate PR06A feasibility pilot
below, not an override of these failed results or a studio product go-decision.

- [x] Validate independent analytic steady/response controls before further renders;
  distinguish source support, applied musical state, native setter and audible
  observation. Unobservable vocal/low-frequency response remains pending.
- [x] Compare one zero-input-hold, source-referenced schedule and only one additional
  Signalsmith preset (256/32), retaining the original numerical requirements.
  Oracle sampled delivery reaches 6–6.53 ms and setter response 3.33–4.33 ms, but
  steady-quality and E2 nonfinite failures disqualify that fast preset.
- [x] After oracle timing passed, execute one unchanged-tracker trailing-history
  schedule; high-register cold recognition remains 40–44.90 ms, not qualified.
  No further tracker tuning or parameter sweep was performed.
- [x] Replay exact retained native calls with matching hashes across FFT backends.
  Built-in FFT removes the observed Accelerate fresh/warm repeat discrepancy in
  this limited diagnostic; it does not remove quality/safety failures or qualify
  general determinism. No backend is selected.
- [x] Capture Rubber Band allocation stacks and compare cold/reconstructed/primed
  eventful states. Same-instance priming can remove allocations in the changing
  case but breaks fresh-state waveform equivalence; it is not an accepted fix.
  Correct the separate finalized-stream restart guard in the PR05 wrapper.
- [x] Pass 120 Python regressions, product full qualification, isolated Debug/
  Release/ASan/TSan contracts and native safety probes. Final 72-case bounded batch
  retains 66 finite completions and six raw nonfinite failures. Gates remain
  failed even though engineering/sanitizer checks pass.
- [ ] Identify a candidate satisfying quality and live timing simultaneously.
  **No survivor; stop further integration under this tested scope.** A mixing-only
  result, altered observer, silent requirement reduction, excluded clip c or extra
  tuning is not an architecture go-decision. Further research/requirement decisions
  need explicit user authorization; universal impossibility is not established.
- Evidence: `build/checks/20261023T195433Z-cfca9f27/environment.json`,
  `build/architecture-checks/20261023T195433Z-ec6fbbed/report.json` and
  `build/architecture-research/20261023T200037Z-24be1cb2/report.json`.
  Method, source/provenance boundaries, exact caveats and stop decision are in
  `docs/ARCHITECTURE_INVESTIGATION.md`; frozen protocol is
  `docs/evidence/architecture/protocol.json`. No new commit/merge/push, AU install,
  Logic/device operation or private-audio access occurred.

### PR 06A — Studio-first timbre and feasibility pilot (OPEN: worker timing / musical qualification)

Depends on: retained PR03–05/architecture evidence and the 2026-10-24 direction.
This splits the former PR06; it does not renumber PRs 00–05 or call their failed
gates passed. The old combined live/mixing no-go remains valid for its scope.

**Scope / TODO**
- [x] Draft/version a studio scope/protocol alongside, **not over**, the historical
  PR02/03 contracts. Record ±12 inclusive, E2–C6, both rates, three harmonies,
  unchanged lead, scale-first and ≤100 ms complete studio delay/PDC. Existing
  scripts still use the historical contract until explicitly updated/tested.
- [x] Map retained pitch/correctness, finite-output, headroom, expression,
  reproducibility, callback and host gates separately from deferred live/MIDI/±24
  gates. Propose the processed-character/formant/listening rubric and explicit
  recorded-vocal onset/transition criteria for approval; no new numerical targets
  or formant-control algorithm are inferred from the artistic reference.
- [x] Obtain explicit approval for the small listening protocol and selected
  development sources. If proposing listening-only renders without annotations,
  implement a separately labeled permission/hash-bound route only after approval;
  do not weaken the current formal/private-reference preflight. No holdout access.
- [x] Propose at most **two existing slower/mixing configurations** and one
  short pilot passage for the initial comparison, using existing approved scale
  semantics and fixed declared voicings. No new engine/preset/parameter sweep.
  Retain current formant-preservation settings unless a change is separately approved.
- [x] Separate oracle/prescribed controls (where trustworthy references exist) from
  tracked scale-mode output to localize failures. An oracle-only win cannot qualify
  the product. Without trustworthy F0 references, keep numerical vocal accuracy
  pending rather than presenting automatic tracker proposals as truth.
  A1 calibrated the frozen meter; A2 matched 72 generated-source cases. Both modes
  fail the same output conditions despite correct source/target controls. This is
  a negative localization result, not a musical accuracy pass or vocal annotation.
- [x] After finite/headroom checks, prepare a small local listening set with lead,
  three voice stems and the complete blend, dry comparison, fixed shared gains,
  disclosed delay alignment and exact settings/build/input identities. No per-voice
  normalization, clipping/limiting, masking effects or album-audio copying. Do not
  initiate playback, capture or installation without explicit coordination.
- [x] Ask the user whether the deliberately processed character is useful and
  request timestamped defects. User reports good sound, prefers Rubber Band, and
  hears no distracting artifacts; no timestamps or numerical ratings supplied.
  This is development preference, not independent listening/product acceptance.
- [x] Before progressing, include the approved expressive/rhythmic c development
  challenge plus low/high register and inclusive ±12 boundary controls. The first
  attractive passage must not stand in for the required support/expressive envelope.
  The c listen and A2 low/high/±12 samples are executed. This checkbox records
  inclusion/testing, **not qualification**: E2 output fails, full support remains
  unqualified, and A3's expressive synthetic stage is stopped by A2. Failed coverage
  remains a blocker; it is not excluded to improve the result.
- [x] Enforce one bounded development correction/retest only after diagnosing a
  concrete defect. Preserve the original comparison; stop for a new user decision
  if neither candidate offers a credible studio path. No endless tuning loop.
  Enforced: zero DSP corrections/retests used; stopped before A3 under the approved
  protocol. The subsequently approved wrapper audit found no evidence-backed
  correction; no speculative regression was run or allowance consumed.

**Validation / exit criteria**
- [ ] Contract/protocol deltas, source permission, safe preparation and evidence
  labels are reviewed; historical contracts/fixtures/results remain immutable.
  Prior tooling safeguards were independently reviewed. The new completion drivers
  are self-reviewed/tested; independent completion review remains before merge.
- [x] Existing engineering checks and any new scope/protocol/privacy regressions
  pass. Wrong notes, lost bends/rhythm, nonfinite output or unsafe levels remain
  defects even if the user likes an electronic texture.
- [x] Report separately: user timbre preference; objective pass/fail/pending;
  exact ≥±12 coverage; source-time/duration/tail correctness; measured processing
  delay; native allocation/reset/repeatability and untested host behavior.
  Synthetic engineering results pass for Signalsmith at both tested rates/buffers;
  Rubber Band callback allocations fail. Actual-vocal/full-support/host/formal
  qualification is still explicitly pending, not inferred from the pilot.
- [ ] User decides whether the pilot merits PR06B. A positive preference result
  authorizes neither AU integration nor a final engine selection; unresolved
  technical blockers require a credible bounded resolution, not a checkbox waiver.
  **Blocked:** A2's output failures prevent recommending PR06B on current evidence.
  No automatic go, weaker pitch threshold, excluded register or correction loop.

**Agent handoff — update before merge**
- Major decisions: studio-first/scale-first/processed-character direction confirmed;
  approved Signalsmith 2048/512 versus Rubber Band R3 short on excerpt a, native
  consonants, unchanged formant settings and **C major diagnostic**. The user
  explicitly approved listening-only unannotated rendering on 2026-10-24; this is
  not a source-key or formal-quality claim. Both approved previews pass safe-export
  engineering checks. Initial user feedback is positive, with a Rubber Band
  preference and a seemingly small difference; formal measurements remain pending.
  `docs/STUDIO_PILOT.md` explains rationale
  and implementation gaps; `docs/evidence/pr-06a/studio-scope.json` and
  `listening-protocol.json` version the proposal without altering historical gates.
- Learnings/evidence: 131 Python regressions and full product qualification pass at
  `build/checks/20261024T151422Z-4b56080d/environment.json`; isolated four-profile
  contracts/16 synthetic guard runs pass at
  `build/studio-native-checks/20261024T151422Z-d822e13c/report.json`.
  Approved private comparison: ignored
  `evaluation/pr-06a/listening-20261024T151731Z-aecf92a7/report.json`, with complete
  provenance and nine hash-verified preview files under `previews/`. No automatic
  playback, fabricated pitch truth or formal quality pass. Rubber Band callback
  allocations still fail; actual-vocal accuracy/repeatability and host acceptance
  remain pending. No corrective private rerender was needed. The metadata-only
  preparer stays separate from receipt-gated `scripts/studio_listening.py`; the
  formal private preflight remains unchanged. Only excerpt a was accessed.
  Follow-up synthetic engineering matrix completed at
  `build/studio-engineering/20261024T173710Z-7dee2ad8/report.json`: 16 invocations,
  48 captures, 60 exact repeat/reconstruction/partition comparisons. Both engines
  have zero observed overdue callbacks; Signalsmith has zero callback allocations
  while Rubber Band allocates in every capture. Stopped reconstruction passes for
  both; native-reset and actual audio-thread host handoff are not thereby qualified.
  136 Python/product checks and isolated four-profile probe safety pass at
  `build/checks/20261024T173235Z-bc6e8e1b/environment.json` and
  `build/studio-engineering-checks/20261024T173235Z-93c09625/report.json`.
- Clip-c execution: original source-specific trial is retained at ignored
  `evaluation/pr-06a/listening-20261024T180305Z-d5b0ddb2/`; both native runs complete,
  Signalsmith passes safe-export checks, Rubber Band's mix exceeds the extra 0.5
  preview ceiling. No full-scale overs were found in intended previews. Package
  withheld; no gain fitting, rerender or automatic playback. Exact private peak
  diagnostics and original artifacts are retained. 139 Python/full-product checks
  pass at `build/checks/20261024T180129Z-236f32fa/environment.json`; DSP binaries
  remain unchanged from the four-profile-qualified engineering build.
- Approved common fixed **0.5 playback export** completed from retained clip-c
  outputs at `evaluation/pr-06a/playback-half-20261024T183809Z-647c08bb/previews/`.
  Nine finite, hash/sample-verified WAVs each retain 12.6 seconds and meet the
  unchanged 0.5 ceiling; dry, both mixes and all mix-gain stems share the same trim.
  No DSP rerender, limiter, altered relative mix or per-candidate normalization.
  The original 243-artifact archive/withheld report and consumed source approvals
  stay unchanged. Additive protocol/receipt, consumed export claim and private
  `export-validation.json`/package integrity bind this new playback-only result.
  Full product/four-profile checks and **148 Python tests** pass at
  `build/checks/20261024T183649Z-e1476dbc/environment.json`; native binaries unchanged.
- Clip-c feedback received: tentative Rubber Band preference, but the user calls
  the difference minimal and does not care which is selected on subjective sound.
  Bound private `user-feedback-001.json` is appended to the half-level package;
  no new artifact absence, articulation/bend rating or formal quality pass is
  inferred. Do not repeat fine-grained A/B tuning to force a stronger preference.
- Verification-gap review/proposal complete: `docs/STUDIO_VERIFICATION.md` and
  `docs/evidence/pr-06a/signalsmith-verification-proposal.json`. Retained synthetic
  JSON review finds all 12 voice/case groups in the four historical scale/mix cases below
  their sparse stable-pitch target, despite clean delivery. Historical observer and
  guard differences limit attribution; no retrospective regrade. First isolate
  meter/tracker/control/native contributions, not another tiny preference/CPU contest.
- Proposed **Stage A**, now synthetic-execution-approved by the user:
  synthetic-only meter controls (36 fixtures), matched prescribed/tracked steady
  captures (72), then eventful delivery (16), with stop points and no tuning loop.
  No proposed runs have been executed. Full support/catalog coverage and human
  qualification remain pending. Source-bound vocal repeats and evaluation-host
  operation require separate approvals; consumed a/c receipts cannot authorize them.
  Signalsmith is still provisional; Rubber Band's allocation failure is not waived.
  PR06B go remains pending. No UI, playback, installation or holdout expansion.
- Tooling repair/review complete: all five initial findings are closed, including
  legacy proposal relocation and packet-causality follow-ups. **45 studio / 165
  total Python tests** and full product Debug/Release/ASan/TSan pass at
  `build/checks/20261024T194129Z-dff8fbbe/environment.json`. Additive retained
  synthetic revalidation of 48 captures/four guard timelines passes new checks;
  all 921 original synthetic artifact hashes remain unchanged. Final repair
  evidence is at `build/studio-review-fixes/20261024T194145Z-23a3bc59/`; engine
  sources/binaries and private outputs/claims remain untouched. See
  `docs/evidence/pr-06a/review-fixes-001.md`. No Stage A capture or new engine render.
- A1 complete: 36/36 calibration fixtures pass at
  `build/studio-verification/20261024T200210Z-edb48fa4/report.json`; 28 positives each
  have 100% eligible observations within 25 cents and all eight negative controls
  behave as expected. No engine executions in A1; calibration and artifacts are
  append-only and the meter is unchanged. Driver qualification passes 176 tests at
  `build/checks/20261024T200029Z-67276484/environment.json`.
- A2 executed: `build/studio-verification/20261024T220613Z-10d6c48c/report.json`.
  All 72 captures pass source/target/control, finite/duration/lead-null/sum, delivery
  and callback checks; zero allocations/overdue callbacks. Each mode passes 19/36
  cases and fails the same 17. Output pitch passes only 144/216 voice groups.
  This cannot be attributed to the tracker alone. A3's 16 cases are correctly
  unexecuted, not reassigned. No DSP correction/retest was applied. Driver checks
  pass 186 Python/full-product tests at
  `build/checks/20261024T220420Z-2511d1ba/environment.json`.
- Historical post-A2 checkpoint: review the negative result and decide whether to authorize a
  diagnosed bounded correction/retest or stop/reconsider this approach. There is
  **no next PR advancement** while PR06A's credible-path gate fails. See
  `docs/STUDIO_VERIFICATION_RESULTS.md`; independent completion-code review also
  remains before any merge. No further native/private/host run or another partial
  merge is authorized by the failed experiment. Current completion work is uncommitted.
- Subsequent decision: the user **approved** one evidence-backed wrapper/
  configuration correction and regression, not tracker changes. The
  [audit](evidence/pr-06a/wrapper-audit-001.md) found no demonstrated integration
  defect or justified replacement. Stop/reject the current 2048/512 configuration
  rather than run speculative tuning. No DSP correction/native regression or
  allowance consumption occurred. This supersedes the pending-approval action
  immediately above, not the original failures or stopped A3/PR06B gates.
- New authorized feasibility task: diagnose the existing Rubber Band callback
  allocations. The frozen eight-capture
  `docs/evidence/pr-06a/rubberband-allocation-diagnosis-001.json` tests exactly one
  silence-only stopped-preparation hypothesis against fresh graphs; it neither
  changes the product wrapper nor repeats the rejected exact-audio priming. Keep
  all original allocation/pitch failures. No engine selection, PR06B go or private/
  host operation is authorized by this diagnostic.
- Diagnosis completed: all eight captures retained at
  `build/rubberband-allocation-diagnosis/20261024T234246Z-23cf5785/report.json`.
  Prepared callbacks/finish allocate zero in the samples, but 4/4 paired comparisons
  fail all three output lengths and zero-lag body comparisons. Stop/reject the
  preparation without retries. Attribution and a disclosed/repaired diagnostic
  retrieval-warning artifact are recorded in
  `docs/evidence/pr-06a/rubberband-allocation-diagnosis-001.md`.
  Proposed next decision: approve or reject an isolated worker-owned rendering
  feasibility prototype under unchanged ≤100 ms/PDC and callback/musical gates.
  No new architecture implementation, product integration or final engine choice
  is authorized by this completed diagnostic.
- Subsequent worker authorization (2026-10-25): the user approved background
  processing to resolve the allocation blocker under unchanged requirements.
  `WorkerEvaluation/` implements fixed SPSC proxies with worker-only native
  ownership, stopped/joined lifecycle, offline coordination outside callbacks and
  fail-closed harmonies on missed delivery. The frozen 14-capture protocol compares
  the unchanged reference with paced/offline workers at both rates/buffers and
  includes deliberate stall negatives. Native results are pending; no product
  integration, private replay, engine selection or PR06B go follows automatically.
- Worker result: `build/worker-feasibility/20261025T140514Z-92f67612/report.json`.
  All 12 normal captures (references plus paced/offline workers) pass their scoped
  gates. Eight normal worker captures allocate zero on callbacks; all 14 waveform/
  partition comparisons are exactly equal. Lead, controls, three voices, duration/
  tail and fixed 100 ms software alignment are unchanged. Worker allocations remain
  visible, not waived/eliminated. Both stall negatives detect missed delivery and
  latch harmonies silent without altering lead; the 48 kHz negative additionally
  starts its first callback late and misses the frozen scheduled-finish gate.
  **Overall status stays failed**, not a retroactive pass. The 14-capture claim is
  consumed; no retry or additional native matrix ran. See
  `docs/evidence/pr-06a/worker-feasibility-001.md` for precise clocks and next gates.
  There is now a working normal-case solution to native callback allocations.
  Resolve the explicit timing/review gate, then musical verification on this exact
  architecture; do not loop back to rejected warmups or waive the original pitch,
  challenge-c, support, host or independent-reference requirements. PR06B remains
  unstarted and no product merge is authorized.
- User-approved checkpoint/handoff (2026-10-25): self-review and commit current
  changes as an **incomplete PR06A checkpoint**, without merging or pushing; branch
  `evaluation-au-prototype` from it. See
  `docs/evidence/pr-06a/checkpoint-review-001.md`. Freeze further engine research.
  The next implementation task is the minimal evaluation-only AU: key/scale,
  three harmonies, unchanged lead and current worker direction. This is not PR06A
  closure, a production engine selection or a waiver of timing/musical/host gates.
  No AU implementation, installation or Logic operation occurs during checkpointing.

### PR 06B — Studio qualification and architecture go/no-go (evaluation AU implemented; qualification open)

Depends on: PR06A's useful pilot/credible technical path, approved versioned studio
contract and the formal source/reference/listener resources. This retains the
substance of the former PR06 formal qualification, **after** the small pilot.

**User-approved sequencing exception (2026-10-25):** build a minimal, separately
identified evaluation-only AU before closing PR06A, not production integration or
an assertion that formal qualification passed. Branch `pr-06b-evaluation-au` starts
at checkpoint `8f3a982`. Scope, build commands, real-time-only limitations and
remaining gates are in `docs/PR06B_EVALUATION_AU.md`. No installation/Logic/private
source operation or automatic commit/merge/push is authorized by this exception.

**Evaluation-AU implementation checkpoint (closed locally; qualification open)**
- [x] Separate local `voxide Studio Eval` component (`aufx / Vx6b / Vxid`), without
  changing the product component or its parameter/state compatibility.
- [x] Explicit key/built-in scale, three +2/+4-step/octave voices, unchanged lead
  at 100 ms alignment, harmony trim/enable, bypass, evaluation state and visible
  fault/restart controls. Native workers and graph reclamation stay off callback;
  the AU excludes the research malloc interposer.
- [x] Release build and five focused functional checks cover processor/worker contracts, native
  audibility, uninstalled AU impulse/100 ms latency, and signed arm64 bundle/system-
  dependency validation. ASan/TSan fake-engine contracts and 204 Python tests pass.
  Final delivery evidence is at `build/pr-06b-artifacts/ready-20261025-01/report.json`;
  build/use scope is recorded in `docs/PR06B_EVALUATION_AU.md`.
- [ ] User-coordinated installation/Logic audition; none performed. Fast offline
  bounce deliberately remains unsupported (explicitly marked delayed-lead-only),
  not a passing harmony render. Formal musical/support/host/listening gates below
  are unchanged and open. See `docs/PR06B_EVALUATION_AU.md`.

The prototype implementation task is closed in a local branch commit at the user's
request, **not completed PR06B qualification or a PR07 go**. All PR06A failures and
consumed experiments remain unchanged. See `docs/evidence/pr-06b/closeout-001.md`.
Work remains on `pr-06b-evaluation-au`; no merge, push, installation or Logic
operation is included in closeout.

**Scope / TODO**
- [ ] Freeze configurations and the processed-character/listening rubric before
  formal listening; confirm all required reference, consent and split approvals.
  Open holdout only under its original explicit authorization/locking rules.
  The staged native/host feasibility proposal in `docs/STUDIO_VERIFICATION.md` is
  not that formal approval or a substitute for full-support/human resources.
- [ ] Render coded listening sets with known synthetic controls, degraded anchors,
  hidden duplicates and matching targets/gains. Include exposed stems and the
  complete three-voice sum; align delay only for declared timbre comparisons.
  The album passage is artistic context, not a perfect transformed reference.
- [ ] Optionally use already-owned Waves/Melodyne references if appropriate;
  absence is disclosed and never creates a purchase/trial dependency.
- [ ] Combine independent processed-character/articulation/stability/usability
  findings, timestamped defects, objective pitch/formant diagnostics, ≤100 ms
  processing/PDC, callbacks, reset/repeatability and licensing. Report per-singer,
  register, ±7/±12 range and worst cases, including expressive challenges.
  Actual host evidence cannot come from the current dry shell. A pre-go research
  AU adapter would require its own explicit evaluation-only approval and separate
  component identity, as proposed in `docs/STUDIO_VERIFICATION.md`; absent that,
  retain the host gate pending rather than integrating the product before go.
- [ ] Freeze any remaining bounded tuning/retest allocation before opening holdout;
  do not reuse the PR06A correction allowance to justify repeated tuning on holdout.
- [ ] Select a free studio architecture only if **all approved first-milestone gates**
  pass. Formal accuracy cannot be inferred from informal preference or an oracle
  bypass. Publish an explicit studio no-go if blockers persist.

**Validation required to merge / product go**
- [ ] Identity-key separation, levels, alignment, duplicates, listener independence,
  uncertainty and score aggregation are documented and independently checked.
- [ ] The complete declared ±12/E2–C6/two-rate/three-voice scope is supported;
  no failed register, octave shift, case or listener disagreement is hidden.
- [ ] Independent human references/listening and retained numerical correctness,
  safety, allocation and reproducibility gates pass under the approved studio
  contract. Missing observations remain pending, not waived by the pilot.
- [ ] User approves an explicit **studio-scale go/no-go**. PRs 07–10 remain blocked
  without this go; a negative engineering report may be preserved without it.
  This does not qualify live use, MIDI mode or ±24, and authorizes no automatic
  installation, purchase or public distribution.

**Agent handoff — update before merge**
- Major decisions: pending — chosen studio configuration or explicit blocker,
  revised contract identity and user-approved go/no-go.
- Learnings/evidence: pending — coded scores, defects, objective/host constraints
  and selection rationale. Distinguish original and studio-only qualification.
- Reflections/next-agent cautions: artistic preference informs the declared timbre
  goal but never converts pitch/safety failures or missing evidence into passes.

### PR 07 — Product processor, minimal controls, automation, and state

Depends on: PR06B's explicit studio-scale go-decision, not PR06A preference alone.

**Scope / TODO**
- [ ] Integrate the selected architecture into the AU shell and shared test target;
  remove evaluation alternatives from normal product linkage, not from evidence.
- [ ] Add only necessary first-milestone controls: key/approved scales, three
  harmony degree settings, voice levels/enables, original level and explicit studio
  processing configuration only if evidence requires it. Defer the MIDI-mode user
  workflow; preserve existing parameter/state IDs and compatibility rather than
  deleting or reinterpreting them. Do not expose unqualified modes as ready features.
- [ ] Use clear readable native controls, keyboard access, meaningful labels/units,
  and modest input/pitch status. No preset ecosystem or ornamental feature expansion.
- [ ] Freeze parameter IDs, ranges, defaults, state schema, and component identity;
  persist musical/voice/processing settings but not transient held MIDI notes.
  Range/state changes for the studio milestone need explicit migration tests;
  this planning revision changes no executable range or saved state.
- [ ] Implement validated state restore, correct host notification and bypass/reset/
  silence behavior, keeping UI/document locks and file work off rendering.

**Validation required to merge**
- [ ] UI and headless/processor renders use the same production DSP and agree.
- [ ] Parameter automation/readback and save/restore reproduce settings/audio;
  malformed/truncated/out-of-range state is handled safely.
- [ ] Editor create/destroy, state restore, and automation concurrent with rendering
  pass focused lifetime/concurrency checks; no stuck notes or stale UI overwrite.
- [ ] UI controls are operable/readable at supported sizes, do not steal host
  keyboard input, and introduce no extra product controls or unqualified MIDI claims.
- [ ] Regression audio and approved three-voice behavior remain within frozen limits.

**Agent handoff — update before merge**
- Major decisions: pending — frozen host/state contract and necessary controls.
- Learnings/evidence: pending — interaction checks, serialization fixtures, caveats.
- Reflections/next-agent cautions: once host IDs/state ship, preserve their meaning;
  UI polish must not alter processing or conceal the selected configuration's limits.

### PR 08 — Recorded-vocal AU/Logic compensation, recall, and bounce

Depends on: PR 07 and user Logic session.

**Scope / TODO**
- [ ] Add installed-AU integration tests and user-coordinated disposable Logic
  projects using recorded vocals, the explicitly supported source bus and scale
  automation. Keep the existing track-fed/Low Latency Mode routing limitation
  visible; dry-shell routing success is not harmony/PDC acceptance.
- [ ] Verify latency property/notifications, host compensation, bus layouts,
  source-audio/scale-automation sync, bypass and stopped/configuration changes;
  retain MIDI delivery/state regressions without claiming MIDI musical qualification.
- [ ] Exercise cycle, seek, stop/resume, mid-phrase start, scale/key/degree changes,
  bypass, silence and reset in the recorded-vocal workflow, including re-acquisition
  without missing the first syllable or leaking a prior phrase.
- [ ] Preserve existing MIDI-state safety/regression behavior without promoting
  it as first-milestone product functionality. Live keyboard/recorded-MIDI musical
  qualification, duplicate notes, >3-note allocation and chase are deferred to the
  separate MIDI follow-up, not marked passed or silently removed from history.
- [ ] Document host chase limitations and expected behavior; never promise state
  reconstruction for MIDI events the host does not send.
- [ ] Compare real-time and offline bounce, start-at-first-syllable, phrase tails,
  and differing host render-block sizes. Physical live input must be recorded first.

**Validation required to merge**
- [ ] Installed build identity/`auval`/actual Logic route verified; no doubled lead.
- [ ] Unity-delay compensation reference aligns within the frozen tolerance;
  transformed-audio onset and pitch timing agree with the documented measurement.
- [ ] Document/test Low Latency Mode on/off and its effect on the supported
  recorded-vocal route; do not call a bypassed/silent harmonizer a passing render.
  State any supported-settings restriction explicitly and document that Low
  Latency Mode is inactive during bounce. No live-monitoring claim is inferred.
- [ ] Save/close/quit Logic/reopen, duplicate instance, and reopen in a fresh process
  retain settings/routing and deterministic note decisions without stale voices.
- [ ] Same deterministic configuration real-time/offline bounces meet declared
  aligned error limits, note decisions, duration, and tail coverage. Any non-exact
  differences are explained, measured, and independently auditioned before acceptance.

**Agent handoff — update before merge**
- Major decisions: pending — compensation strategy and supported host workflows.
- Learnings/evidence: pending — project hashes, bounce comparisons, manual observations.
- Reflections/next-agent cautions: PDC aligns playback, not causal live input;
  neither a saved project file nor a script proves Logic was reopened successfully.

### PR 09 — Studio session performance and final listening

Depends on: PR08's recorded-vocal host qualification and user/listener sessions.

**First studio milestone — scope / TODO**
- [ ] Measure optimized Release callbacks for three changing scale-derived voices
  on the user's representative recorded-vocal Logic session at 44.1/48 kHz and
  declared supported buffers; test variable/block boundary stress separately.
- [ ] Retain the callback occupancy/zero-overdue/allocation, finite-output,
  headroom, reset/repeatability and ≤100 ms accurate-PDC requirements. Offline
  render speed or acceptable user preference is not callback safety evidence.
- [ ] Run the existing 30-minute representative Logic soak with playback, transport,
  scale/voice automation, editor lifecycle and multiple-instance stress; no hidden
  quality switch, reduced range or fewer voices to fit the workload.
- [ ] Complete independent final listening under PR06B's approved processed-character
  rubric, including required expressive/rhythmic c and declared ±12 boundaries.
  Record articulation, stable intended notes, rhythm/bends, tails and usability,
  not just resemblance to an album texture. Resources/consent remain prerequisites.

**Validation required for the studio milestone**
- [ ] All required studio gates, host/PDC/recall/bounce checks and declared
  representative session performance pass, with raw failures/outliers preserved.
- [ ] Zero observed dropouts, stuck output, nonfinite samples or session-overload
  alerts in the declared soak. No native allocation/reset/repeatability waiver.
- [ ] User accepts the qualified recorded-vocal scale workflow and its exact
  support/limits; unqualified live/MIDI/±24 features remain explicitly deferred.
  If blocked, produce a labeled negative studio qualification report, not success.

**Agent handoff — update before merge**
- Major decisions: pending — studio configuration, tested Mac/buffers/session and
  final recorded-vocal acceptance. Analog loopback is not inferred from PDC.
- Learnings/evidence: pending — distributions, soak log, independent judgments and
  support limitations. A studio milestone is not full original-product completion.

### Deferred live/MIDI follow-up — original PR09 monitoring gates retained

Not a prerequisite for the first studio milestone and **not passed or abandoned**.
Activate only under a separately approved scope after the studio decision; no
hardware capture, installation or live research is authorized by this replan.
The original live-specific obligations remain:

**Scope / TODO**
- [ ] Use existing interface/cables to measure analog loopback baseline and the
  complete monitored route. If unavailable, retain an explicit measurement blocker;
  do not infer analog latency from Logic's display alone or buy equipment.
- [ ] Test 44.1/48 kHz and 32/64/128 frames where available; record which configuration
  is actually stable. Mixing checks also include larger/variable buffers.
- [ ] Capture repeated startup/steady-state/ratio-change recognition, audible
  response, lead/harmony delay, MIDI delay, callback P50/P95/P99.9/max and overdue counts.
- [ ] Run Release measurements without concurrent builds/profilers/sanitizers, then
  profile separately. Include three changing voices in the representative project.
- [ ] Run a 30-minute Logic soak and randomized live trials by user/second singer;
  assess playability and quality separately from aligned offline listening.

**Validation required to merge**
- [ ] Actual hardware reports meet all frozen timing/CPU/headroom gates; retain raw
  outliers and failures rather than trimming them or replacing with selective reruns.
- [ ] Zero observed dropouts, stuck notes, non-finite samples, or session-overload
  alerts in the declared soak, including transport, automation, and editor changes.
- [ ] Independent live judgments and complete three-voice quality gates pass;
  no hidden quality/voice-count reduction to fit the monitoring budget.
- [ ] Direct-monitor and software-monitor routes have separate results and no
  accidental double-monitoring. Wireless output is not a qualified live route.
- [ ] Any remaining failure is escalated; merge only an explicitly labeled negative
  qualification report if blocked, not an assertion of completed acceptance.

**Agent handoff — update before merge**
- Major decisions: pending — qualified hardware/buffers and final live/mix acceptance.
- Learnings/evidence: pending — measured distributions, soak log, independent judgments.
- Reflections/next-agent cautions: results certify only the tested machine/workload;
  do not inherit Nitride's Mac measurements or claim universal Apple Silicon support.

### PR 10 — Reproducible local handoff and qualification report

Depends on: successful studio PR09 qualification, or explicitly limited no-go
documentation. Label the outcome **studio-first scale-mode milestone**, not
completion of the deferred live/MIDI/±24 brief.

**Scope / TODO**
- [ ] Produce a concise setup/use guide and full evidence index: selected architecture,
  supported ranges/settings, Logic routing, monitoring/compensation, MIDI semantics,
  recall/bounce procedure, known failures, and reproducible commands.
- [ ] Clearly separate qualified recorded-vocal/scale/±12 behavior from deferred
  live, MIDI and ±24 behavior. Do not present an available shell parameter, research
  render or album reference as a supported/qualified product feature.
- [ ] Provide a local ad-hoc-signed build/install path with ownership checks and
  safe uninstall. Do not add paid signing, notarization, installers, or public release.
- [ ] Audit zero-spend compliance, dependency notices, source/distribution obligations,
  and private-recording separation. Do not publish/upload without user direction.
- [ ] Close each PR handoff and state final go/no-go with unresolved dependencies.

**Validation required to merge**
- [ ] Fresh checkout/cache-based build, full test profiles, installed-AU checks,
  and documented user workflow succeed with the exact candidate identity.
- [ ] Installation collision and edited-file refusal tests preserve user files and
  Nitride; ordinary checks do not touch devices, recordings, or installed components.
- [ ] Another reader can reproduce a synthetic comparison and locate the evidence
  supporting each acceptance claim. Private evidence has clear availability limits.
- [ ] No pending required gate is called passed; user accepts the final outcome.

**Agent handoff — update before merge**
- Major decisions: pending — final status and permitted sharing/use boundary.
- Learnings/evidence: pending — exact reproducible candidate and evidence index.
- Reflections/next-agent cautions: preserve known limits and negative results; a
  local qualified AU is not a notarized/public release or a commercial license grant.

## 6. Dependencies and stop decisions

1. **Foundation/routing gate (PRs 00–01):** compatible free licensing and actual
   Logic audio+MIDI route, otherwise stop early.
2. **Requirements/data gate (PR 02):** freeze acceptance and obtain credible sources/
   listeners. Without them, only synthetic feasibility can be claimed.
3. **Development preference gate (PR06A):** version/approve the studio scope,
   listening/source protocol and bounded candidate list; prepare a safe small
   comparison. User preference guides feasibility, not formal acceptance. No
   holdout, private-preflight bypass or engine purchase.
4. **Studio architecture gate (PR06B):** formal versioned ±12/scale/studio
   qualification, independent references/listening and all retained technical
   gates; explicit user-approved go. The original combined no-go is preserved.
5. **Product/host gate (PRs 07–08):** proceed only after the studio architecture
   go, then qualify actual recorded-vocal AU behavior; no automatic installation.
6. **Studio session/acceptance gate (PRs 09–10):** all required manual/measured
   studio observations must exist before declaring the limited milestone complete.
   Live/MIDI/±24 qualification is separate future work, not silently passed.

PRs 03 and 04 can be separate independent work streams after PR 02, but this plan
does not authorize subagent spawning. No other feature branches are implied.

If no no-cost engine meets the approved quality/latency/range simultaneously,
deliver reproducible failures and options to the user: stop, explicitly revise a
requirement, or separately scope new research. **Do not reinterpret the zero-spend
constraint as permission to compromise the fixed brief without approval.**

The 2026-10-24 studio-first decision is such an explicit priority/range/artistic
revision, not evidence that an engine now passes. The next exact task is PR06A's
versioned scope/listening-source protocol and small candidate proposal, **not**
another full matrix, AU integration or re-opening the holdout. A failed studio
pilot/qualification returns to a user decision rather than an automatic new search.

Cannot conclude yet: real-vocal quality, full-range live feasibility, three-voice
headroom, actual analog monitoring latency, final Logic recall/bounce reliability,
or permitted distribution under the user's preferences. These require recordings,
executed source builds, independent listening, actual hardware observations, and
license decisions. Commercial SDK quality/price remains unknown and irrelevant to
the current zero-spend implementation decision.

## 7. Primary sources for future verification

Web material was inspected during planning; pin source revisions and archive
permitted documentation during PR 00/04. These links are not measured findings.

- JUCE pinned license: https://github.com/juce-framework/JUCE/blob/91ad83ae34a81e0833b1a2b0866f54846370ae53/LICENSE.md
- Signalsmith implementation/API/license: https://github.com/Signalsmith-Audio/signalsmith-stretch
- Signalsmith author design notes: https://signalsmith-audio.co.uk/writing/2023/stretch-design/
- Rubber Band API/delay: https://breakfastquay.com/rubberband/code-doc/classRubberBand_1_1RubberBandLiveShifter.html
- Rubber Band source: https://github.com/breakfastquay/rubberband/blob/default/src/finer/R3LiveShifter.cpp
- Rubber Band license: https://breakfastquay.com/rubberband/license.html
- pYIN paper (Mauch/Dixon, ICASSP 2014): https://webspace.eecs.qmul.ac.uk/s.e.dixon/pub/2014/MauchDixon-PYIN-ICASSP2014.pdf
- Apple music-effect AU type: https://developer.apple.com/library/archive/qa/qa1737/_index.html
- Apple AU latency property: https://developer.apple.com/library/archive/documentation/MusicAudio/Conceptual/AudioUnitProgrammingGuide/TheAudioUnit/TheAudioUnit.html
- Logic latency/PDC/Low Latency Mode: https://support.apple.com/guide/logicpro/work-with-plug-in-latencies-lgcpe11997ba/mac
- Logic monitoring latency: https://support.apple.com/en-us/105040
- Concrete Logic MIDI/sidechain route: https://www.waves.com/support/how-to-control-waves-plugins-with-midi-in-logic-pro
- Optional owned reference manual: https://www.waves.com/1lib/pdf/plugins/waves-harmony.pdf
- Optional owned reference algorithm behavior: https://helpcenter.celemony.com/M5/doc/melodyneStudio5/en/M5tour_NA_Mode_2?env=standAlone
- Listening-method limits: https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1534-3-201510-I!!PDF-E.pdf
- Excluded commercial context: https://www.zynaptiq.com/ztx/ztx-versions/
- Excluded INTONE API context: https://licensing.zplane.de/uploads/SDK/INTONE/V1/manual/INTONE_v1_sdk_documentation.pdf
