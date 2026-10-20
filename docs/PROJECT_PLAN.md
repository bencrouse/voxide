# voxide — zero-spend project plan

Status: PR 00 implemented and locally revalidated after independent review on
`pr-00-bootstrap`. Subsequent PRs remain planned. No harmonizer
quality/live-monitoring qualification yet.
Created 2026-10-20.

## 1. Brief and hard boundaries

Build a basic, professional-quality vocal harmonizer for Logic Pro: **one original
lead plus exactly three available generated harmony voices**, key/scale control
and MIDI control, usable for both live monitoring and mixing.

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
- A mixing-only result is not a successful completion of the requested product.
  Do not silently narrow the range, increase latency, reduce harmony count, or
  relax quality to manufacture a pass. Escalate a demonstrated conflict to the user.

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

All numerical targets below are provisional until PR 02 approval. They are
requirements to test, not capabilities already demonstrated.

### Listening standard

- Correct intended notes with no octave jumps, semitone chatter, unintended voice
  reassignment, or lingering wrong notes.
- Recognizable singer/vowel identity; no conspicuous chipmunk, hollow, metallic,
  buzzy, phasey, or watery coloration.
- Consistent expression policy for vibrato, scoops, dynamics, and endings.
- Intelligible consonants/breaths without chirps, smeared attacks, missing syllables,
  or exaggerated stacked sibilance.
- Three simultaneous harmonies remain clear during changing notes, without clicks,
  bursts, warbling, or timing flams. Test mono as well as stereo presentation.
- Original lead is unshifted and otherwise unprocessed except explicit gain and
  documented alignment delay. Verify it separately by a delayed unity null test.
- Exposed harmonies and a fixed representative mix are usable without repair or
  masking processing failures with other effects.

The target is harmonies retaining the lead's character, not a promise of three
independently performed singers. Ask whether the user expects that stronger illusion.

### Proposed support envelope

| Item | Proposed requirement |
| --- | --- |
| Source | Dry, mono, one singer; no pre-existing harmonies |
| Input F0 | E2–C6, approximately 82–1,047 Hz |
| Shift per voice | −12 to +12 semitones, including dynamic changes |
| Mathematical output extremes | Approximately 41–2,093 Hz; these extremes also require qualification |
| Project rates | 44.1 and 48 kHz |
| Required articulation | Normal voiced singing, breathiness, vibrato, register transitions, consonants |
| Stress material | Fry, growls, whispers, clipping, accompaniment bleed: safe/graceful behavior, with reliable pitch guarantees explicitly decided |

Report common shifts within ±7 separately from octave shifts. Passing the smaller
range does not qualify the full range. Note names use C4 = MIDI 60 regardless of
Logic's configurable octave display.

### Separate timing budgets

| Quantity | Definition | Proposed gate |
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
- [ ] Confirm ranges, maximum shifts, source conditions, and whether 96 kHz is
  essential (not assumed supported by this plan).
- [ ] Approve latency ceilings and whether lead monitoring must be entirely in
  software or normally uses the interface's direct path. Direct lead monitoring
  does not make delayed harmonies low-latency.
- [ ] Approve musical mapping, exact initial scale list, expression policy, and
  expected behavior on non-scale notes and unsupported/ambiguous source material.
- [x] User confirmed local-only use for now under JUCE's AGPLv3 option. Revisit
  source/notice obligations before sharing; no paid license fallback is assumed.
- [ ] Confirm no-cost recordings and independent listeners available. Missing
  resources remain blocked gates, not permission to invent results.

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

Use free Python/NumPy/SciPy, Praat, Instruments, AU tools, and independently checked
output-pitch analysis. Do not certify output with Voxide's own tracker alone.

### Proposed final pass gates (freeze in PR 02)

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

### PR 01 — Prove Logic audio/MIDI routing before DSP investment

Depends on: PR 00 and user Logic session.

**Scope / TODO**
- [ ] Add diagnostic pass-through and bounded timestamped MIDI/audio logging outside
  the audio callback (fixed-capacity telemetry, no console/file writes in render).
- [ ] Prepare a disposable Logic project: AU MIDI-controlled effect on an instrument
  track, recorded vocal via sidechain, MIDI region and live controller input.
- [ ] Document recorded-source and physical-input routes, exactly one audible lead,
  input monitoring, record-enable, source output suppression, and direct-monitor split.
- [ ] Record the actual hardware/software environment without serials or hostname.

**Validation required to merge**
- [ ] Native Logic discovers the correct new build; recorded sidechain and MIDI
  note events reach the same instance, including within-block event offsets.
- [ ] User-coordinated physical input test works while stopped and during recording;
  focus/record-enable/mute/solo behavior is documented, not assumed from `auval`.
- [ ] No doubled lead, feedback route, stale telemetry, or stuck diagnostic notes.
- [ ] Low Latency Mode on/off test confirms which routes/sends remain active.
- [ ] Save/quit/reopen the diagnostic project and verify routing/MIDI again.

**Agent handoff — update before merge**
- Major decisions: pending — chosen Logic route and direct/software monitoring policy.
- Learnings/evidence: pending — screenshots/project hash, actual version and observations.
- Reflections/next-agent cautions: Logic may bypass effects or disable sends in Low
  Latency Mode; audible pass-through is not proof the intended processing remains active.

### PR 02 — Freeze requirements, corpus, fixtures, and measurement protocol

Depends on: PR 01 and available recordings/listeners.

**Scope / TODO**
- [ ] Close the user decisions above and freeze acceptance thresholds before tuning.
- [ ] Gather/annotate the no-cost corpus and seal the holdout split; retain rights.
- [ ] Generate known-F0/formant/noise fixtures from versioned scripts/seeds.
- [ ] Define JSON manifests for sources, sample-indexed targets/MIDI, configurations,
  metrics, raw reports, listener IDs, and environment/build identities.
- [ ] Implement basic WAV/control rendering and independent metric/annotation tools;
  specify uncertainty rules, stable-frame regions, voiced-boundary exclusions,
  recognition settling criterion, and onset timestamp definitions.
- [ ] Set exact loudness, mix levels, comparison tolerance, listener-session design,
  and defect severity definitions. No per-engine masking EQ.

**Validation required to merge**
- [ ] Re-running fixture generation with the same seed produces identical hashes;
  ordinary checks never regenerate expected results.
- [ ] Two annotators review agreement and uncertain regions; scripted validators
  reject missing files, bad hashes, invalid note ranges, or inconsistent timestamps.
- [ ] Known synthetic pitch/delay/formant errors are recovered by measurement tools;
  deliberate off-by-one and wrong-octave controls are detected.
- [ ] Development/holdout separation and the full budget/criteria have explicit
  approval; unavailable singers/listeners are recorded as blockers, not waived silently.

**Agent handoff — update before merge**
- Major decisions: pending — approved contract and musical semantics.
- Learnings/evidence: pending — corpus manifest, annotation disputes, tool calibration.
- Reflections/next-agent cautions: annotations are estimates; synthetic truth and
  human judgment serve different purposes. Never tune against a repeatedly opened holdout.

### PR 03 — Causal F0/voicing tracking and deterministic harmony selection

Depends on: PR 02.

**Scope / TODO**
- [ ] Implement a bounded causal YIN-family baseline and one multi-candidate causal
  variant; document window/hop, history, smoothing, and any lookahead separately.
- [ ] Produce timestamped F0/confidence/voicing, with defined low-confidence behavior.
- [ ] Implement scale-degree offsets and absolute MIDI targets for three slots;
  deterministic allocation, duplicate notes, note-off, overflow, and >3-held-note policy.
- [ ] Define vibrato/scoop handling, scale-boundary hysteresis, and silence/seek/reset
  behavior without processing the original lead.

**Validation required to merge**
- [ ] Exact expected-note tests cover approved scales/roots, accidentals, ties,
  limits, rapid changes, duplicate/overlapping MIDI, event ordering, and releases.
- [ ] Cold and continuous recognition response, F0 accuracy, octave errors, voicing
  errors, and false triggers measured per register on development material.
- [ ] Vibrato around note boundaries does not chatter; fast deliberate changes are
  not hidden by excessive smoothing. Missing-fundamental cases are included.
- [ ] Block partitions 32/64/128/257/512/1024 and varying sequences preserve event
  semantics; reset/seek does not use future samples or stale history.
- [ ] Allocation-audit self-test detects deliberate render allocations, then reports
  none in exercised tracker/selector callbacks; sanitizer tests pass.
- [ ] Report any target misses honestly. A reproducible research result may merge,
  but unresolved required tracking failures block the architecture go-decision.

**Agent handoff — update before merge**
- Major decisions: pending — tracker variant, confidence/hysteresis/voice-allocation policy.
- Learnings/evidence: pending — failure excerpts and per-register timing distributions.
- Reflections/next-agent cautions: MIDI does not eliminate source-pitch tracking;
  offline Viterbi accuracy is not live causal performance.

### PR 04 — Isolated engine comparison with oracle controls

Depends on: PR 02; may proceed independently of PR 03 once fixtures are ready.

**Scope / TODO**
- [ ] Build separate Signalsmith and Rubber Band evaluators using the same source,
  sample-indexed reference F0/targets, output format, and measurement schema.
- [ ] Signalsmith: evaluate 512/128, 1024/256, 2048/512 window/hop at 48 kHz;
  document corresponding 44.1 kHz choices. Enable formant compensation explicitly.
- [ ] Rubber Band: short/medium window, formant preservation, fixed-block adapter;
  query start delay with initial ratio set. Keep its dependency out of the product.
- [ ] Render static 0/±3/±7/±12 semitones and changing ratios, one and three instances,
  time ratio 1. Use synthetic truth and manually checked real-vocal reference F0.
- [ ] Measure queried and actual delay, ratio-change settling, formants, artifacts,
  peak callback cost, state reset, and output duration/tail behavior.

**Validation required to merge**
- [ ] Unity/control delay and synthetic output pitch/formants match independently
  calculated expectations or are explicitly recorded as candidate failures.
- [ ] Repeat renders identify determinism; varying block lengths and FIFO wrap
  do not drop/repeat samples or produce unexplained timing differences.
- [ ] Impulse tests are used at unity; non-unity timing uses suitable envelopes/
  known transitions rather than invalid raw-waveform correlation assumptions.
- [ ] Optimized Release measurements retain raw timings and failed cases; source
  inspection/allocation tests identify callback hazards. Do not time sanitizer builds.
- [ ] Report evidence by configuration. Discarding an engine requires a reproducible
  failure or documented incompatible delay, not a name/marketing preference.

**Agent handoff — update before merge**
- Major decisions: pending — viable configuration shortlist and isolated-engine limitations.
- Learnings/evidence: pending — pinned revisions, raw oracle renders and measurements.
- Reflections/next-agent cautions: defaults are not low-latency proof; Rubber Band
  is a quality comparator, not a presumed live solution; oracle tests bypass real tracking.

### PR 05 — Complete three-voice interaction and consonant treatment

Depends on: PRs 03–04.

**Scope / TODO**
- [ ] Integrate shared tracking/selection with three independent shifting states,
  explicit source-time alignment, bounded ratio transitions, and controlled summing.
- [ ] Compare engine-native versus one common confidence/voicing-aware consonant
  treatment; crossfade mixed boundaries and control reinforced consonants.
- [ ] Log source timestamp, F0/confidence, target, applied ratio/time, voicing state,
  and output alignment into bounded non-render-consumed telemetry.
- [ ] Run oracle F0 + prescribed targets; live F0 + prescribed targets; and complete
  scale/MIDI modes. Render upper/lower/mixed three-voice voicings and exposed stems.
- [ ] Define lead alignment and accurate latency reporting. If distinct live/mix
  configurations are necessary, make the switch explicit/stopped, persist it,
  and qualify both; do not switch quality secretly during offline bounce.

**Validation required to merge**
- [ ] Note-transition tests expose stale-F0/control alignment; all three voices
  change consistently without unwanted assignments, clicks, bursts, or flams.
- [ ] Breathy vowels, z/s/sh, plosives, silence, phrase tails, and noise/bleed stress
  cases are checked in stems and the sum; no consonant copying/gating workaround
  is accepted without evaluating the complete blend.
- [ ] Lead unity/null test passes with documented delay; summed output is finite
  and respects fixed gain/headroom without adding a masking limiter.
- [ ] Three-voice delay/response/CPU and correctness tables are produced for all
  retained configurations; direct-lead and software-aligned routes are distinguished.
- [ ] ASan/TSan and self-verifying allocation checks pass for processing, reset,
  automation, and state handoff; framework caveats are documented separately.

**Agent handoff — update before merge**
- Major decisions: pending — timestamp contract, consonant policy, lead alignment.
- Learnings/evidence: pending — ablations localizing tracker/selector/shifter failures.
- Reflections/next-agent cautions: acceptable individual voices may fail as a sum;
  bypassing consonants and delaying a lead are audible architecture decisions.

### PR 06 — Blind comparison and architecture go/no-go

Depends on: PR 05 and independent volunteers.

**Scope / TODO**
- [ ] Freeze configurations, open holdout once, render coded listening sets, and
  run the predeclared independent-listener protocol.
- [ ] Include known synthetic desired outputs and degraded anchors; optionally
  include already-owned Waves/ Melodyne references with matching targets/settings.
  If absent, disclose it; no purchase or trial dependence.
- [ ] Combine ratings, duplicate consistency, timestamped defects, objective
  metrics, latency/CPU, and license findings. Report per-singer and worst-case results.
- [ ] Allow **one bounded development-data tuning/retest cycle**, with fresh or
  separately reserved holdout material. Preserve original failures and results.
- [ ] Select a free engine/configuration only if evidence supports all approved
  gates, or publish an explicit no-go/requirement-conflict report for user decision.

**Validation required to merge**
- [ ] Randomization/identity-key separation, loudness/alignment, duplicates, and
  listener independence are documented; score aggregation is independently checked.
- [ ] Decisions include uncertainty/confidence intervals and do not hide failed
  octave shifts, registers, cases, or individual listener disagreements in averages.
- [ ] User approves go/no-go. A negative report can merge, but **PRs 07–10 do not
  proceed without a go-decision**. No commercial fallback or unbounded custom DSP.

**Agent handoff — update before merge**
- Major decisions: pending — chosen engine/configuration or explicit blocker.
- Learnings/evidence: pending — anonymized scores, raw defect log, selection rationale.
- Reflections/next-agent cautions: preferences are not pass criteria; a good demo
  or reference product's failure cannot override the agreed requirements.

### PR 07 — Product processor, minimal controls, automation, and state

Depends on: PR 06 go-decision.

**Scope / TODO**
- [ ] Integrate the selected architecture into the AU shell and shared test target;
  remove evaluation alternatives from normal product linkage, not from evidence.
- [ ] Add only necessary controls: scale/MIDI mode, key/approved scales, three
  harmony degree settings for scale mode, voice levels/enables, original level,
  and the explicit processing configuration only if evidence requires it.
- [ ] Use clear readable native controls, keyboard access, meaningful labels/units,
  and modest input/pitch status. No preset ecosystem or ornamental feature expansion.
- [ ] Freeze parameter IDs, ranges, defaults, state schema, and component identity;
  persist musical/voice/processing settings but not transient held MIDI notes.
- [ ] Implement validated state restore, correct host notification and bypass/reset/
  silence behavior, keeping UI/document locks and file work off rendering.

**Validation required to merge**
- [ ] UI and headless/processor renders use the same production DSP and agree.
- [ ] Parameter automation/readback and save/restore reproduce settings/audio;
  malformed/truncated/out-of-range state is handled safely.
- [ ] Editor create/destroy, state restore, and automation concurrent with rendering
  pass focused lifetime/concurrency checks; no stuck notes or stale UI overwrite.
- [ ] UI controls are operable/readable at supported sizes; keyboard focus does
  not steal intended host MIDI, and no extra product controls were introduced.
- [ ] Regression audio and approved three-voice behavior remain within frozen limits.

**Agent handoff — update before merge**
- Major decisions: pending — frozen host/state contract and necessary controls.
- Learnings/evidence: pending — interaction checks, serialization fixtures, caveats.
- Reflections/next-agent cautions: once host IDs/state ship, preserve their meaning;
  UI polish must not alter processing or conceal the selected configuration's limits.

### PR 08 — Installed AU/Logic compensation, recall, and offline bounce

Depends on: PR 07 and user Logic session.

**Scope / TODO**
- [ ] Add installed-AU integration tests and disposable Logic acceptance projects
  using recorded audio sidechain and sample-positioned MIDI.
- [ ] Verify latency property/notifications, host compensation, bus layouts,
  sidechain/MIDI sync, bypass, and stopped/configuration changes.
- [ ] Exercise live keyboard plus recorded MIDI, duplicate/overlapping notes,
  >3-note allocation, all-notes-off, cycle, seek, stop/resume, and mid-held-note start.
- [ ] Document host chase limitations and expected behavior; never promise state
  reconstruction for MIDI events the host does not send.
- [ ] Compare real-time and offline bounce, start-at-first-syllable, phrase tails,
  and differing host render-block sizes. Physical live input must be recorded first.

**Validation required to merge**
- [ ] Installed build identity/`auval`/actual Logic route verified; no doubled lead.
- [ ] Unity-delay compensation reference aligns within the frozen tolerance;
  transformed-audio onset and pitch timing agree with the documented measurement.
- [ ] Low Latency Mode on/off confirms the intended harmonizer/feed are active;
  document that Low Latency Mode is inactive during bounce.
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

### PR 09 — Actual-hardware monitoring, performance, and final listening

Depends on: PR 08 and user/singer sessions.

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

Depends on: successful PR 09 qualification, or explicitly limited no-go documentation.

**Scope / TODO**
- [ ] Produce a concise setup/use guide and full evidence index: selected architecture,
  supported ranges/settings, Logic routing, monitoring/compensation, MIDI semantics,
  recall/bounce procedure, known failures, and reproducible commands.
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
3. **Architecture gate (PRs 03–06):** bounded comparison, one tuning cycle, and
   independent assessment. No engine purchase.
4. **Product/host gate (PRs 07–08):** proceed only after architecture go-decision.
5. **Hardware/acceptance gate (PRs 09–10):** all required manual and measured
   observations must exist before declaring success.

PRs 03 and 04 can be separate independent work streams after PR 02, but this plan
does not authorize subagent spawning. No other feature branches are implied.

If no no-cost engine meets the approved quality/latency/range simultaneously,
deliver reproducible failures and options to the user: stop, explicitly revise a
requirement, or separately scope new research. **Do not reinterpret the zero-spend
constraint as permission to compromise the fixed brief without approval.**

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
