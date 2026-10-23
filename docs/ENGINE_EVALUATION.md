# PR 04 — isolated engine comparison with oracle controls

The product AU/Standalone remain the reviewed PR 03 dry lead and target selector.
This PR creates separate native executables under `EngineEvaluation/`; neither
Signalsmith nor Rubber Band is a transitive product dependency. No device, Logic,
AU install, commercial package, paid service or public distribution is required.
No engine or architecture is selected by these experiments.

## Pinned engines and configurations

See `THIRD_PARTY_NOTICES.md` and `cmake/engine-dependencies.json` for full revisions,
archive hashes, notices and local-use/distribution boundaries.

- Signalsmith Stretch 1.4.0 tag plus its pinned Linear 0.6.4 dependency, Apple
  Accelerate FFT. Test **512/128**, **1024/256**, **2048/512** window/hop samples.
  These same sample counts are intentional at 44.1 kHz: window durations are
  11.61/23.22/46.44 ms there, versus 10.67/21.33/42.67 ms at 48 kHz.
  `setFormantFactor(1, true)` explicitly compensates pitch; fixed random seed
  `0x564f5849`, split computation off. The upstream header's version array is 1.3.2
  despite the 1.4.0 tag; exact source identity, not a version-string assumption,
  establishes the tested code.
- Rubber Band 4.0.0 **R3 Finer**, RealTime, ThreadingNever/NO_THREADING,
  FormantPreserved, PitchHighConsistency, fixed input quantum **128** and
  `setMaxProcessSize(128)`. Test short and standard windows; standard is the plan's
  medium/quality comparator, not an invented literal FFT size. R3 uses its native
  multi-resolution processing. The native CLI selectors are 1=short and 2=standard.
  vDSP FFT and built-in BQ resampling are compiled from its supported single-file
  build. R2 and other FFT/resampler combinations are **not** thereby rejected.

Each harmony is a separate mono engine instance, not a stereo/multichannel trick.
All cases keep time ratio 1.0 and shifts within inclusive ±24 semitones. There is
no dry/harmony sum, consonant workaround, limiter, per-stem gain fitting or tuning
of the input. Complete interaction/consonant policy is PR 05 work.

## Oracle inputs and source-time contract

`docs/evidence/pr-04/protocol.json` records this engineering research protocol;
it is not an extra user-approved listening/perceptual protocol. All original PR 02
numerical requirements and remaining approval states are unchanged.

Sources and immutable controls are shared by both evaluators. Each control has
source sample, three ratios and source F0. Known analytic F0 (or a reviewed human
grid) supplies Signalsmith's rough formant prior. Unvoiced/uncertain input uses an
explicit fixed 200 Hz engineering prior, **not** automatically estimated truth.
Rubber Band has no external F0-prior API; it receives the same ratios and uses its
native formant analysis. The difference is disclosed, not hidden as identical DSP.

Source F0/targets are oracles for this comparison, not output from the production
tracker or the failed private whistle guides. Frozen moving-pitch sources use their
sample-indexed annotation grid, held between grid points. Signalsmith applies
controls when its processing-source clock reaches the event (`input - inputLatency`);
Rubber Band uses the incoming-source clock. Both quantize to the next fixed input
quantum and log requested time, API application, processing time, ratio/F0, and queried
current start pad/delay. Initial ratios are installed **before** initial delay queries.
Initial preset state is distinguished from a live MIDI event; no <5 ms external
MIDI or audible response is inferred from an API setter.

### Output offset is not live availability

- Signalsmith preserves the raw input-latency + output-latency offset. No `.seek()`
  with future source data or offline pre-roll is used to make a live configuration
  appear faster. Processing receives equal input/output counts.
- Rubber Band gets only its recommended **zero** start pad, then its queried start
  delay is discarded as its API recommends. Padding is before source time zero;
  no future source samples are used. That aligns stored output, **not** live delivery.
- Fixed-capacity FIFOs capture everything the native APIs retrieve, with bounded
  retrieval work and explicit overflow/errors. Host partitions do not change the
  fixed input quantum. Output is a variable-count **offline sink**, not yet a
  production one-sample-in/one-sample-out live adapter with a fixed latency reserve.
- Every output chunk records its contiguous output range, native consumed-source
  count and **callback-return** source count. The latter prevents backdating samples
  released mid-callback. Callback wall time is measured separately. A future live
  output FIFO may add latency; no physical monitoring/PDC acceptance is claimed.

Finite zero-tail input and finalization are explicit, not secretly truncated to a
perfect duration. Reports retain source count, start pad/trim, zero-tail count,
retrieved count, last nonzero sample and post-source tail energy. Raw float32 stems
and IEEE-float WAVs preserve every amplitude (including overs/unsafe artifacts).
The WAVs include a `fact` sample count. Nothing plays audio automatically.

## Measurements and failure handling

The complete matrix has **930** case/configuration runs at 44.1/48 kHz:
- All nine static shifts 0/±3/±7/±12/±24 on 1-second known-F0 low/mid/high harmonic
  probes, **one and three instances**, for every configuration/rate.
- The same shifts/counts on frozen broadband resonances for independent synthetic
  formant measurements; no claim that these are real-vocal formant references.
- A nine-event ratio sweep with distinct three-voice controls, fresh-process repeats
  and mixed callback partitions. Known unity impulses and non-unity level steps.
- Frozen missing fundamentals, pitch steps, glide/vibrato, bleed, noise, silence
  and level probes. No ordinary check regenerates the frozen expected assets.
  Moving-pitch source-grid errors are retained as separate stable/expressive groups
  with an explicit 4096-sample observer, not discarded or converted to tracker truth.

Before candidate grading, independent tools must recover known perfect target tones
across the complete output range, synthetic resonances and introduced unity delays.
The full calibration has 60 instrument cases. Accuracy uses a full-range independent
offline estimator, never a search narrowed around the expected answer. Eligible
missing F0 estimates remain failures; short/unsupported observation windows are
reported rather than fabricated. These sparse analytic frames are not independent
singer statistics or full vocal accuracy qualification.
PR 04 uses versioned offline normalized autocorrelation with locally interpolated
peak **heights before ranking**. Otherwise integer-lag sampling can reject a high-F0
fundamental and prefer a doubled period. A known C8 control exposed this instrument
defect; its failed calibration remains at
`build/engine-research/20261022T211250Z-9332a7a2/report.json`. The corrected instrument
passes the 60-case full-range calibration (also archived separately). No expected
candidate answer enters its search, no engine audio is modified to fit it, and the
frozen PR 02 instruments/assets are unchanged. Earlier uncalibrated pitch scores
are not grounds for an engine verdict.

Unity impulse correlation is used **only at unity**. Shifted timing uses a known
amplitude step and a 5 ms RMS observer, with raw output and causal-availability
timestamps. Ratio settling retains the independent observer's 4096-sample window,
10 ms grid and completion of a 20 ms correct dwell. Its centered-window lookahead
is included in reported availability, never backdated to the center or dwell start.
It is a conservative **observer-inclusive** measurement, not isolated engine latency
or the production tracker's recognition response. Do not reject an engine solely
because that observer cannot resolve a tighter response target.

Raw peak, adjacent-sample step, RMS/gain and tail values are descriptive artifact
proxies—not confirmed clicks, missing consonants or human naturalness ratings.
All failed case IDs remain in per-configuration summaries; averages cannot hide
failed octaves/registers. Configurations remain research candidates, not approved
product choices. No engine family is discarded from one preset's result.

### Adapter correctness versus native engine gates

A deterministic passthrough control must preserve exact PCM bits through the same
adapter at 32/64/128/257/512/1024 and mixed partitions. FIFO wrap and overflow are
tested. Native input hashes and control chronology must also remain identical.
Fresh **same-partition** controls distinguish fresh-instance variation from host
partition effects. Raw native repeat and reset errors are compared against frozen
max-absolute/RMS tolerances, per voice—not pooled to conceal one bad harmony.
Failed native repeats/resets retain their raw outputs and timelines.
For reset length differences, overlapping-sample errors and unmatched-tail peak
are also recorded. This distinguishes native end-padding/count variation from
audible waveform disagreement without trimming either raw result into a false pass.
Reset-silence self-tests accumulate their observations and save failing stems and
timelines before writing the complete gate report and returning failure. Separate
leaky-transport negative controls verify this failure-retention path; their reports
are explicitly diagnostic, not engine observations.

Crucially, a passing adapter/ASan/TSan test is **not** a passing native repeatability,
pitch, timbre, allocation or live-latency gate. The machine reports carry those
separately. No test is weakened into declaring an engine failure successful.

Callback timings come only from optimized, unsanitized, allocation-audited Release
binaries. They include fixed-quantum bursts, all requested instances and bounded
hash/telemetry instrumentation. Peak/p99.9 occupancy, overdue calls and allocation
calls are retained, with raw callback CSVs. Cold setup padding, constructor scope,
reset and finish are distinguished. Deliberate C/C++ allocation controls must first
verify the test interposer. As in PR 03, that audit is disabled under sanitizers;
ASan/TSan do not substitute for a normal Debug/Release allocation audit.

## Reproduction and provenance

```sh
# First use only: acquire free, checksum-pinned source archives; no installation.
python3 scripts/engine_dependencies.py --destination build/engine-release/_deps

make engine-check
# Or product regressions plus isolated engines in one stable-source workflow:
python3 scripts/check.py --full --offline --engines
```

`--quick` explicitly runs incomplete smoke coverage; `--no-research` runs only native
checks. Neither substitutes for full PR 04 evidence. No network is used with
`--offline`; modified archives/source trees are refused and preserved. Upstream
build systems cannot fetch optional packages. The ordinary AU build is unchanged.

`build/engine-checks/*/report.json` records profiles, binary/dependency identities,
native adapter results and separate engine-gate failures.
`build/engine-research/*/report.json` retains complete case lists, calibration,
per-configuration summaries, callbacks, control/availability CSVs and raw renders.
Source snapshots and exact binaries are archived for research reproducibility.
Compiled native source identity, build cache, source fingerprints and canonical
dependency verification reject stale binaries or edits during measurement.
Every fingerprinted file is archived, including dirty tracked orchestration helpers,
not just new engine files. Shared-cache archive locks protect concurrent build
directories; verified downloads are published atomically, never partially visible.

Private development requires an explicit corpus path under ignored `evaluation/`:

```sh
python3 scripts/engine_evaluation.py private --development-corpus evaluation/your-corpus/corpus.json
```

The existing permission/split/hash validator is mandatory; there is **no holdout
mode**. Two registered, completed, agreeing human annotations are required before
private oracle renders. Audio/annotations are hashed and decoded from their actual
immutable byte snapshots. All private identities, rendered stems and derived
reference/measurement evidence stay under ignored `evaluation/pr-04/`. Uncertain
reference frames are excluded and reported; unstable expressive frames/errors are
retained separately rather than tuned away or counted correct. Agreement is not
proof of truth. Current missing references remain **pending**, not automatic ground
truth from tracker estimates or old whistles. Rhythmic/bending clip c remains required.
Standalone private runs retain the same complete source/binary/runtime/dependency
and compiler/build provenance as analytic research, with before/after verification.

### Review corrections

An independent, read-only OpenCode review in the bottom-right Herdr pane found
seven harness/reporting/provenance defects. The corrections preserve numerical
targets and all negative evidence:

1. Source-supported pitch windows remain eligible when engine output is truncated;
   missing output is now an explicit failed estimate, not a smaller denominator.
2. Configuration summaries include frozen stable source-grid pitch failures, while
   retaining expressive/uncertain/no-support groups and the pending stress policy.
3. Successful and unresolved ratio events and missing/unobservable envelopes remain
   identifiable in summaries. Observer limitations are not intrinsic-latency verdicts.
4. Reset-silence gate failures retain complete raw evidence before failing.
5. Private-only runs archive and verify exact build/runtime provenance.
6. Research source snapshots include dirty tracked helpers as well as new files.
7. Shared dependency downloads are serialized per archive and published atomically.

Regression tests cover truncation, frozen-grid and unresolved-observer summaries,
private provenance/runtime changes, dirty-helper snapshots, concurrent cold-cache
preparation and native reset-failure evidence retention. The prior complete baseline
remains archived at `build/checks/20261022T212126Z-5ef207ad/environment.json` and
`build/engine-research/20261022T212404Z-2711c106/report.json`; its limited summaries
are superseded by the corrected reporting, not silently relabeled as current results.
Re-review confirmed all seven original fixes and caught one new parallel-test
isolation issue. Retention controls now use per-engine, per-invocation directories
so concurrent tests cannot count one another's reports.
The same reviewer verified that final fix and reported **no remaining concrete
code-review blockers**. All eight findings are closed by independent source review;
test/measurement results are reported separately below.

## Exploratory observations — not final qualification

The initial 40-case smoke run is retained at
`build/engine-research/20261022T203631Z-d4eeeb07/report.json`, explicitly incomplete.
It flagged apparent octave-shift pitch misses, synthetic formant misses, and cold
Rubber Band processing allocations. Its pitch scores predate full-range instrument
calibration and are superseded, not grounds for rejecting an engine. Independent
timing/allocation/native-repeat observations remain retained on these pins/wrappers,
not blanket verdicts on either engine family.
Rubber Band's reset now installs the intended initial ratio **before** `reset()`
because that API retains current ratios; prior exploratory reset differences are
preserved, not silently blamed on the engine.

An intermittent Signalsmith fresh-instance mismatch was then reproduced with
**identical 128-sample host partitions** and a fixed seed: max absolute difference
approximately 0.0223. The failing executable/source and a bounded reproduction are
archived under `build/engine-exploratory/20261022T204239Z-fresh-repeat-failure/`.
Later runs can pass; it is not called fixed. Native input/control transcripts and
the deterministic transport control prevent misattributing it to partition drops.
Root cause (including possible backend numerical sensitivity) is not established;
this is an explicitly retained native-repeatability gate miss.

Source inspection notes: Signalsmith configures/reserves spectral buffers, while
its processing path resizes a pre-capacitated scratch vector; actual callback
audits remain the test, not an assumption. Rubber Band's selected vDSP FFT code
has lazy `initFloat/initDouble` allocation sites (`src/common/FFT.cpp`); its R3
scale objects own FFTs. This is a follow-up lead consistent with cold FFT work,
not a call-stack-proven attribution of every observed allocation. A validated
warm-up/preallocation strategy would be separate evidence, not an assumed fix.

## Final engineering qualification — 2026-10-23

`python3 scripts/check.py --full --offline --engines` passed against unchanged
sources. Product regressions and isolated engine contracts passed in Debug,
Release, ASan and TSan. The normal allocation auditor self-verified; sanitizer
timings/audit counts were not used as performance evidence. Twenty engine Python
regressions passed, and all four Release native tests also passed concurrently
under `ctest --parallel 4`, including both negative reset-retention controls.

Evidence:
- Product/full orchestration:
  `build/checks/20261023T134518Z-016aaf92/environment.json`.
- Four-profile isolated engine checks:
  `build/engine-checks/20261023T134622Z-40c258f2/report.json`.
- Complete corrected matrix:
  `build/engine-research/20261023T134741Z-81ad9ed5/report.json`.
  **930/930 rendered**, zero native render errors, **60/60** known-truth
  calibration cases passed, complete source/build/runtime snapshots retained.
- PR 02 regression/calibration:
  `build/evaluation-checks/20261023T135351Z-65e2904e/report.json` passed.
- Private preflight:
  `evaluation/pr-04/20261023T135351Z-84ae23f2/private-report.json` and its
  `provenance.json`: three development sources, **zero reference-ready sources**.
  No private audio was rendered, graded, uploaded or treated as human truth.

### Three-instance configuration results

Failure counts below are **case counts**, not frame/singer confidence estimates.
Static pitch has 27 cases per row; synthetic formants have nine. Frozen stable-grid
failures are shown separately (11 frozen probes, some with no eligible voiced
support); expressive/uncertain/no-support observations remain in the raw report.
Unity delay is causal callback-return delivery, not just stored-waveform alignment.

| Configuration | Rate | Static pitch misses / 27 | Frozen stable-grid misses | Formant misses / 9 | Unity delivery ms | Cases with callback allocations / 52 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Signalsmith 512/128 | 44100 | 17 | 3 | 7 | 12.97 | 0 |
| Signalsmith 1024/256 | 44100 | 13 | 3 | 6 | 24.58 | 0 |
| Signalsmith 2048/512 | 44100 | 8 | 3 | 4 | 53.61 | 0 |
| Rubber Band R3 short | 44100 | 4 | 1 | 8 | 47.80 | 52 |
| Rubber Band R3 standard | 44100 | 4 | 2 | 8 | 88.44 | 52 |
| Signalsmith 512/128 | 48000 | 15 | 4 | 7 | 12.17 | 0 |
| Signalsmith 1024/256 | 48000 | 14 | 2 | 7 | 22.83 | 0 |
| Signalsmith 2048/512 | 48000 | 6 | 3 | 6 | 44.17 | 0 |
| Rubber Band R3 short | 48000 | 4 | 1 | 7 | 49.50 | 52 |
| Rubber Band R3 standard | 48000 | 4 | 2 | 7 | 81.50 | 52 |

Both engines retain accuracy/formant limitations; no preset passes all approved
numerical requirements. The smallest Signalsmith configuration is the only tested
one with unity-impulse delivery below the 15 ms live-processing ceiling, but that
does not qualify its non-unity response, quality, host route or physical monitoring.
The larger windows remain quality/research comparators, not hidden live fallbacks.

Across all one-/three-instance cases, summaries retain 202 pitch-failed cases
(including 24 frozen stable-grid cases), 134 synthetic-formant-failed cases,
372 allocating-callback cases (all primary Rubber Band renders), three failed
fresh-repeat cases and eight failed reset comparisons. All failed IDs/raw outputs
remain available. There were zero observed overdue callbacks and no unity query
offset mismatches. Worst per-case p99.9 occupancy across three-instance cases was
36.60% on this instrumented run; this is not a host soak or hard-real-time guarantee,
and the callback-allocation failures remain disqualifying evidence for these wrappers.

Of 320 ratio-event/voice observations, **113 remain unresolved** by the declared
observer; none is omitted from summaries or automatically called an intrinsic
engine-latency failure. All envelope observations were observable. In particular,
Rubber Band standard's shifted amplitude-step delivery reached 226.94 ms at
44.1 kHz and 218.67 ms at 48 kHz; its aligned unity waveform does not establish
acceptable non-unity delivery. Successful observer measurements retain their full
lookahead/dwell/callback clocks as well.

Rubber Band's eight dynamic reset comparisons differ in overlapping audio, **not
merely EOF zero padding**: maximum differences range approximately 0.441–0.880,
per-voice RMS approximately 0.125–0.205, with zero unmatched-tail peak. Raw length
differences and both waveforms remain preserved; the reset ordering correction
does not resolve these failures. Reset-to-silence gates passed on these runs.

Signalsmith repeatability remains intermittent: this qualification's Debug
self-test had seven failed voice comparisons while its Release self-test passed.
The separate Release matrix still had three fresh-process repeat failures on the
512/128 configuration (maximum difference up to approximately 0.138). Neither
the passing Release self-test nor clean sanitizers erase those failures. Identical
native-input/control chronology and the independent transport checks passed.
Root cause remains unproven; no numerical tolerance was relaxed.

**Outcome:** engineering implementation/review/qualification is complete, with an
explicit negative candidate report—not product or architecture acceptance.
Real-vocal references, listeners, Logic/device monitoring, remaining protocol/resource
approvals and architecture acceptance stay open. Rhythmic/bending clip c remains
required. Product `Source/`, root `CMakeLists.txt`, frozen fixtures and approved
contracts are unchanged. Only evidence documentation was updated after qualification;
no engine is integrated or selected. User approved local commit/merge of this
engineering/research milestone on 2026-10-23, retaining all negative results and
pending gates. That approval does not authorize a push, installation or host operation.
