# Wrapper/configuration audit — no justified correction

## Approval and outcome

After the failed A2 result, the user approved investigating the wrapper/configuration,
not the tracker, and at most **one evidence-backed correction and one regression**
with unchanged requirements. That approval supersedes the earlier pending-decision
language; it does not authorize a speculative setting sweep.

**No evidence-backed correction was identified. Stop and reject the current
Signalsmith 2048/512 configuration for the retained requirements.** No DSP change,
new build, native render or regression claim was made. The correction/regression
allowance remains unspent, not an excuse to run an undiagnosed experiment.
This is not proof that every Signalsmith configuration is impossible, nor a
selection of Rubber Band. PR06A remains blocked; A3/PR06B do not proceed.

## Audited integration

- `InteractionEvaluation/InteractionProcessor.cpp:234` supplies
  `exp2(shift/12)` to the adapter. `setTransposeFactor()` takes that frequency
  multiplier, not semitones or its reciprocal. The retained independent control
  checks already establish the intended intervals in both modes.
- `EngineEvaluation/EngineAdapter.cpp:28` uses that multiplier directly.
  `setFormantFactor(1, true)` matches the pinned pitch-compensated preservation
  API; disabling compensation would change the required treatment, not repair a
  demonstrated integration error.
- `setFormantBase(sourceHz/sampleRate)` matches the pinned README's explicit
  200 Hz example and the STFT's cycles/sample conversion. The README's ambiguous
  “relative to Nyquist” phrase is not evidence for doubling this value.
- Equal input/output processing, bounded drain, input/control lag and native
  offset match the pinned streaming API and retained complete-clock/delivery
  evidence. All original source/control/hash, null and fixed-sum checks pass.
- All Signalsmith interaction compile commands attest the approved Accelerate
  backend. No backend substitution or upstream modification is justified.

Pinned sources are retained under `build/interaction-release/engines/_deps/`:
stretch `a670068d9aeb64913331d5cc29337b19a457a7df` and linear
`de55e6a50ffcf6f8f43f649692d94691c7025151`. The audit report hashes the inspected
files and verifies relevant wrapper/driver sources against original A2 provenance.

## Why not blindly enlarge the window?

The native engine estimates spectral peak positions from energy centroids
(`findPeaks()`), then interpolates frequency offsets (`updateOutputMap()`). This
is a plausible source of numerical bias at low frequencies, **not an established
root cause or evidence that a particular replacement setting fixes it**. Correct
requested ratios do not guarantee exact output frequency in this algorithm.

Window shape itself depends on block/hop ratio (`setInterval()` selects Kaiser
bandwidth), and FFT sizing includes padding/fast-size rounding. A larger block
with a smaller hop cannot simply be asserted to improve the relevant resolution.
No setting was selected or rendered to try to turn this hypothesis into a pass.

For an even block B, quantum Q, tracker reserve A and split computation disabled,
the current scheduler's full-packet delay bound is **A + B + Q − 1** samples:
packet source `j*Q-B` becomes available at wall `A+(j+1)*Q-1`. This includes
quantum batching, not just the native engine's advertised latency.

| Rate | Tracker A | Original 2048/512 bound | Unselected 3072/512 bound | 100 ms budget |
| --- | ---: | ---: | ---: | ---: |
| 44.1 kHz | 1001 | 3560 | **4584 (too late)** | 4410 |
| 48 kHz | 1045 | 3604 | 4628 | 4800 |

These are static sample-clock bounds, not new callback/host measurements. The
aligned lead/PDC declaration remains exactly 4410/4800 samples. A block of 3072
with a smaller hop is not ruled out by this table, but has no demonstrated pitch
fix. The library's default 120 ms block already exceeds the ceiling; its cheaper
100 ms block consumes it before tracking/batching. Both preset hops also exceed
the current 512-sample processing capacity. Neither is a drop-in solution.

## Evidence and limits

- Audit: `build/studio-wrapper-audit/20261024T224141Z-c4899af9/report.json`
- SHA-256: `3a31cc320963d8715cf4685d38d1936ee4c877db7d01803e7e94646b249a35fe`
- Both A1/A2 artifact manifests were reverified unchanged. The calibrated driver
  and meter remain unchanged; no original grades were recalculated or relaxed.
- Original A2 still fails 34/72 cases, the same 17 conditions per mode. Retained
  simple-tone spectral detuning is not explained away as tracker error; complex
  output measurement limitations remain disclosed.
- No private audio payload reads, playback, new audio measurements, engine runs,
  installs, spending, source-support changes or commit/merge/push occurred.
- This audit is self-reviewed, not an independent review of the completion code.
  No new DSP implementation exists to qualify; prior 186-test qualification stands
  for its original source snapshot, not a claim that the DSP experiment passed.
- After documentation updates, all **186 Python tests passed again** and
  `git diff --check` passed. A source-fingerprint check confirms only documentation
  differs from the original qualified code snapshot. Unit-test listening/export
  fixtures run in temporary roots, not against the private recording packages.
