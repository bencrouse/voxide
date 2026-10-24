# Bounded architecture investigation — 2026-10-23

## Decision

**Historical scope note — 2026-10-24:** the conclusion below evaluates the original
combined live/mixing brief and remains unchanged. The user subsequently prioritized
recorded-vocal scale mode, inclusive ±12 support and intentional processed character,
referencing “Bottomliners,” 1:30–2:00. This permits planning the separate PR06A studio
pilot, **not** treating these failures as passes or authorizing product integration.
The current sequencing and outstanding protocol approvals are in
`PROJECT_PLAN.md` and `DECISIONS.md`. No new measurements or listening are implied.

**Do not proceed to product integration under the tested scope.** The authorized
batch and one corrective retest leave no demonstrated candidate meeting live
timing, quality, finite output and native-state requirements together. This is a
no-go for the current implementation/configurations, **not proof that a professional
harmonizer is impossible**, or that every possible use of these two libraries fails.
Further tuning, dependency patches, engines or requirement changes need a new,
explicit scope decision. Mixing-only success does not satisfy the live brief.

The architecture review was right to challenge PR05's broad negative headlines:
some latency was introduced by our schedule and most unresolved response
observations were unresolvable by that instrument. Correcting that interpretation
does **not** remove the independently corroborated quality/safety failures below.

Baseline: PR05 commit `dda47a7`, retained unchanged in git. Work is isolated on
`research-architecture-feasibility`, uncommitted. The product AU remains dry.
No spend, installation, playback, capture, device/Logic operation, private-audio
access, holdout access, new engine family, upstream patch, commit, merge or push.
All original ranges, three available harmonies, unchanged lead and numerical
requirements remain intact; no common consonant policy is selected.

## What was executed

`ArchitectureEvaluation/` is a separate CMake project using the exact PR04 pins.
It adds only the authorized **256/32** Signalsmith preset and a compile-time
comparison of its existing Accelerate and built-in FFT backends. Each render has
three independent states. The thin Signalsmith wrapper retains PR04's seed,
transpose/formant settings and public API; Rubber Band uses the unchanged PR04
adapter with availability-bounded retrieval. No engine links into the AU.

The final batch contains **72 native cases**: 66 finite completions and six
explicit nonfinite-output failures. It includes both rates, E2/A3/C6 steady
controls with −24/+7/+24 shifts, common-shift target changes at three quantum
phases, held/unheld scheduling controls, the conditional trailing-tracker screen,
exact retained-call replay, and Rubber Band cold/warm/primed diagnostics. This is
a focused falsification set, not a replacement full singer/listening matrix.

### 1. Measurement chain

- Independent positive-crossing periods, with period-consistency and sinusoidal
  energy checks, corroborate the existing full-range NACF on analytic sine-like
  output. Neither instrument receives an expected-answer search interval.
- **10/10** steady controls spanning approximately 20.6–4186 Hz at both rates
  pass both instruments. **Four** immediate/80 ms-delayed response controls are
  correctly separated around the 50 ms ceiling. Wrong-octave, silence, mixed-tone,
  insufficient-support, unavailable-output and next-event boundary controls pass.
- Response is measured only after complete periods and a completed ≥20 ms dwell,
  with native packet availability included. Search stops before the next target
  event. No backdating to the first crossing or observer-window center.
- This restricted observer **cannot qualify general vocal or low-frequency tight
  response ceilings**. Its abstentions are unresolved, not passes or proof of
  intrinsically slow engines. Dense bend controls are not independent note trials.
- Ninety fully supported windows from five retained PR05 oracle/native/mix
  configurations are cross-checked without transition-spanning support. The
  independent sine-like screen abstains on 63 of those harmonic/distorted windows;
  only three are independently confirmed pitch misses by both instruments.
  That is not exoneration or a new singer-accuracy estimate. New simple-tone
  controls below provide much clearer corroboration.

### 2. One alternative source-time schedule

The alternative removes the blanket half-support-plus-hop input hold. Native
controls remain source-referenced at `input begin - queried control lag`; events
cannot affect earlier source time. Actual PR03 MIDI-selector slot changes at
receipt, native setter calls and observed output have separate logs. The receipt
selector is a diagnostic shadow state, **not** an audio-path response pass.

| Schedule / preset | Rate | Maximum sampled native delivery | Request → native setter |
| --- | ---: | ---: | ---: |
| No hold, 512/128 | 44.1 kHz | 14.51 ms | 8.75–10.86 ms |
| No hold, 512/128 | 48 kHz | 13.33 ms | 8.00–9.35 ms |
| No hold, 256/32 | 44.1 kHz | 6.53 ms | 3.67–4.33 ms |
| No hold, 256/32 | 48 kHz | 6.00 ms | 3.33–3.67 ms |

Both FFT backends have the same scheduling results. Reintroducing the original
hold raises 512/128 sampled delivery to approximately 35.10–37.21 ms and maximum
setter response to 31.10–33.54 ms. Those are **schedule-control failures**, not
intrinsic engine-delay conclusions. The report's per-backend grouped blockers
include held controls; use the per-case records/table above to distinguish them.

The small preset passes this **oracle delivery/setter timing screen**, including
all three tested event phases at both rates. That is not CPU/host/physical
monitoring qualification, shifted-envelope alignment proof or correct audible
pitch. The strict native-setter screen is kept separate from the approved musical
applied-state requirement; changing its interpretation cannot repair quality.

Only then was one trailing-history schedule tested with the unchanged tracker:
choose the newest available frame whose support ends no later than the native
processing-source time, rather than holding all input for its midpoint. No future
frame, prediction, lead tuning or retroactive audio correction is used. Its support
span is logged, not asserted to be instantaneous F0. Correct high-register cold
decisions still take **44.90 ms at 44.1 kHz / 40.00 ms at 48 kHz**, versus the
30 ms high-register P95 target. These individual analytic trials are not a P95
population estimate. The tracker is not qualified; no acquisition sweep followed.

### 3. Quality and finite-output blockers remain

On new fully supported oracle steady plateaus (including those inside target-change
trials), both instruments agree on many wrong frequencies:

| Backend / preset | Observations | NACF misses or unavailable | Independently corroborated >25-cent misses |
| --- | ---: | ---: | ---: |
| Accelerate 512/128 | 72 | 58 | 50 |
| Built-in 512/128 | 72 | 58 | 50 |
| Accelerate 256/32 | 66 | 57 | 41 |
| Built-in 256/32 | 66 | 57 | 42 |

These are correlated descriptive controls, not 99%-accuracy estimates for singers.
They are sufficient to reject a claim that *all* observed problems are tracker
errors, transition windows or autocorrelation mistakes. Some extreme outputs
remain ambiguous to the corroborating instrument and are not declared confirmed
wrong fundamentals from NACF alone.

More decisively, **six E2 small-preset cases produce nonfinite raw output**: both
rates and both backends in oracle mode, plus both trailing-tracker E2 cases.
Every voice is affected. Oracle cases first become nonfinite at raw sample 128,
then remain invalid through the primary voiced material. Trailing cases begin at
raw sample 2112/2048 respectively. Raw float payloads, first-invalid indices and
counts are retained; no playable WAV or quality pass is generated for them. A
faster unusable or nonfinite configuration is not a product survivor.

### 4. Native initialization, repeatability and lifecycle

**Signalsmith:** the exact fixed native calls of retained failing `case-0002` were
replayed—not a replacement easy workload. All native input/control hashes match
the historical run. Three executions/backend compare fresh processes and a
process warmed by a complete prior workload followed by a fresh graph.

- Accelerate: cold repeats match, but warmed-process reconstruction differs by
  **max 0.184456 / RMS 0.016689**. The historical problem is reproduced.
- Built-in FFT: both comparisons are exactly equal in this limited set. This
  narrows attribution toward the backend integration; it does not establish
  universal determinism. Steady-quality and small-preset safety failures persist
  on that backend, so it is not selected as a fix.

**Rubber Band R3 short, 48 kHz:** stack capture attributes 96 allocations to lazy
`D_VDSP::initDouble` FFT setup, plus three static / seven changing-ratio
`BQResampler::state_for_ratio` allocations. Stacks are captured in separate
diagnostic runs; unwinder costs are never realtime performance evidence.

| Stopped setup strategy | Static workload callback allocations | Changing-ratio callback allocations | Eventful output vs fresh |
| --- | ---: | ---: | --- |
| Cold graph | 99 | 103 | Reference |
| Warm workload, destroy/rebuild graph | 99 | 103 | Exactly equal |
| Prime exact workload on same graph, reset before finalization | 3 | 0 | Static equal; changing fails |

The zero-allocation changing-ratio primed run differs by **max 0.164923 / RMS
0.076440**. Priming therefore cannot be accepted as an allocation fix. Its sampled
delivery is still approximately 56 ms; cold runs reach 56.67–57.33 ms, outside
the live ceiling. Finite future-ratio priming would not establish arbitrary dynamic
ratio coverage even if these samples had matched. No upstream patch was attempted.

The PR05 wrapper's separate finalized-stream restart gap is fixed:
`InteractionEvaluation/InteractionProcessor::start()` now rejects restarting a
finalized graph until stopped reset/reconfiguration reconstructs it. A regression
covers rejection and successful reset/start. This changes lifecycle misuse, not
the processing results in PR05's one-shot archived runs. Experimental graphs are
also single-use; the controlled priming test resets **before** finalization.

## Evidence and validation

- Final product Debug/Release/ASan/TSan regression, **120 Python tests** including
  eight new instrument regressions:
  `build/checks/20261023T195433Z-cfca9f27/environment.json` — pass, source-stable.
- Final isolated qualification:
  `build/architecture-checks/20261023T195433Z-ec6fbbed/report.json` — pass,
  source-stable. Interaction and architecture projects each pass seven native
  tests in all four profiles; 24 additional oracle/trailing native safety renders
  cover the three backends across those profiles. Sanitized runs are not quality,
  allocation or realtime performance passes.
- Final corrected batch:
  `build/architecture-research/20261023T200037Z-24be1cb2/report.json` — bounded
  batch complete, **not product pass**. Exact binaries/runtime/build metadata,
  complete source snapshot, verified canonical dependency identities, input/event
  hashes, raw output, native packets/controls, allocation CSVs and stacks retained.
  Compiled identity, current source/binaries and referenced baseline artifacts were
  checked before/after. Every failure remains present.
- First batch:
  `build/architecture-research/20261023T194701Z-8f975a55/report.json` — retained.
  Its six nonfinite cases failed fast; the corrected batch preserves their raw
  output/counters, bounds response observation before the next event, and adds
  the two same-instance stopped-priming tests. No additional preset or tracker
  tuning was introduced. Earlier safety qualification is retained at
  `build/architecture-checks/20261023T194735Z-b515027e/report.json`.

Reproduction: `make architecture-check` (offline, existing verified cache only).
This deliberately reruns the bounded diagnostics, not an automatic engine search.
The approved contract and frozen PR02/03/product sources remain unchanged. PR04
adapters/evidence are untouched. Only evidence documentation changes after the
final qualification; no private corpus was accessed during this investigation.
The preceding architecture review was independent; this new diagnostic implementation
has been self-reviewed and automatically validated, not independently code-reviewed.

**Stop here:** no expanded quality matrix, PR06/product integration or human/host
qualification was triggered without a technical survivor. Vocal references,
independent listening, expressive/rhythmic clip c, formant/articulation assessment,
Logic/PDC and physical monitoring remain pending—not discarded and not evidence
that a different, explicitly approved architecture could never work.
