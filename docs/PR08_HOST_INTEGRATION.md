# PR08 — product host, compensation, recall and bounce implementation

Branch: `pr-08-host-bounce-integration`, based on merged PR07 `f36e5d8`.

## Scope and authority

The user requested PR08 implementation to completion on a branch. This authorizes
code, synthetic tests and a reproducible handoff, not automatic installation,
Logic/device operation, playback, private-recording reads or another corpus sweep.
The prior evaluation-AU manual acceptance remains accepted; it is not fabricated
as testing of this new product binary. The PR07 measured-qualification deferral
and all old failed experiments remain unchanged.

**Engineering implementation and actual host acceptance are distinct.** This
branch can complete code and automated tests without operating Logic. The plan's
actual installed/Logic/recorded-vocal gates remain pending until the coordinated
session occurs. No generated project file, script or native API report substitutes
for opening/closing/reopening Logic, measured PDC, or a recorded-vocal audition.

## Product changes

- Product version **0.3.0**, same `com.voxide.audio.voxide / aumf Vx00 Vxid` identity,
  same 30 host IDs/ranges/defaults/version hints and exact v4 state bytes/migrations.
  The separately identified evaluation AU and old artifacts are unchanged.
- **Actual offline harmony bounce**, using the same pinned Rubber Band R3 short
  worker engines, 128-sample native command stream, preserved-formant/native-
  consonant policy and 100 ms source/output alignment as playback. No alternate
  engine, processing quality, tuning, normalization or range policy is selected.
- Only when the host explicitly marks non-realtime processing does the render
  coordinator wait for native workers after a quantum and drain their same tagged
  output. Realtime callbacks never call this wait path; tests compare per-thread
  wait-call counters before/after every realtime callback and retain allocation
  auditing. Native construction/destruction and metadata ownership stay off render.
- An offline stream/configuration reset can wait for the off-render builder's
  fresh spare rather than accepting a temporarily dry-only bounce. Worker and
  spare waits have five-second bounds; failure latches an explicit fault and
  preserves finite original output. That output is **not a passing harmony bounce**.
  Failed native builds still require explicit recovery; no retry loop is introduced.
- A missing-spare timeout remains latched even if the builder later publishes a
  graph. Ordinary callbacks, recall, transport and mode changes neither re-wait nor
  adopt it; an explicit harmony restart or host re-preparation is required.
- Mode changes are declared stream discontinuities. Supported rates remain
  **44.1/48 kHz**, with **4410/4800 sample latency**; lead is unchanged except declared
  alignment/gain. Exactly three voices and inclusive ±12 requirements remain.
  Bends/expressive challenge c and calibrated musical/full-range gates are not waived.
- Native editor now accurately states playback plus offline bounce. Unsupported
  sample rates and legacy MIDI synthesis still have explicit original-only status;
  live monitoring/MIDI synthesis are not newly qualified.

Offline completion can wait; real-time processing cannot. This is a scheduling
distinction, not a hidden offline-quality mode. Whole-wrapper lock freedom remains
unqualified because pinned JUCE still takes its callback lock. Host prepare/release
require rendering stopped/joined; callback-granular parameter capture, bounded
nested recall and source/output control clocks remain the PR07 contract.

## Automated integration

`BounceTests.cpp` checks both rates, real-time/offline exact agreement through
key/scale/degree/trim edits and recall, variable partitions (1/32/128/257/512/1024),
first nonzero input sample, gaps and a supplied **0.6 s zero tail**. It verifies
finite stereo, native-ready status and aggregate wet output, not just dry parity.
Fake failures reject invalid offline output; rapid offline harmony restarts test
spare synchronization without dropping the queued original.

`HostBounceTests.cpp` loads an **exact component path** and uses process-local
registration only. It does not discover/install system components or open devices.
The harness exports no symbols, isolating its own statically linked JUCE from the
loaded bundle's JUCE storage; otherwise Debug weak-symbol interposition can mix
their distinct empty-string singletons. This is a harness link option, not an
upstream or product patch.
Fourteen controlled cases cover both rates, harmony and unity-original references,
paced playback, fast/variable offline blocks, explicit main/sidechain selection,
key/degree/level changes, warm bypass, first sample and tails. It checks the AU
latency property **and notification**, 30 parameters/legacy source ID, API readback,
stopped sample-rate reconfiguration with fresh latency notifications, and exact
output agreement with a healthy direct production processor. Native
scope is aggregate functional output, not individual-voice pitch qualification.

The pinned JUCE AU API exposes discrete controls as indices and continuous
controls as [0,1], not physical degree/dB values. The harness maps through both
actual AU metadata and the production parameter ranges, then checks readback.
It does not patch the wrapper or change host parameter meanings to fit a test.

Fresh-process checks serialize actual AU ClassInfo, dispose/exit, launch a new
process, restore before initialization and reproduce the same automation/audio.
All 30 expected initial parameter values are read back immediately after restore
and again after initialization, before audio or automation can mask a missing
field. Independent key-default and scale-default negative controls must fail that
comparison, even when the chosen audio would produce the same early shifts.
The coordinator requires distinct PIDs, unchanged state/binary/bundle hashes,
identical finite/nonzero 76,800-frame float output including tail at 48 kHz, and
native success reports with narrowly declared scope. This is fresh **native host**
recall, not a claim that Logic was reopened successfully.

```sh
cmake -S . -B build/pr-08-release -DCMAKE_BUILD_TYPE=Release -DVOXIDE_OFFLINE=ON
cmake --build build/pr-08-release --parallel 6
ctest --test-dir build/pr-08-release --output-on-failure
python3 scripts/host_integration.py check --build-dir build/pr-08-release
```

`make host-check` offers the same build-only workflow using `build/local-release`.
The normal CTest set includes device-free exact-AU and fresh-process checks; no
installed mode, `auval`, Logic, device enumeration, live capture or playback runs.
Fake processor tests cover offline coordination under ASan/TSan; sanitized native
bounces are deliberately not used as realtime/performance evidence.

## Installed and user-session handoff

`make host-kit` creates a new immutable-path kit under ignored `evaluation/pr-08/`:
four low-level synthetic WAVs (both rates, first-sample and pre-roll variants),
their hashes, a copy of [the checklist](PR08_LOGIC_CHECKLIST.md), and an all-pending
worksheet. It reads no user audio and fabricates no `.logicx` project. Actual
recorded-source selection is performed by the user; agent-side access requires a
separate source-bound approval. Old consumed receipts cannot authorize new work.

The optional `installed` command refuses **before installed-file/ledger access**
unless both `--allow-installed-au` and `--allow-auval` are explicitly supplied.
It performs no installation: the existing installer retains ownership/rollback
rules. Installed files must match the requested built component; signing/identity/
version checks and scoped `auval` run, followed by exact-installed-path synthetic
tests. Private installed-session evidence stays under ignored `evaluation/pr-08/`.
Registry identity/version is not cryptographic proof of a cached loaded image;
neither that nor exact-path native loading proves actual Logic behavior.
The installed check holds the installer's shared publication lock from preflight
through final reporting, blocking normal exclusive installer publication. The
requested build's original fingerprint is carried into native testing, checked
around `auval` and every native process, and compared again at completion; it is
never replaced with a later installed-bundle baseline. Noncooperating persistent
file edits fail the boundary checks; no claim of protection against arbitrary
hostile transient filesystem modification or cached registry images is made.

The supported **initial** user settings remain recorded input, PDC All, Low Latency
Mode Off, 128-frame I/O and Small process buffer. The known track-fed/Low Latency
Mode failure remains visible, not regraded. LLM On is a separate restriction test;
a bypassed/silent harmonizer is never a pass. LLM is inactive during bounce. The
unity reference must meet the frozen zero-integer-offset, max 1e-6/RMS 1e-7 null
limits; shifted-vowel phase is not a unity reference. Host chase cannot reconstruct
MIDI events the host never sends; MIDI musical qualification remains deferred.

## Actual host acceptance still required

- Approved installed identity/`auval` and actual Logic route, with no doubled lead.
- Recorded-vocal first syllable/re-acquisition, transformed onset/pitch timing,
  source-automation sync, cycle/seek/stop/resume, and the LLM restriction matrix.
- Real save/close/quit/reopen/duplicate/fresh Logic instance, with project/evidence
  hashes and manual observations rather than a script-generated assertion.
- Actual real-time/offline bounces, matching project range/configuration/format,
  correct duration and tail, and measured differences. Any non-exact differences
  require explanation and independent listening before acceptance.

Those are not marked passed by native tests. PR09 session performance/soak,
formal accuracy/support, challenge c, licensing and final studio go stay open.

## Engineering closeout

Implementation decisions, retained development failures, self-review, validation
and preserved signed delivery are recorded in
[implementation-001](evidence/pr-08/implementation-001.md). No independent PR08
review or actual-host acceptance is implied by that engineering closeout.

The subsequent [independent review](evidence/pr-08/review-001.md) found three P2
timeout/identity/recall-test issues. Their fixes and new regression evidence are
tracked separately in [review-fixes-001](evidence/pr-08/review-fixes-001.md); the
original `6d751fa` artifact and passing evidence remain preserved, not retroactively
promoted as proving the missing guarantees.
