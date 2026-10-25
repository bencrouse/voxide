# Rubber Band allocation diagnosis — preparation rejected

## Outcome

**Completed the eight approved diagnostic captures.** The silence-only stopped
preparation eliminates measured callback/finish allocations on these samples, but
**all four fresh/prepared comparisons fail**: every voice has a different native
output length, and common voiced samples differ substantially without realignment.
Reject this preparation; do not adopt it, retune it or repeat the consumed run.

The product wrapper, pinned engine/backend, source support and accuracy/latency
requirements remain unchanged. Rubber Band is not selected or pitch-qualified.
Signalsmith's original 34/72 pitch failures also stand. **PR06A remains blocked;
PR06B/product integration has not started.** This is a concrete feasibility result,
not another partial-tooling merge or proof that no architecture could work.

## What was tested

The user authorized continuation of the recommended Rubber Band allocation
diagnosis. The [protocol](rubberband-allocation-diagnosis-001.json) froze one
source-backed hypothesis and eight captures before execution: both rates,
static/changing prescribed controls, fresh versus silence-prepared graphs, three
voices, a self-generated E2 six-harmonic source and a 600 ms zero tail.

The new isolated `AllocationEvaluation/` target uses the **unchanged**
`EngineEvaluation/EngineAdapter.cpp`, R3 short, formant preservation, high-consistency
pitch mode, Accelerate FFT and built-in BQResampler. It has no private-input route.
All allocation observations are stage-separated; stack capture is diagnostic,
**never realtime/callback timing evidence**. Preparation and reset are stopped
operations; they are not silently excluded from an allocation total.

Unlike the previously rejected exact-audio priming, preparation feeds only zeros.
The half-ratio grows resampler history; two near-unity high-numerator ratios
exercise both phase-table banks. At 44.1 kHz, the constructor's `2*rate` phase
reserve is only 88,200, below the 96,000 rational setting used by this resampler.
This explains additional dynamic table growth at that rate; the zero-input test
checks whether preparation can retain capacity without stale audible history.
One existing-wrapper reset follows preparation, before normal startup padding.

## Retained results

| Rate | Workload | Fresh callback calls | Prepared callback calls | Prepared finish calls | Output comparison |
| --- | --- | ---: | ---: | ---: | --- |
| 44.1 kHz | Static | 100 | 0 | 0 | Fail, all 3 voices |
| 44.1 kHz | Changing | 109 | 0 | 0 | Fail, all 3 voices |
| 48 kHz | Static | 100 | 0 | 0 | Fail, all 3 voices |
| 48 kHz | Changing | 103 | 0 | 0 | Fail, all 3 voices |

All inputs/control bytes and independently recomputed native hashes match within
each pair. Startup metadata remains pad/trim **1280/1280**. Prepared outputs have
**31–126 additional samples per voice** despite unchanged advertised startup
metadata. These are native stream lengths, not measured end-to-end host latency.
No output is cropped, shifted, normalized or retrospectively regraded to hide this.

An additive zero-lag comparison over the common voiced body (raw samples
`1280+rate/2` through `1280+5*rate/2`) finds maximum differences up to **0.355595**
and RMS differences up to **0.151045**. These descriptive checks do not replace
the original mandatory equal-length failure or constitute pitch/listening grades.

### Allocation attribution, including a probe defect

Each fresh capture records **96 `D_VDSP::initDouble` allocations**. The remaining
engine processing allocations are in `BQResampler::state_for_ratio` and, for the
44.1 kHz changing case, five `phase_data_for` allocations. `control()` records zero
allocations; `setMaxProcessSize(128)` is already used. This is not an allocating
application queue or an unbounded callback buffer in the existing product wrapper.

The new diagnostic's first version requested a full scratch buffer on retrieval
even when fewer native samples were available. Rubber Band clamps that request,
returns the actual count and warns. Its first warning creates **one additional
thread-local/runtime allocation per fresh capture**. Logs and stacks expose this
probe artifact. The table above preserves **all original counts**, not a silently
subtracted/regraded result. The existing interaction processor already caps its
retrieval request correctly; this is not a newly discovered product defect.

The diagnostic source is repaired to cap requests to `available()`, with a fake
three-sample engine regression. **The eight captures were not rerun.** Their exact
original source/binary snapshot remains retained. The warning path returns only
available samples, and capture stores only that returned count, so it does not
explain away the paired length/body differences. No performance claim is made
from the warning/stack-instrumented run in any event.

### Why stopped preparation is not neutral

Pinned `BQResampler::reset()` clears the initialized/fade flags, not both history
buffers. `state_for_ratio()` inherits prior buffer size, fill and phase; larger
retained history can therefore alter fresh-stream startup/output even after a
zero-only warmup. `R3Stretcher::reset()` delegates to that reset. Reconstructing
the graph restores fresh behavior but also restores the lazy allocations.

This explains why simply “warm it up” is not an accepted fix. The tested public
wrapper exposes no separate capacity-reservation/reset-to-pristine operation for
these internal objects. No upstream access/patch or new backend was attempted.
The diagnosis does not prove every possible public-API sequence impossible.

## Evidence and validation

- Result: `build/rubberband-allocation-diagnosis/20261024T234246Z-23cf5785/report.json`
- SHA-256: `3ce4c5761b7e79ba274200e08d5c3840eb97c06e49257d8e168059e3183bd481`
- Additive attribution: `build/rubberband-allocation-attribution/20261024T234320Z-3a0559d7/report.json`
- SHA-256: `e15a1237ef91e99650ddfd53480e8d05eb62b0f86e96a6f082526415953d9e64`
- Protocol SHA-256: `ac090b9ab85259ce1eadb6893d764a83e8ee5dceee375663774ae708a5a4658f`
- Executed identity: `e2943d5f534cb2edaa755a842fecb5bb3799f872a314f43812aaf3f5917321aa`
- All eight captures completed; source/binary unchanged during execution. The
  artifact manifest verifies the original raw outputs, controls, allocation CSVs,
  stacks/logs, complete source snapshot, binary/library and dependency provenance.
- All **193 Python tests** pass. The native allocation-positive control passes;
  the subsequent corrected probe's allocation/bounded-drain controls pass in the
  separate `build/rubberband-allocation-toolcheck-002/` build, without native captures.
  This is self-reviewed tooling, not independent completion-code review or new
  full product/sanitizer/host qualification.
- No private recording reads, playback, spending, installs, upstream changes,
  automatic commit/merge/push, A3 reuse or pitch-threshold changes occurred.

## Next plan decision

With both current direct-callback configurations blocked and upstream patches/new
engines excluded, the next plausible investigation is an **isolated worker-owned
rendering prototype**, not another warmup/preset loop. It would keep native engine
allocations off the host callback; it would **not eliminate** those allocations
or guarantee deadlines. This is an architecture change requiring explicit approval,
not permission inferred from the allocation diagnosis.

Before executing that prototype, freeze a bounded test proving preallocated audio/
control queues, no callback locks/waits/allocations, correct source-time controls,
unchanged lead, all three voices, fail-closed deadline handling, deterministic
offline behavior and the **complete ≤100 ms/PDC budget**. Worker jitter and native
allocation stalls must remain visible. Rubber Band still needs separate calibrated
pitch/full-support qualification even if callback isolation succeeds. No prototype
or PR06B go is executed/claimed here.
