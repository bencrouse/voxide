# PR 05 — three-voice interaction and consonant research

This integrates the **reviewed PR03 tracker/selector** with **three independent
PR04 shifting instances**, without selecting an engine or linking one into the
product AU/Standalone. `InteractionEvaluation/` is a separate native project;
`EngineEvaluation/`, production `Source/`, the root product CMake target and frozen
PR02 fixtures/contracts remain unchanged. Engine/tracker failures from earlier
PRs are not presumed fixed. No new dependencies, purchase, install, device, Logic
operation, audio playback, holdout access or lead tuning is involved.

## Processing and clock contract

`InteractionProcessor` accepts one finite mono sample and returns exactly one
sample of each of three native/pre-policy voices, three treated voices, unity
direct/aligned lead and the two complete blends. There are always three separate
engine states. Musical controls come from four explicit research modes:

1. Analytic/reviewed oracle F0 + prescribed absolute targets.
2. Shared causal tracker F0 + the **same** prescribed targets.
3. Shared causal tracker + the PR03 scale selector.
4. Shared causal tracker + sample-positioned sustained MIDI targets/PR03 allocation.

An oracle is not an automatically generated vocal annotation. For live tracking,
the midpoint of the supplied support interval is an **engineering source anchor**,
not a proven instantaneous F0. The frame is unavailable until its actual support
end. Input is held for half the support plus one tracker hop, allowing that
decision to reach the delayed processing stream without using unreceived audio.
This reserve is explicit, not subtracted from latency. Moving-signal temporal
bias and the existing tracker acquisition/recognition misses remain limitations.

Pitch and music queues have separate source chronology. Incoming messages record
requested source time and actual render availability. Native API calls apply
controls on `input-source-begin - engine.controlLag` for all three voices together.
All times are epoch-local; reset replaces the epoch. Early/future frames, malformed
events, overflowing inboxes and unordered source messages fail closed and are
counted. Late decisions remain late. MIDI supplies targets, never source F0.

Requested shifts outside ±24 semitones are rejected/reported, not silently clamped
into a correct target. Within-range log-pitch changes are rate-limited to 2400
semitones/second at each native quantum. This is a bounded stair-step controller,
**not** proof that audible transitions are clickless. Activation and shared-policy
weights crossfade linearly at sample rate over 10 ms. Exactly the same controls,
fixed gains and comparison sources are used across engines/policies.

### Fixed delivery, lead alignment and failure accounting

Two named stopped presets are tested: **live = 15 ms** and **mix = 100 ms** total
harmony delivery reserves. These are the approved ceilings used as experiments,
not demonstrated capabilities. They include analysis, native delay and adaptation.
The initial native ratio is 1; Rubber Band's recommended zero start pad and fixed
queried startup trim are applied once. Signalsmith's nominal raw offset is retained
in source/output indexing. No future pre-roll or dynamic re-trimming is used.

Retrieved native samples have absolute source/output indices in fixed-capacity
FIFOs. At a missed fixed deadline the processor emits safe zero and increments
underflow. Later arrival of that expired sample is counted/discarded; it cannot
shift later audio into a false alignment pass. Missing policy metadata, FIFO
overflow and unrendered nonzero finish tails are separate failed gates. Finite
zero-tail input and native finalization are retained, not cut to a pretty length.

The lead stem is bit-preserving at unity (for finite source PCM), either immediate
or delayed by exactly the declared reserve. Both routes are rendered separately:
- Aligned lead + harmonies share one declared delay and can have one PDC value in
  a future host processor, **only if delivery/quality gates also pass**.
- Direct lead is immediate while harmonies retain their reserve. This is not a
  single-delay compensated route; do not claim delaying the dry lead elsewhere
  makes the harmonies physically faster.

The research processor exposes `latencySamples()`; it is not an installed AU
latency notification or proof of host compensation. The product still reports
its existing dry-path latency. Configuration changes are rejected while running.
Stopped presets/settings and event files are persisted per render. There is no
hidden bounce mode or quality switch. All render, producer and telemetry owners
must be externally stopped/joined before lifecycle replacement. A stopped reset
**reconstructs** the graph instead of relying on PR04's failed dynamic native reset;
its allocation/cost is not concealed in a render callback.

## Consonant comparison and fixed headroom

Policy A uses the engine's native consonant handling. Policy B uses a single
common voicing/confidence policy: smooth confidence-weighted shifted audio toward
`source / 3` per active harmony during unvoiced material. The fixed mixer is
`lead + (voice1 + voice2 + voice3) / 3`. Therefore three unvoiced dry contributions
add **one third of the source** in the complete wet sum, not three full consonant
copies. At full confidence all shifted audio remains; breathy/voiced consonants
are not categorically removed by a binary input gate. Inactive MIDI slots fade.

This is a proposed, tested ablation—not an accepted consonant workaround. It can
still reinforce the lead, color mixed sounds or damage articulation. Raw/treated
stems and **both complete blends** retain region RMS, peak and adjacent-step
proxies. These are not listening ratings or confirmed click/intelligibility tests.
Independent unvoiced output-F0 proxies are retained for pure s/sh/plosive/silence
regions when a complete analysis window fits; shorter regions remain explicitly
unobservable to that instrument, not automatically artifact-free.
There is no limiter, clipping, gain fitting, normalization, masking EQ or secret
voice reduction. Float WAVs preserve overs; unsafe peak cases fail headroom.

## Telemetry, concurrency and qualification

Audio-thread telemetry goes only into a bounded SPSC queue; an independent
consumer drains it outside callback timing/allocation scopes. Overflow is counted,
not allowed to block rendering. Controls and output packets include epoch, support
interval/availability, requested target/time, source/processing time, F0/confidence,
voicing, actual ratio, activation, native output index and callback availability.
Independent input/control hashes distinguish transport bugs from native instance
variation. A separate bounded SPSC inbox transfers automation/MIDI/oracles.
Render owns tracker, selector and all engine state. No UI/shared-object mutation,
file writes, formatting, locks or heap growth is part of the intended render path.

Contracts cover exact transport/lead delay, independent voices and controlled
sum, bounded ramps, common unvoiced budget, insufficient-reserve failures,
late-oracle accounting, stopped configuration/reset, and actual concurrent
automation/telemetry handoff. Native smoke checks cover all four modes and both
rates/policies, including stopped reconstruction. Debug/Release audit controls
must detect deliberate C/C++ allocations; interposition is disabled under
ASan/TSan as in earlier PRs. Native allocation/performance/quality failures remain
separate from passing transport or sanitizer contracts.

The full declared matrix has **520 primary cases**: all five pinned configurations,
44.1/48 kHz, both reserves, both policies, all four modes and upper/lower/mixed
voicings, plus unity impulses. The versioned analytic suite covers E2/C6, pitch
steps, breathiness, z/s/sh, plosives, intentional bends, phrase endings, silence
and bleed. These are speech-like synthetic challenges, not recorded singers or
evidence of human consonant intelligibility. Scale voicings use independent degree
expectations; prescribed/MIDI voicings span common shifts and ±24-semitone extremes.
Mixed-partition fresh-process repeats retain native failures for every configuration,
rate, reserve and policy in oracle mixed mode, plus an initial control case.

Independent offline pitch uses the **8192-sample full-range calibrated PR04 meter**
on a sparse 50 ms output observation grid; source references remain at 10 ms.
It is never narrowed around the expected answer. Source-supported missing output
remains a failed estimate. Centered windows can cross transitions; those values
are descriptive, not instantaneous vocal truth. First correct observed output
includes completed sampled dwell, the entire centered-window support, fixed
delivery and callback return. Unresolved observations remain in reports; this
conservative observer cannot certify a tight intrinsic engine response target.
MIDI request-to-API response is measured separately, with coalesced events explicit.
Lead null, complete-sum headroom, finite output, delivery failures, raw callback
occupancy/allocations and full negative case IDs are retained by configuration.

Research requires optimized unsanitized audited Release, compiled source identity,
verified canonical dependency trees, immutable invocation/input hashes, all-source
and exact binary/runtime/build snapshots, and before/after verification. Private
development uses only explicitly selected permission/hash-bound corpus sources
and two completed registered agreeing human references. Missing references stay
pending, including required rhythmic/bending c; no holdout mode exists. All private
identity/reference/audio/derived evidence stays under ignored `evaluation/pr-05/`.

## Commands and current status

```sh
make interaction-check
python3 scripts/check.py --full --offline --engines --interactions
python3 scripts/interaction_evaluation.py private --development-corpus evaluation/your-corpus/corpus.json
```

`--quick` is explicitly incomplete. All builds use the existing verified dependency
cache offline. Source and binaries must remain unchanged while qualification runs;
update evidence documentation afterward. An early exploratory smoke was terminated
by the caller timeout at `build/interaction-research/20261023T142711Z-6ff45cc6/` and
has no completed report; it is not qualification. A later 24-case smoke at
`build/interaction-research/20261023T143509Z-a6699fd8/report.json` completed, but its
4096-sample pitch observer could not cover the 20.6 Hz extreme. Its pitch scores
are superseded; the current meter uses the calibrated 8192-sample support. No
candidate audio was changed or expected range reduced to hide that instrument issue.

Final qualification is recorded below. Human listening, actual-vocal corpus
references, Logic/PDC/monitoring and architecture acceptance remain open. No
engine, consonant policy or product integration is selected by this PR.

### Superseded validation and retrieval correction

The full baseline at `build/checks/20261023T144717Z-482614ff/environment.json`
passed all engineering suites and the original 520-case interaction matrix. A
self-review correction then made the sparse response observer restart across
missing/unvoiced/uncertain grid points, strengthened dynamic harmony-automation
coverage and recorded stopped reconstruction allocations. That source state passed
at `build/checks/20261023T152733Z-a6e3944a/environment.json` with its full research
at `build/interaction-research/20261023T153046Z-b9248371/report.json`.

Final raw-log inspection exposed a further **caller defect**, not an intrinsic
Rubber Band failure: retrieval requested a full 1024-sample scratch block even
when `available()` reported fewer. The pin returns the actual count but writes
`RingBuffer::read` warnings to stderr. The latter run retained 362,284 such warning
lines across its 208 Rubber Band cases. PR05 now requests at most the native
availability; a strict transport control rejects over-requests. Those prior callback
timings/allocation observations include avoidable wrapper-induced diagnostic I/O
and are superseded by the final corrected run, not evidence to discard the engine.
PR04 used the same over-request pattern; its immutable historical evidence remains
retained with this caveat. No dependency source/pin was altered or warning hidden.

## Final engineering qualification — 2026-10-23

The corrected source state passed `python3 scripts/check.py --full --offline
--interactions`. **112 Python tests** (nine PR05 regressions), production native
regressions and **seven isolated native tests per profile** passed, including
Debug, Release, ASan and TSan. Release native tests also passed concurrently with
`ctest --parallel 4`. The tests exercise real voiced live modes, dynamic harmony
automation, MIDI/telemetry concurrency, malformed/future controls, strict native
retrieval bounds and stopped state reconstruction. Stopped reconstruction's
intentional allocations were audited separately; sanitizer audit counts/timings
were not used as realtime evidence.

Evidence:
- Final full source-stable product/interaction qualification:
  `build/checks/20261023T160144Z-90bc0fa8/environment.json`.
- Four-profile interaction qualification:
  `build/interaction-checks/20261023T160242Z-0053b0ee/report.json`.
- Final corrected **520/520 primary renders**, zero native render errors,
  **60/60** full-range instrument calibrations:
  `build/interaction-research/20261023T160456Z-ffcc2998/report.json`.
  Its `provenance.json`, complete source snapshot, exact binaries/runtime/build
  metadata, raw stems, events, settings and callback/control CSVs are retained.
- Unchanged PR04 requalification (930 cases), with the retrieval/logging caveat:
  `build/engine-checks/20261023T144826Z-8a905805/report.json` and
  `build/engine-research/20261023T144947Z-1a248259/report.json`.
- PR02 regression/calibration:
  `build/evaluation-checks/20261023T163326Z-66004dd1/report.json` passed.
- Explicit private development preflight:
  `evaluation/pr-05/20261023T163326Z-a32800d3/private-report.json` and
  `provenance.json`: three sources, **zero reference-ready sources**. No real-vocal
  renders/grades were fabricated. Required expressive c remains pending, not excluded.

### Three-voice delivery/allocation table

Each row contains 52 cases across both rates, both policies, four modes and three
voicings plus unity controls. A delivery pass means no missing metadata,
underflow/late samples or FIFO overflow on that fixed timeline—not accepted audio
quality or hardware latency. All failed case IDs are retained by configuration.

| Engine / samples | Fixed reserve | Delivery pass / 52 | Zero callback allocations / 52 | Worst per-case p99.9 occupancy |
| --- | ---: | ---: | ---: | ---: |
| Signalsmith 512/128 | 15 ms | 16 | 52 | 5.26% |
| Signalsmith 512/128 | 100 ms | 52 | 52 | 5.43% |
| Signalsmith 1024/256 | 15 ms | 0 | 52 | 6.80% |
| Signalsmith 1024/256 | 100 ms | 52 | 52 | 7.42% |
| Signalsmith 2048/512 | 15 ms | 0 | 52 | 10.57% |
| Signalsmith 2048/512 | 100 ms | 52 | 52 | 10.50% |
| Rubber Band R3 short | 15 ms | 0 | 0 | 40.65% |
| Rubber Band R3 short | 100 ms | 52 | 0 | 41.47% |
| Rubber Band R3 standard | 15 ms | 0 | 0 | 46.65% |
| Rubber Band R3 standard | 100 ms | 16 | 0 | 45.96% |

Overall, **240 delivery passes / 280 failures**; **312 zero-allocation cases /
208 allocating cases**. The corrected 520 primary runs had **zero nonempty native
stderr logs**, so the earlier wrapper-induced retrieval warnings are resolved.
Rubber Band processing allocations persist independently of that logging correction;
do not silently treat them as solved or attribute them to an unproven call stack.
All 520 lead-null, headroom, control-chronology and finite/tail checks passed.
All captured stem/blend peaks were below unity (largest approximately 0.946).
There were zero observed overdue virtual callbacks; this is not a Logic soak or
physical monitoring qualification.

### Negative interaction and quality results

- **No complete tracked live configuration qualifies.** The explicit half-support
  plus-hop analysis reserve already exceeds the 15 ms delivery budget, before
  native processing. Only the smallest Signalsmith oracle cases meet that fixed
  deadline; an oracle does not qualify the live tracker path. No delay, support
  range or voice count was changed to conceal the conflict.
- All **120 complete MIDI cases fail** the 5 ms request-to-native-API screen.
  Applied event observations span approximately **24.44–67.44 ms**, including the
  disclosed source-alignment/analysis/quantum scheduling. A small callback or
  timely receipt of a MIDI message is not a timely native control application.
- All **480 non-impulse cases** have at least one voice below the 99% sparse
  stable-frame pitch target. Oracle failures remain, so tracking alone cannot
  explain the result. Transition-spanning 8192-sample observation windows and
  synthetic/non-vocal material limit attribution; this is not a per-singer
  accuracy estimate or proof every audible frame is wrong.
- Of 30,000 correlated event/voice response observations, **28,680 remain
  unresolved** by the sparse, windowed, completed-dwell observer. Dense bend
  controls, missing/uncertain/unvoiced grid points and unavailable output are not
  discarded or counted as immediate response. The conservative observer is not
  a precise intrinsic-engine timing instrument. Raw clocks remain available.
- Of 41 native mixed-partition fresh-process comparisons, **six failed** the
  frozen waveform tolerance, all on Signalsmith 512/128; maximum difference reached
  approximately 0.1845. Input/control hashes matched. These failures remain native
  repeatability limitations, not transport passes erased by clean sanitizers.
- The shared consonant budget is **not selected**. For example, the 48 kHz,
  100 ms, smallest-Signalsmith oracle mixed trial had s/sh complete-blend RMS ratios
  to source of about **1.049/1.102** with native treatment versus **1.325/1.333**
  with the shared policy. Its analytic dry budget avoids three full dry copies,
  but can reinforce these consonants more than native treatment. No energy proxy
  establishes intelligibility or human preference; mixed/breathy segments, stems
  and complete sums remain retained rather than normalizing away this outcome.

**Outcome:** PR05 engineering implementation and automated qualification are
complete as a **negative research milestone**, not an accepted three-voice product
architecture. Human articulation/listening, real-vocal references, Logic/PDC and
physical monitoring remain pending; tracker/engine quality/timing failures remain
failed gates. No independent PR05 code review has been performed. No engine or
treatment is selected and PR07's architecture go-gate is not unlocked. Source,
fixtures, pins and contracts from PRs 02–04 remain unchanged. Only evidence
documentation is updated after final qualification. User subsequently approved a
branch-only commit on 2026-10-23 to preserve this negative research milestone before
a bounded architecture investigation. No merge to main, push, AU installation or
device/Logic operation is authorized.
