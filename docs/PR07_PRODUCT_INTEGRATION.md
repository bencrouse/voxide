# PR07 — product processor, controls, automation and state

Branch: `pr-07-product-integration`, based on `fb233d8`.

## Authority and scope

The user reports the evaluation AU's manual Logic/listening checks work, including
the discussed timing, loop/seek and recall behavior. No settings, numerical PDC
measurements, source metadata or formal grading report were supplied; none are
invented. These manual checks are accepted without demanding another audition.
The user then explicitly authorized completing PR07 on a branch **while deferring
formal measured qualification and retaining all failures/accuracy requirements**.
See [the decision](DECISIONS.md#pr07-sequencing-approval-and-manual-logic-acceptance-2026-10-25).

PR07 implementation completion is not completed PR06A/PR06B formal qualification,
a release/distribution license decision, or automatic merge/installation/host work.
No engine/preset shopping, new dependency, research retry or private render occurs.

## Product contract

- Preserve product identity: `com.voxide.audio.voxide`, `aumf / Vx00 / Vxid`.
  Local development version is **0.2.0**, so explicit installer/auval version
  checks can detect a stale 0.1.0 shell. The evaluation component remains unchanged.
- Sole native backend: existing pinned Rubber Band R3 short, preserved formants,
  native consonants, pitch-high-consistency, native internal threading disabled.
  Source is prepared offline from the already-pinned archive; no evaluator,
  Signalsmith alternative, or test allocator enters normal AU linkage.
- `Source/Studio/` implements only studio scale/native scheduling, derived from
  the reviewed evaluation path. A separate test executable compares the production
  stream against preserved evaluation code; that reference code is not AU-linked.
- Three worker-owned voices, inclusive **±12 semitones**. Preserve source bends;
  no lead tuning, key detection, automatic range folding or limiting. Out-of-range
  and uncertain targets fade inactive under existing policy. E2–C6 and both
  44.1/48 kHz requirements remain; functional tests are not full-support grades.
- Fixed **4410/4800 samples (100 ms)**, reported to the host. Selected input
  channel 1 is duplicated to stereo; explicit main/sidechain selection, no silent
  sidechain fallback or stereo downmix. Main and sidechain accept mono/stereo.
- Original is unchanged except declared alignment and original-level gain. Each
  harmony retains fixed one-third mix gain, plus its own enable and trim. All
  levels are −60 to 0 dB; −60 is explicitly **Off**. New sessions default to
  original unity and all three voices on at 0 dB trim. Provide input headroom.
- Level/enables are **output-time**, amplitude-ramped over up to 10 ms. Key,
  scale/custom classes, degree and octave controls are **source-time**, audible
  ~100 ms later. Simultaneous changes are not promised to affect one source frame.
- Native failures, delivery starvation/overflow and invalid mixes visibly latch
  harmonies off; finite original continues at declared gain. Double wet/mix
  arithmetic prevents intermediate overflow; unrepresentable final mix faults,
  not clips/normalizes. Nonfinite source is replaced by zero and diagnosed.
- Prebuilt spare graphs and off-render reclamation; no native construction,
  destruction, waits, file I/O or application mutex on the render path. Fast
  repeated resets may exhaust the spare and temporarily mute harmonies visibly.
  Host prepare/release/destruction require render stopped/joined. Pinned JUCE's
  wrapper callback lock remains; **whole-AU lock freedom is not qualified**.
- Manual restart/recall and ordinary AU bypass preserve queued original audio.
  Bypass emits unity aligned original. Observed source changes, seek/loop,
  stop/resume, offline transition or explicit non-bypass host reset clear history.
  A reset coinciding with bypass is treated as bypass unless observed transport
  proves a discontinuity. Unknown/unreported host moves cannot be inferred.
- **Fast offline bounce unsupported:** aligned original only, explicit warning.
  Unsupported rates similarly produce original only. Retained absolute-MIDI mode
  is also explicitly original-only; it is not an exposed ready synthesis feature.
  The editor offers a return-to-scale action for restored legacy MIDI sessions.

## Frozen host/state compatibility

The first **23 parameter IDs, order, version hints, ranges, choices and defaults**
remain unchanged. This includes `sourceBus` (hint 1), and hint-2 `harmonyMode`,
`scaleRoot`, `scaleSet`, `pitchTracker`, `customPc0..11`, and interleaved
`voiceDegree1/voiceOctave1` through `voiceDegree3/voiceOctave3`.
Legacy degree −11…11 and octave −2…2 ranges remain; unsupported resulting shifts
mute rather than reinterpret stored values. All 41 built-in 12-TET sets and custom
pitch classes retain their meaning. Custom classes and legacy mode/tracker choices
remain host-automatable/persistent but are not expanded into the minimal editor;
custom sets can be edited through retained host parameters. Multi-candidate YIN
remains the default; the legacy tracker parameter still selects its stated variant.

Append only these hint-3 IDs, in this order:

| ID | Type/range | Default |
| --- | --- | --- |
| `voiceEnabled1` | bool | true |
| `voiceLevel1` | dB −60…0, floor Off | 0 |
| `voiceEnabled2` | bool | true |
| `voiceLevel2` | dB −60…0, floor Off | 0 |
| `voiceEnabled3` | bool | true |
| `voiceLevel3` | dB −60…0, floor Off | 0 |
| `originalLevel` | dB −60…0, floor Off | 0 |

State: NUL-terminated `voxide-studio-v4`, then exactly **30 little-endian normalized
float32 values**, in host parameter order. Validate exact length/identity and every
finite [0,1] value **before** applying anything. Persist musical/routing/mixer
settings, not held notes, worker objects, audio history or faults.

Accept `voxide-tracking-v3`'s original 23 values, `voxide-shell-v2`'s source byte,
and `voxide-shell-v1`. **All legacy migrations leave new harmonies disabled**
because those sessions were dry-only; original remains unity, routing and original
musical values retain their defined meanings. New 100 ms alignment is declared
for PDC rather than silently pretending the old zero-latency shell remains.
Evaluation-AU state is rejected, never silently reinterpreted.

State serialization/recall use a non-render mutex. Recall marks an atomic
generation odd while applying parameters, even when committed. The renderer
performs one bounded read and keeps its previous complete snapshot if recall
overlaps; it never locks, spins, or applies a partial transaction. Normal host/UI
parameter gestures use JUCE attachments and host notifications. Automation is
callback-granular; sample-accurate sub-block automation is not promised. Recall
concurrent with automation follows host callback ordering/last-writer behavior;
it is not an atomic transaction spanning arbitrary independent automation writers.

## Native editor and validation

Minimal native JUCE controls: explicit key/scale and source, three degree/octave/
enable/level rows, original level, modest input/pitch/active snapshots and recovery.
Keyboard-focusable controls; editor itself does not take host keyboard focus.
Supported editor sizes: **720×600 to 1000×760**. Attachments update on automation/
recall and detach on editor destruction; opening/closing does not write stale state.
No presets, MIDI keyboard workflow, ornamentation, logs or file work in rendering.

Focused tests include legacy tracking/diagnostic behavior (adapted to delayed
original), all migration formats, malformed/truncated state, source/layout/block
handling, three identifiable fake contributions and missing-voice controls,
per-voice/original mixing, ±12 boundaries/out-of-range muting, native/nonfinite/
overflow dry fallback, production/evaluation reference agreement, and exact built
uninstalled AU routing/latency/bypass/transport/recall. Offscreen native editor
snapshots/gestures, UI-vs-headless audio agreement, reopen/recall and concurrent
automation/recall/render are tested without opening a window or audio device.

Build offline, without installation:

```sh
cmake -S . -B build/pr-07-release -DCMAKE_BUILD_TYPE=Release -DVOXIDE_OFFLINE=ON
cmake --build build/pr-07-release --parallel 6
ctest --test-dir build/pr-07-release --output-on-failure
```

`make reload-au` now builds/installs **this product AU**, not Studio Eval. It remains
an explicitly user-invoked install/sign/auval operation, not part of branch work.

## Completed implementation validation

**Implementation complete on its branch, not merged/installed.**

- Debug and Release: **8/8 CTest checks each**, including **209 Python unit tests**
  per tooling run. DSP, product, native UI, fake and paced native reference
  agreement, exact built AU and signed bundle guards pass.
- ASan and TSan: **4/4 focused checks each** (DSP, fake-engine product, native UI/
  concurrency, fake reference). ASan uses `detect_leaks=0`, so process-wide leak
  freedom is not claimed; explicit fake-native lifetime/ownership assertions remain enabled. Sanitized
  checks are not native real-time or whole-AU lock-freedom evidence.
- Exact uninstalled AU: 96 routing cases, 35,136 blocks, 100 ms property/sample
  alignment, warm/cold bypass transitions, stopped-to-forward-resume history
  clearing and fresh-instance state. MIDI API traffic is exercised; this is not
  an assertion of observed host MIDI-offset delivery or Logic PDC.
- Native stream comparison is aggregate functional reference agreement at both
  rates, not calibrated musical accuracy or each native voice's pitch proof.
- Signed arm64 AU 0.2.0 has only system dynamic dependencies and no static interpose,
  evaluation/Signalsmith or allocator-audit symbols. Historical evaluators,
  frozen meters/pins and both evaluation-AU artifact manifests remain unchanged.

Logs: `build/pr-07-validation/final-003/`.
Signed component, source snapshot, logs, native UI images and hash manifest:
`build/pr-07-artifacts/ready-20261025-01/`.
[Closeout and self-review](evidence/pr-07/implementation-001.md).

## Boundaries retained

The user-reported Logic acceptance belongs to the evaluation AU, not a fabricated
installation/test of this new product binary. PR08 is the next coordinated product
Logic session. Formal measured pitch/full-support, expressive challenge c,
references/listening, native scheduling/stress, licensing and explicit qualified
studio go remain deferred/open. Signalsmith output-pitch failures, rejected Rubber
Band preparation and original worker startup timing miss remain unchanged. New
functional comparisons do not retry or regrade those consumed experiments.
