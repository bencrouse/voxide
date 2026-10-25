# PR06B — minimal evaluation AU

**Scope:** a local, evaluation-only harmonizer on `pr-06b-evaluation-au`, branched
from incomplete checkpoint `8f3a982`. The user explicitly approved this sequencing
exception on 2026-10-25. **PR06A remains incomplete; PR06B formal qualification and
PR07 product integration are not complete/approved.** No failed historical result
is regraded, discarded or rerun to create this component.

**Implementation closeout:** reviewed, validated and preserved in a local branch
commit at the user's request. [Closeout/handoff](evidence/pr-06b/closeout-001.md).
This closes the prototype implementation task, **not** the formal qualification
gates below; no merge, push or installation is implied.

## What is implemented

- Separate **voxide Studio Eval** AU: `com.voxide.audio.studioeval`,
  `aufx / Vx6b / Vxid`. The existing `voxide` product component, parameter IDs,
  state and source files remain unchanged.
- Explicit key and built-in 12-TET scale selection. Exactly three available voices
  use +2/+4 scale steps and octave-up (third/fifth in seven-note scales); out-of-range/uncertain targets retain
  the existing disable policy. No key detection, lead tuning or MIDI workflow.
- Existing pinned Rubber Band R3 short, preserved formants/native consonants and
  worker-owned processing. No new backend, engine shopping or upstream patches.
- Mono vocal source from **main input channel 1**, duplicated to stereo output.
  Stereo main input is accepted but channel 2 is ignored; no downmix/automatic bus
  fallback or sidechain selector is introduced in this small prototype.
- Lead is unchanged except **4410/4800-sample alignment (100 ms)**. Each harmony
  retains its one-third relative mix gain, with one global harmony trim (−60 to
  0 dB) and enable. Defaults match the prior mix. No normalization/limiter/masking
  effects; provide headroom before the insert to avoid sums above full scale.
- Enable/trim are **output-time mixer controls**, with the existing 10 ms wet-gain
  ramp. Key/scale are **source-time** controls and reach audible output ~100 ms
  later. Simultaneous automation is not promised to affect the same source passage.
- Voice averaging and lead/wet mixing use double intermediates and finite/float-range
  checks. Unrepresentable output latches an explicit harmony fault and falls back
  to finite aligned lead, not clipping, normalization or acceptance of invalid wet.
- Visible ready/preparing/fault/offline/unsupported-rate status, active voice count
  and a manual **Restart harmonies** action. Delivery faults latch harmonies off;
  the aligned lead continues, and the failure is visible rather than accepted.
- A worker failure does not invalidate a finite packet already advertised to its
  consumer. This avoids an exception/allocation race between `available()` and
  `retrieve()`; session health still gates all audible wet output off on failure.
- A pristine spare graph lets ordinary resets/transport jumps swap at callback
  boundaries. Old graphs and worker joins are reclaimed off render. Rapid repeated
  resets can temporarily exhaust the spare and mute harmonies while it is rebuilt;
  loop/first-syllable/reacquisition qualification remains pending.
- Manual harmony restart and parameter-state recall preserve queued lead. Ordinary
  AU bypass transitions (including pinned JUCE's reset callback) preserve it too.
  An explicit host reset without a bypass transition, observed seek/loop, offline
  mode change, stop or resume discards source/worker history. Resume always starts
  a fresh stream, even at the same stopped position; stopped callbacks cannot bleed
  into playback. Without host position/transport information, unreported source
  changes cannot be inferred. A reset coinciding with a bypass change is treated
  as bypass unless an observed transport/source discontinuity overrides it.
- Host prepare/release/destruction must occur with rendering stopped/joined.
  Host/UI reset requests are atomic; only the render owner swaps graphs. Readouts
  are snapshots, not proof that Logic is currently delivering callbacks.
- Separate validated `voxide-studio-eval-v1` parameter state. Malformed/truncated/
  nonfinite state is rejected before applying any values. Full concurrent host
  automation/recall guarantees remain a later qualification gate.

## Explicit prototype limitations

**Real-time playback only, at 44.1/48 kHz.** Fast offline bounce is not implemented:
when the host marks non-realtime rendering, this prototype outputs **delayed lead
only**, displays an explicit warning and does not pretend to have rendered harmonies.
Use neither that output nor an unsupported-rate dry render as passing qualification.
No callback waits are added to make a fast offline render appear successful.

This is not a live-monitoring product: PDC cannot remove 100 ms from physical
monitoring. Actual Logic route, Low Latency Mode, compensation, transport, recall,
bounce and multi-instance/stress behavior remain untested. Basic audible output
is not calibrated pitch/formant/support qualification or independent listening.
Required challenge c and all E2–C6 / inclusive ±12 / three-voice requirements stand.

Start a coordinated audition with 128-frame I/O and a small process buffer. Prior
isolated worker evidence covers 128/512 callbacks; this AU's native functional
checks use 128. Larger host blocks and scheduling combinations are unqualified
and may trigger the visible delivery-fault mute, not an accepted dry-only pass.

The original worker test's startup scheduled-deadline miss remains failed. New
processor/AU functional tests do not repeat or replace that consumed experiment.
The AU deliberately omits the research malloc interposer; tests instrument their
own process, not the plug-in loaded into Logic.

## Build, without installation or host/device operation

```sh
cmake -S EvaluationAU -B build/pr-06b-eval-release -DCMAKE_BUILD_TYPE=Release -DVOXIDE_OFFLINE=ON
cmake --build build/pr-06b-eval-release --target voxide_studio_eval_AU eval_processor_tests eval_worker_contract_tests eval_au_smoke --parallel 6
ctest --test-dir build/pr-06b-eval-release -R '^eval_' --output-on-failure
```

Only existing verified dependency archives are used. The ad-hoc-signed component is:

`build/pr-06b-eval-release/voxide_studio_eval_artefacts/Release/AU/voxide Studio Eval.component`

Builds never copy it to an AU installation directory. **No automatic installation,
`auval` registry scan, Logic launch, playback, audio-device access or private source
render is part of this task.** Installation and the actual Logic audition require
explicit user coordination. JUCE/Rubber Band remain local-only under the existing
license constraints; no distribution/commercial-license claim is made.

## Focused validation

- Headless processor contracts: rates/layouts/variable blocks, exact delayed lead
  and bypass, parameter state, spare-graph resets, offline/unsupported-rate warnings,
  worker ownership, native-error fail-closed behavior and callback allocation checks.
- Fake-engine processor contracts under ASan/TSan; sanitized tests are not native
  realtime performance evidence.
- Two paced, synthetic native-tone **functional audibility** checks at the two
  supported rates. They establish nonzero harmony processing, not pitch accuracy,
  host performance, a new feasibility matrix or permission to replay private audio.
- Exact built, **uninstalled** AU loaded in a device-free, process-local harness:
  component identity/parameters, 100 ms AU latency property and exact delayed dry
  impulse/continuous lead across actual AU bypass-property transitions.
  This is not a Logic/PDC/bounce test or public component registration.
- Bundle metadata/arm64/signature verification and a dependency check rejecting
  non-system/test allocator libraries and static Mach-O interpose sections in the AU.

The pinned JUCE AU wrapper takes `getCallbackLock()` around processing. Direct
processor tests do **not** qualify whole-AU lock freedom or lifecycle contention.

## Initial validation result (358b0fb; preserved)

**Implementation/build complete; focused tests pass.** All five Release checks cover
headless processor and audited worker contracts, native functional audibility at both rates,
direct-built AU impulse/latency smoke, and bundle/signature/dependency validation.
ASan and TSan pass the fake-engine processor contracts, including rapid resets,
worker ownership/reclamation, native-fault muting, and unknown-position/seek
handling, including failure between packet advertisement and retrieval. The Python suite passes **204 tests**. No malloc interposer or other
build-local dynamic library is linked into the actual AU.
An [independent review](evidence/pr-06b/review-001.md) found five actionable
runtime/test issues in `358b0fb`. That original outcome is preserved; subsequent
fix verification does not establish formal musical/Logic qualification.

Build/test logs: `build/pr-06b-validation/delivery-20261025T161139Z/report.json`.
Original preserved component (superseded by the review-fixed artifact below):

`build/pr-06b-artifacts/ready-20261025-01/voxide Studio Eval.component`

Artifact/source hashes and copied validation logs:
`build/pr-06b-artifacts/ready-20261025-01/report.json`.
Earlier intermediate validation records remain historical.
These are functional checks, not a replacement for the failed PR06A screen or
full native performance/pitch qualification. Initial AU-smoke factory lookup and
test-runner wiring errors were fixed; they were implementation regressions, not
retries of a consumed research/quality experiment.

## Review-fixed validation

The [five independent findings](evidence/pr-06b/review-001.md) are addressed in
[the fix record](evidence/pr-06b/review-fixes-001.md). Five Release checks and both
fake-engine contracts under ASan/TSan pass; **205 Python tests pass**. This includes
actual AU bypass transitions, overflow/dry-fallback checks, stopped-stream resume,
identifiable fake voices/negative controls and malformed-state atomicity.
Logs: `build/pr-06b-review-fixes/20261025-01/`.

Review-fixed delivery (separate from the unchanged original):
`build/pr-06b-artifacts/ready-20261025-02/voxide Studio Eval.component`.
Artifact/source hashes and copied validation logs:
`build/pr-06b-artifacts/ready-20261025-02/report.json`.

**Next user-facing step:** coordinate installation of this separate component and
a disposable recorded-vocal Logic audition. Neither has happened automatically.
Actual usable sound, scale behavior, PDC, transport/recall, required challenge c,
independent references/listening and formal studio go still need their approved
evidence. PR06B remains open; this implementation is not a declaration it passed.
