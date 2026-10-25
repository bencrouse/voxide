# Worker feasibility — callback isolation demonstrated; one timing gate fails

## Outcome and project progress

**The background-processing prototype is implemented and works in all normal
sampled cases.** Moving the unchanged Rubber Band engines to worker ownership
reduces normal callback allocation calls from **416 to zero**, with **exactly
identical audio and controls**, no normal delivery misses, and unchanged complete
software alignment of **4410/4800 samples (100 ms)**. This is a concrete resolution
of the native-on-callback allocation mechanism in the isolated prototype—not merely
another proposal, warmup workaround, upstream patch or requirement relaxation.

**The complete frozen screen nevertheless FAILS:** one deliberate-stall capture
has a scheduled callback-finish miss. It occurs on the **first callback, before
the injected worker stall and before processing its first source sample**. Keep this failed
mandatory timing observation; do not relabel the overall screen passed or claim
universal realtime/host safety. The 14 captures are consumed; no retry/tuning ran.

PR06A remains open/blocked at remaining qualification/decision gates, not complete.
The two old direct-callback configurations remain failed for their original
reasons. The new worker architecture has a promising measured normal path, not a
final engine selection or PR06B/product-integration go.

## Approved architecture and unchanged behavior

The user explicitly approved background processing on 2026-10-25 while preserving
sound requirements and the 100 ms ceiling. The
[protocol](worker-feasibility-001.json) froze six processes / 14 native captures.

- `WorkerEvaluation/WorkerEngine.*` gives each voice a native-owner thread. Fixed
  SPSC queues copy each exact input quantum and its ratio/F0 controls in order.
  Output packets carry continuity indices. The callback performs no native
  engine calls, locks, waits, wake syscalls, thread creation or joins.
- Reuse the **unchanged** `InteractionEvaluation/InteractionProcessor.*` tracker,
  scale selector, source-time controls, uncertainty policy, gains, sums, lead
  alignment and 100 ms delivery clock. No user-selected key/scale semantics change.
- Reuse pristine fresh Rubber Band R3 short graphs and unchanged
  `EngineEvaluation/EngineAdapter.cpp`, formant settings, Accelerate/BQResampler
  backend and pinned sources. No audio/silence priming or native reset workaround.
- Construct, finish and join with callback ownership stopped. Worker errors and
  missed delivery latch all harmony/native output silent without altering the
  lead; such a dropout is a **failed observation**, not acceptable musical masking.
- The custom offline coordinator waits **between** callback invocations, never
  inside them. It reproduces the reference deterministically in this harness;
  this is not an implemented/qualified Logic offline-bounce adapter.
- Worker allocations are still present and recorded. This **moves** allocation
  out of the callback; it does not eliminate native allocation or guarantee that
  allocation/scheduler stalls will always fit the deadline.

No AU/product code, private recording or physical host/device operation is involved.

## Fixed experiment results

At each rate/buffer point, one synchronous reference, one wall-clock-paced worker
capture and one coordinated fast-offline worker capture process the same 5-second
engineering scene plus 600 ms supplied zero tail. It includes E2/A3/C6, six-harmonic
tones, noise/uncertainty, bends and four source-time C-major harmony requests.

| Rate | Callback | Reference callback allocations | Worker paced / offline allocations | Worker paced / offline p99.9 occupancy | Normal delivery |
| --- | ---: | ---: | ---: | ---: | --- |
| 44.1 kHz | 128 | 105 | 0 / 0 | 3.25% / 3.10% | Pass |
| 44.1 kHz | 512 | 105 | 0 / 0 | 2.17% / 2.12% | Pass |
| 48 kHz | 128 | 103 | 0 / 0 | 3.53% / 3.57% | Pass |
| 48 kHz | 512 | 103 | 0 / 0 | 2.35% / 2.36% | Pass |

- **12/12 normal captures pass their retained gates.** The synchronous references
  intentionally establish the known allocation failure; their positive-allocation
  control is not a regrading of the old direct-callback implementation as safe.
- All eight worker normal captures have zero callback allocations, underflows,
  late samples, queue/control errors and runtime overruns. All four paced normal
  captures also have zero scheduled callback overruns.
- **14/14 exact comparisons pass:** eight worker-vs-reference and six callback-
  partition comparisons, all ten audio channels with **max/RMS difference zero**.
  Independent input/control hashes and complete serialized control timelines agree.
- Direct/aligned lead nulls, fixed sums, finite output, duration, tail and native
  packet coverage pass. No correlation alignment, gain correction, clipping,
  limiting, source exclusion or modified pitch threshold is used.
- Normal worker body allocations total **832**, separately retained. Individual
  graphs record 105 at 44.1 kHz / 103 at 48 kHz, matching their reference counts.
  Setup/finish/destruction counts also remain separately recorded. Maximum normal
  input-queue high-water is ten commands, including stopped startup padding.

These are bounded synthetic observations on this run, not universal hardware or
physical monitoring guarantees. The lead is delayed exactly 100 ms in software;
actual AU PDC, transport, save/reopen and Logic bounce remain untested.

## Deliberate-stall negatives and the unwaived timing failure

At each rate/128-frame callback, voice 0's worker pauses 200 ms at process command
64. Both cases expose missed native delivery, retain the missed/late counts and
latch all three harmony outputs silent while preserving the unchanged lead.

| Rate | Voice-0 underflows / late samples | First fail-closed sample | Callback allocations | Scheduled callback-finish misses |
| --- | ---: | ---: | ---: | ---: |
| 44.1 kHz | 8108 / 8108 | 8764 | 0 | 0 |
| 48 kHz | 9117 / 9117 | 9079 | 0 | **1** |

The missed scheduled finish is in `48000-128-fault/callbacks.csv`, **begin=0**:

- scheduled 128-frame end: **2,666,666 ns** after the chosen timer epoch;
- callback start lateness: **3,917,375 ns**;
- callback computation: **2,042 ns**, zero allocations;
- observed finish: **3,919,417 ns**, exceeding the scheduled end by **1,252,751 ns**.

This is initial harness dispatch lateness, not evidence of a 200 ms native stall
inside the callback. It precedes the deliberate fault and source processing.
Workers may already have processed stopped startup padding; no scheduler trace
establishes the underlying cause of the late dispatch or rules out worker load.
Nevertheless the protocol explicitly includes dispatch lateness in the scheduled
finish gate, so its original **`callback_budget: false`** and overall
**`worker_screen_failed_stop`** remain unchanged. No first-frame omission, shifted
epoch, threshold waiver or “external jitter” exception turns it into a pass.

All captures have zero *runtime-only* overdue callbacks. That narrower fact must
not conceal the one scheduled-finish miss or the two intended worker underflows.

## Evidence and validation

- Main report: `build/worker-feasibility/20261025T140514Z-92f67612/report.json`
- SHA-256: `dde15242c093954f9c5a7025e66b697a888256181df151ad1d3fdf9a5f1ea4ac`
- Additive retained-clock attribution:
  `build/worker-feasibility-attribution/20261025T140830Z-f06384f1/report.json`
- SHA-256: `5cbe1eca52a8d4b58b78656185c6a337dc5c5ad4b7fc33eed01bcfa32a1558c6`
- Qualification: `build/worker-feasibility-qualification/20261025T140510Z-5c9373b2/report.json`
  — **199 Python tests**, Release/ASan/TSan fake-engine contracts pass. Tests cover
  native thread ownership/lifetime, ordered/split transfers, callback allocation
  detection, separately visible worker allocations, overflow, nonfinite failure
  and finalized-restart rejection. Sanitized runs are not performance evidence.
- All six native processes / 14 captures completed once. Source, binary and audit
  library identities were unchanged during execution. Native runs were serial,
  without concurrent builds, profilers, stack capture or parallel FFT analysis.
- The manifest retains raw channels, callbacks, full telemetry, counters, exact
  binary/audit library, compile commands, source snapshot and verified pinned
  dependency provenance. Additive attribution makes no new native execution or
  grade change. Earlier A1/A2 and Rubber Band failed evidence remains intact.
- All **19,144 raw callback clock rows** independently verify: scheduled ends equal
  source positions/rate, and paced finishes equal scheduled start plus measured
  start lateness and computation. This retains exactly the original single miss.
- No product commit/merge/push or independent completion-code review is claimed.

## Back to the plan

The allocation investigation now has a working normal-case implementation. Do not
return to engine shopping, discarded priming or the failed Signalsmith settings.
The remaining architecture issue is **the recorded timing screen**, not another
engine-allocation guess: any future timing protocol must explicitly establish its
stream-start/dispatch clock before execution and preserve this first-frame miss.
There is no retry authorization under the consumed `001` claim.

After that gate and review are resolved, continue PR06A's musical verification
with this exact architecture and calibrated meter, before PR06B. Exact agreement
with Rubber Band's existing output is **not** a pitch/formant/support pass. Keep
E2–C6, inclusive ±12, both rates, three voices, unchanged lead, required expressive
challenge c, independent references/listening and host/PDC gates intact.
