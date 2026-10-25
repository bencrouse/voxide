# PR06A completion attempt — calibrated synthetic result

**PR status: PR06A is BLOCKED at its technical feasibility/decision gate.**
The approved bounded experiment reached a genuine stopping condition, not an
unfinished tooling step. Do not call PR06A accepted/complete, merge another partial
milestone as its completion, or start PR06B/product integration on this evidence.

The previous `534f6e5` local merge preserved research/tooling, not PR06A acceptance.
These completion changes/results are preserved on `pr-06a-completion` as an
**incomplete research checkpoint**, not a completed or merged PR06A. The
`evaluation-au-prototype` branch starts from that checkpoint for the next task;
see the [review/handoff](evidence/pr-06a/checkpoint-review-001.md). The PR
sequence now has an explicit stop: PR00–05/research are locally merged, PR06A is
blocked by the findings below, and PR06B–10 remain unopened/blocked. No renumbering
or retrospective qualification is used to reconcile that sequence.

## What was actually completed

- Implemented the approved A1 calibration and matched A2 prescribed/tracked
  verification, with frozen [execution contract](evidence/pr-06a/signalsmith-verification-execution.json),
  exclusive stage claims, generated-only inputs, fixed gains/alignment, original
  numerical gates and append-only raw/reference/provenance evidence.
- **A1: 36/36 fixtures pass**: 28 positive rate/pitch/shape combinations and eight
  wrong-target/unvoiced negatives. Every eligible positive pitch observation is
  within 25 cents; wrong semitone/octave references are exposed, and silent/noise
  inputs do not earn fabricated voiced-accuracy passes. No engine runs in A1.
- **A2: all 72 native cases executed**, covering both rates, E2/A3/C6, sine and
  six-harmonic input, octave/upper/lower voicings, and prescribed versus tracked
  C-major paths. This includes exact ±12-semitone endpoints and unchanged lead.
- Independent input/control hashes, native configuration/guard identity, complete
  control/packet clocks, finite output, source duration/tail, lead null, both fixed
  sums and callback checks pass for all 72 captures. Source tracking and target
  interval checks pass against generated truth in every case.
- **Output pitch fails in 34/72 cases**. Each mode passes 19/36 cases and fails the
  **same 17 conditions**. Only 72/108 voice groups per mode pass the retained output
  gates (144/216 overall). No failed voice is hidden by a complete-mix result.
- **A3: deliberately NOT EXECUTED**, as required after A2 failure. Its 16 reserved
  captures are not reassigned to retries, tuning or another engine. No correction
  allowance was spent; no DSP tuning or native rerender occurred.

## Matched-path output results

Each cell counts complete three-voice cases passing out of six shape/voicing
combinations. Any failed voice or mandatory control gate fails the case;
output-pitch failures, not source/control failures, cause these results.

| Rate | Input register | Prescribed F0/targets | Tracked scale |
| --- | --- | ---: | ---: |
| 44.1 kHz | E2 | 0/6 | 0/6 |
| 44.1 kHz | A3 | 4/6 | 4/6 |
| 44.1 kHz | C6 | 6/6 | 6/6 |
| 48 kHz | E2 | 0/6 | 0/6 |
| 48 kHz | A3 | 3/6 | 3/6 |
| 48 kHz | C6 | 6/6 | 6/6 |

All sampled source/control accuracy fractions are 1.0. Maximum applied interval
error is approximately `7.11e-15` semitones (floating-point rounding). Source F0
and selector controls therefore cannot by themselves explain the output failures;
the prescribed path fails the same conditions without relying on the tracker.
This isolates the blocker toward the native processing/output measurement path,
not a fabricated source-key diagnosis or a request to retune the lead.

The prescribed path is diagnostic only. Neither its passing cases nor the C6
subset qualifies the full E2–C6/continuous ±12 support envelope, other scales or
actual vocals. Clean-tone calibration does not establish human pitch truth for
every complex transformed waveform.

## Illustrative retained-output diagnostics

No new renders were made for these checks. A descriptive 65,536-sample Hann-windowed
FFT ranks peaks over 16–5,000 Hz without searching around the desired answer.
It is **not** a replacement pitch grade or a changed acceptance threshold.

| Prescribed input/voice | Intended output | Strongest spectral peak, approximately |
| --- | ---: | ---: |
| 44.1 kHz E2 sine, octave down | 41.203 Hz | 40.274 Hz |
| 44.1 kHz E2 sine, octave up | 164.814 Hz | 168.250 Hz |
| 48 kHz A3 sine, octave down | 110 Hz | 111.966 Hz |
| 48 kHz E2 six-harmonic, lower third | 65.406 Hz | 61.706 Hz |

The first three examples corroborate persistent detuning on simple tones rather
than merely a short transition-spanning window. Some complex outputs produce
subharmonic autocorrelation estimates; do not label every such estimate a confirmed
perceptual wrong note. Keep the observations and original scoring unchanged.
Many out-of-tolerance spans occupy essentially the whole eligible steady interval
(about 2.81/2.83 seconds), not just a hidden startup frame.

Thresholds remain ±25 cents, ≥99% stable accuracy, <0.1% octave-error fraction and
≤50 ms sampled wrong-note span. A pleasant texture does not waive them; “processed”
is not permission to silently widen them or exclude E2.

## Safety/performance and limits

- All 72 captures have zero callback allocation calls and zero observed overdue
  callbacks. Worst per-capture p99.9 virtual callback occupancy is **11.94%** on
  this run. This is not Logic or universal hardware qualification and does not
  offset output-pitch failures.
- Dense measurement uses the unchanged independent 8192-sample meter, 10 ms
  reference centers, declared boundary/full-support exclusions and exact software
  alignment. Missing eligible estimates count as wrong. Correlated frames are
  descriptive, not independent singer/listener samples.
- No private recording/corpus was read, private render/preview repeated, audio
  played or host/device operated. No engine/backend/upstream source or product AU
  changed. Existing a/c feedback and historical failures stand.
- Rubber Band remains a sonic reference with an unresolved allocation failure;
  these Signalsmith results do not automatically select it as the product engine.

## Evidence and code validation

Ignored synthetic evidence retains exact source/binaries, generated inputs,
events/references, controls, raw channels and observations:

| Evidence | Path | Report SHA-256 |
| --- | --- | --- |
| A1 | `build/studio-verification/20261024T200210Z-edb48fa4/report.json` | `18fab35185aeb022119290c91dde7fc9c3d9cf29ae5e023143e23e5070f76d38` |
| A2 | `build/studio-verification/20261024T220613Z-10d6c48c/report.json` | `9a894f28724e6de90334a679f4c930911b45a9ea92c34f4064a8baa27bb42074` |
| Attribution | `build/studio-verification-attribution/20261024T221611Z-f5534836/report.json` | `e9cc0bc22349f5bc99c0091dfb59dd28de394b28477fa7eccf799f515b147bd2` |

A1/A2 artifact manifests verify unchanged. A2's source/build fingerprint is stable;
input and serialized control FNV hashes independently agree with native counters.
The calibrated measurement driver and frozen meter are unchanged between stages.
No historical failure was regraded or overwritten.

Driver validation passes **186 Python tests** and full product
Debug/Release/ASan/TSan at `build/checks/20261024T220420Z-2511d1ba/environment.json`;
A1's earlier qualification is `build/checks/20261024T200029Z-67276484/environment.json`
(176 tests). Those test passes validate tooling, **not** the 34 failing DSP cases.
The new completion drivers are self-reviewed/tested; the prior independent tooling
review is not misrepresented as independent review of this new code.

## Required decision, not another automatic loop

PR06A cannot meet its credible technical-path gate on this result. **Hold PR06B.**
Before more engine work, decide whether to authorize one diagnosed, explicitly
bounded correction/retest or stop/reconsider this approach. No correction, new
configuration sweep, engine shopping, upstream patch or requirement relaxation is
authorized by this experiment. Full vocal references/listening, support, formant/
onset criteria and host qualification remain separate gates, not excuses to call
this pilot passed.

## Subsequently approved wrapper audit

The user subsequently approved the bounded wrapper/configuration investigation
and at most one evidence-backed correction/regression. Approval is **granted**, not
pending. The [audit](evidence/pr-06a/wrapper-audit-001.md) found no demonstrated
API/streaming defect or justified replacement configuration. Blindly adopting the
library presets exceeds the full latency budget; another manual window/hop is an
unproven hypothesis. **Stop/reject the current 2048/512 configuration** on its
retained failed evidence rather than spend the allowance on speculative tuning.
No DSP change or new native run occurred; the allowance remains unspent. A3 and
PR06B remain blocked. This is not a finding that all configurations are impossible.

## Subsequently authorized Rubber Band allocation diagnosis

The user next authorized diagnosing the existing Rubber Band allocation blocker.
The [fixed eight-capture investigation](evidence/pr-06a/rubberband-allocation-diagnosis-001.md)
tests silence-only stopped preparation, without changing the product wrapper.
It removes observed callback/finish allocations in these samples but changes
native output lengths and voiced samples in all four paired comparisons. Reject
the preparation; no retry or engine selection follows. Original Signalsmith A1/A2
evidence/grades, A3's stop and PR06B's block remain unchanged. A worker-owned
architecture prototype is proposed separately, not approved by this diagnosis.

## Subsequently approved worker implementation

The user then explicitly approved background processing. The
[implemented worker prototype](evidence/pr-06a/worker-feasibility-001.md) passes all
normal callback-isolation/delivery points: zero callback allocations, exact audio/
control agreement and unchanged 100 ms software alignment. The complete fixed
screen nevertheless fails one first-callback scheduled deadline in a fault case;
the retained failure is not waived. All 14 captures are consumed without retries.
This provides a working normal-case path for the allocation blocker, not a new
pitch grade, full timing/host qualification, engine selection or PR06B go. Original
A1/A2 results and stopped A3 remain unchanged.
