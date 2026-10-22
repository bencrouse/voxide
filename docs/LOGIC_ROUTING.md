# PR 01 — native routing checks and human-operated Logic acceptance

## Agreed test strategy

The user approved replacing scripted Logic UI testing with an automated native AU
development loop and a separate manual Logic smoke test. Do not revive AX/keyboard
automation or infer host acceptance from another host. Product scope is unchanged:
this remains a dry lead shell, not a harmonizer yet.

The native loop needs no Accessibility permission. The earlier permission grant
can be revoked by the user if it is no longer wanted.

**Engineering checks can pass while Logic acceptance remains pending.** No native
test proves Logic's routing graph, Low Latency Mode, physical monitoring, project
recall, or audible lead count. Those observations belong to the checklist below.

PR 03 tightens `--require-released`: new logs must contain authoritative musical
key-press and sounding-pitch counters, both zero with known, unbypassed MIDI state.
The old held-key bitset cannot certify repeated-note or sustain releases. Legacy
captures remain usable for routing analysis, not this stronger release gate. A
future new Logic capture requires a separately authorized AU install; native review
and checks do not install anything. See `docs/PR03_CODE_REVIEW.md`.

## Automated loop

```sh
make routing-check                         # incremental Debug; no Logic/device/install
make routing-check PROFILE=release         # same native tests in Release
make check-full                            # ordinary suites plus focused ASan/TSan
```

The routing command builds just the production processor and native AU host targets,
runs processor/AU/tooling tests, and preserves a unique
`build/routing-checks/<run>/report.json` with commands, statuses, source fingerprints,
exact component-binary hash, and the native host's report. Sources changing during
the check invalidate it. Dependency acquisition is offline for this loop; first-time
dependency setup uses the ordinary build instructions.

The native host registers the **exact built AU in its own process**, not the cached
installed component. It uses deterministic, time-varying input buffers and checks:

- 96 source/sidechain/bypass/rate/block configurations, four renders each.
- Playing, stopped, backward project-time seek, reset/forward seek; the render clock
  remains monotonic, independently of host project time.
- 768 MIDI API submissions at offsets 7 and 23 without altering the dry output.
- Parameter ID `449045605` and saved AU ClassInfo restored into a new instance,
  surviving initialization and reset.

The AU host observes transport-callback use and output samples. It does **not**
inspect the AU's private MIDI telemetry, so its report explicitly sets
`midi_offset_delivery_observed: false`. Separate tests of the actual production
processor assert offsets 7/23, note-on/off tracking, stop/reset recovery, bounded
64-event MIDI scans, overflow indication, and 20,000-record SPSC ordering under
concurrent producer/consumer threads. These tests also run under ASan/TSan; they
do not certify every framework callback as lock/allocation-free.

## Diagnostics contract

Expected current build: **0.1.0 / routing-003**. Preserve the existing component and
`sourceBus` parameter identities. The editor shows a new per-instance UUID, source
meters, callback epoch/frame/host time, MIDI prefixes and sample offsets, held-key
diagnostics, and queue loss. A callback older than 0.5 seconds is labeled stale,
not presented as a current observation. Held keys are not sounding harmony voices.

- The render producer only publishes fixed-size POD records to a 2,048-entry SPSC
  queue; it never opens/writes files or prints diagnostic text.
- Source/output peaks and word-FNV hashes summarize samples, not retain PCM. Hash
  equality checks the selected dry copy, not the whole Logic output mix.
- MIDI inspection is limited to 64 events per callback and three bytes per record.
  Oversized messages retain their original length; no SysEx payload is allocated
  or copied in the diagnostic path. Truncation makes held-key state unknown until
  stop/seek/reset recovery, rather than claiming a reliable zero count.
- Queue overflow drops new records without waiting. Log analysis rejects loss or
  sequence gaps; offline/faster-than-real-time rendering can intentionally exceed
  the GUI consumer's capacity and is not a valid live diagnostic capture.
- **Start diagnostic log** is opt-in and writes local JSONL metadata to ignored
  `evaluation/pr-01/telemetry/`. It does not record microphone PCM. **Stop diagnostic
  log**, or closing the editor, ends capture. Logging is not persisted in project
  state and never resumes automatically on recall.
- Only the editor/message thread consumes records and formats/writes JSON. No
  competing consumers should drain this queue. Instance UUIDs are not persisted;
  a fresh processor receives a new UUID, preventing an old session's identity from
  being mistaken for the newly opened project.
- The consumer buffers at most 64 MIDI records until their audio summary arrives.
  Stopping mid-block discards only that incomplete tail and reports its record
  count in the footer/analysis, rather than writing orphaned MIDI rows. A capture
  with no complete audio block still fails analysis. JSONL writes are unbuffered
  at the JUCE stream layer so short writes fail visibly instead of being lost at
  flush; this does not promise survival of a power loss or filesystem failure.

Logs can still reveal voice activity and MIDI notes: keep them private. No upload,
hostname, device UID, or serial collection is implemented.

## Test materials and evidence

```sh
make routing-fixtures
python3 scripts/routing.py environment --output evaluation/pr-01/environment-new.json
```

Fixture generation creates a **new** ignored directory and refuses overwrites.
It contains an 8-second mono 48 kHz WAV routing probe (two quiet synthetic phrases)
and a 4-second, 120 BPM MIDI region with six note-on/off pairs plus all-notes-off.
These are controlled test signals, **not dry vocal recordings**. `fixtures.json`
records their hashes/timing. Use an existing dry vocal or a separately agreed input
take for actual vocal-source validation; do not fabricate that evidence.

The environment helper queries CoreAudio/CoreMIDI properties without starting an
audio device or creating an endpoint. Its device defaults are **not** Logic's
selected device/buffer configuration, and its reported values are not measured
monitoring latency. It omits device UIDs, hostname, and serial fields.

After a manual diagnostic capture:

```sh
python3 scripts/routing.py analyze /path/to/capture.jsonl --require-audio --require-midi --require-notes --require-offsets --require-released
```

This rejects incomplete/aborted captures, queue loss, sequence gaps, mismatched
MIDI/block timestamps, invalid sample offsets, unknown held state, non-finite
signals, and missing requested activity. `--require-midi` accepts any MIDI traffic;
`--require-notes` additionally requires a matching note-on/off pair (including
zero-velocity note-on as release), so controllers/clock/SysEx cannot substitute for
notes. With both note and offset requirements, a note event must have a nonzero
offset. `--require-released` checks the final diagnostic held-key count is zero.
A `valid_capture` is not Logic acceptance; it does not establish all six probe
pairs arrived or that MIDI and audio overlapped in time. Check the actual events.
For live Musical Typing, omit `--require-offsets` if the host delivers events only
at block boundaries; record that limitation rather than changing the recorded-MIDI
test's requirement. An external MIDI keyboard was not supplied and is not qualified.

## One reusable Logic project — manual checklist

Create and retain this project yourself; no undocumented `.logicx` generator or
automated GUI driver is part of the software checks. Keep raw project/logs under
ignored `evaluation/pr-01/`, never in the public fixture tree.

### Setup

- [ ] Close any loaded Voxide session before explicitly running `make reload-au`.
  The helper now rejects a stale registry version, even if `auval` returns success.
  If needed, use Logic → Settings → Plug-in Manager to reset/rescan **only Voxide**;
  do not delete broad caches or kill the registrar/DAW.
- [ ] In native Logic, create an empty **Voxide Routing Study** project at 48 kHz,
  120 BPM. Record the actual Logic version, audio device, buffer, PDC setting, and
  whether direct monitoring is enabled. Do not change unrelated projects.
- [ ] Add an audio track named **Source**, import `routing-probe.wav` at bar 1, and
  set its output to **No Output**, not Mute. Add a software-instrument track and
  select Voxide from **AU MIDI-controlled Effects** in its instrument slot.
- [ ] Import the MIDI probe onto that instrument track, replacing/removing any
  automatically created synth route in this disposable project. The only audible
  lead path should be Voxide → Stereo Output.
- [ ] Select Source in Logic's plug-in **Side Chain** menu. Check Voxide's meters:
  Logic may deliver this source on main input rather than the auxiliary bus. Choose
  the observed **Vocal source** bus explicitly and record which works. If neither
  meter receives Source, stop and report the route; do not assume native tests proved it.
- [ ] Confirm **0.1.0 / routing-003** and note the instance UUID. Wait for current
  render activity before starting a log. If Logic does not render while stopped,
  that must be labeled stale, not read as current silence.

### Recorded audio + MIDI

- [ ] Start a log, play from before the first note through the probe, then stop
  logging. Analyze it with all five requirement flags above. Verify nonzero input/output,
  note on/off activity at the same instance, within-block offsets, matching dry
  hashes, and a final held-key count of zero.
- [ ] Check for exactly one audible lead. Temporarily lower the Voxide channel
  fader to silence: no other project route should continue playing Source. Restore
  the fader. Record the observation; plug-in-internal hashes cannot prove this.
- [ ] Repeat with a real dry vocal recording if available. Synthetic success alone
  does not establish this vocal-source observation.

### Live MIDI and physical input

- [ ] With Voxide's instrument track focused/record-ready, use Logic's Musical
  Typing to press and release notes while stopped and while playing. Capture a log,
  verify MIDI activity and release to zero held keys. Label this **Musical Typing**,
  not external-controller validation. MIDI produces no harmonies in this build.
- [ ] Coordinate the microphone/input test separately. Use existing wired headphones
  and a safe level; never enable a live mic-to-speaker feedback path. If suitable
  monitoring is unavailable, record with monitoring off and keep the live-monitoring
  gate pending. No purchases are required or authorized.
- [ ] For the agreed live test, route the intended physical input via Source or
  Logic's direct input sidechain selector. Use only one dry monitoring path; turn
  interface direct monitoring off if software-monitoring the same lead. Record the
  exact input, monitoring/record-enable flags and track focus needed for callbacks
  while stopped and during recording. Observe mute/solo behavior explicitly.

  **Observed route:** the user reports direct physical-input selection works,
  whereas the live audio-track feed did not reach Voxide. Start with the direct
  input route for further live testing; do not treat a successful Source recording
  as evidence that its live track feed reaches the plug-in. In the recorded-source
  captures, Logic delivered audio on Voxide's Main bus and left Side silent.
  The user also confirmed direct-input monitoring through Voxide remains audible
  with Low Latency Mode both off and on, with Live Source set to No Output. Prefer
  that observed live route; the track-fed route's mode failure remains separate.

### Low Latency Mode and recall

- [ ] Capture separate labeled logs with Low Latency Mode off/on. Confirm Voxide
  and its source feed remain active, not silently bypassed/disconnected. Document
  any disabled send/route and the configured limit. No monitoring latency is inferred.
- [ ] Stop logging, save the project with the chosen source setting, close/quit
  Logic without affecting other work, then reopen it in a fresh process. Recheck
  source setting, routing, audio and MIDI. The new processor UUID should differ;
  capture a new log instead of reusing old telemetry.

Keep a note for each observation: pass/fail/pending, observer, actual configuration,
project hash or preserved project copy, and relevant log hashes. Only these actual
observations may close the Logic gates. Full monitoring-latency and harmonizer
quality qualification remain later work.
