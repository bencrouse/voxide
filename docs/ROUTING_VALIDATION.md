# PR 01 validation record

Branch: `pr-01-logic-routing`, based on `2b1ffae`. The user approved a native AU
development loop plus a separate human Logic checklist, replacing scripted DAW UI
testing. No engineering timelines or paid dependencies are introduced.

## Current evidence boundaries

| Area | Status |
| --- | --- |
| Diagnostics and deterministic native-host implementation | Implemented |
| Incremental native routing check, Debug (post-review) | Passed; `build/routing-checks/20261020T210159Z-87f6fc2a/report.json` |
| Incremental native routing check, Release (post-review) | Passed; `build/routing-checks/20261020T210303Z-4c8100c5/report.json` |
| Full final Debug/Release/ASan/TSan regression run (post-review) | Passed; `build/checks/20261020T210313Z-fc7eb798/environment.json` |
| Human Logic acceptance | User reports direct-input monitoring with Low Latency Mode off/on and successful save/quit/reopen; track-fed mode failure and remaining detailed checks are documented below |
| Live microphone/input capture or monitoring | User reports direct physical-input selection works, records, and monitors with Low Latency Mode off/on; track-fed live route failed; complete stopped/recording/focus matrix still incomplete |
| Live MIDI controller | Not performed; only a microphone was available; Musical Typing remains a labeled manual alternative |
| Vocal DSP/harmony quality or monitoring latency | Not evaluated by this PR |

The machine-readable native report records 96 routes, 384 time-varying rendered
blocks, 768 MIDI API submissions, host transport-callback use, and AU state restored
into a fresh instance. It explicitly reports that internal MIDI offset delivery was
not observed through the opaque AU. The actual production-processor tests verify
MIDI offsets/held-state behavior and bounded diagnostic publication separately.

## Automated checks

Final post-review qualification command: `python3 scripts/check.py --full --offline`.
All 12 configure/build/test steps exited zero, with a stable source fingerprint:

| Profile | Result |
| --- | --- |
| Debug | 5/5 suites passed: DSP, processor, native AU, tooling, bundle metadata |
| Release | 5/5 suites passed: DSP, processor, native AU, tooling, bundle metadata |
| ASan | 2/2 focused suites passed: DSP and processor; leak detection disabled as documented in `CONTRIBUTING.md` |
| TSan | 2/2 focused suites passed: DSP and processor, including concurrent queue ordering |

Final evidence: `build/checks/20261020T210313Z-fc7eb798/`, preserving per-step logs
and source/binary hashes. Only completion documentation changed afterward; tested
code is unchanged. Earlier pre-review evidence remains at
`build/checks/20261020T173919Z-9a2b0600/` and is not substituted for this final run.

- Queue wrap/overflow and 20,000-record concurrent producer/consumer ordering.
- Note-on/off at sample offsets 7/23 with correct block/frame/epoch context.
- At most 64 inspected MIDI events per callback; overflow makes key state unknown.
- A 4,096-byte SysEx message yields only a three-byte diagnostic prefix plus length.
- Invalid sample offsets are retained, not silently normalized into valid evidence.
- Prepare/reset/stop/seek recovery; negative project positions remain distinguishable
  from missing host timestamps. Diagnostic MIDI never synthesizes audio.
- Selected source/output hash agreement; non-finite input is flagged without
  changing the original dry samples or serializing invalid JSON floating-point data.
- Log header/event/footer serialization, explicit start/stop, loss-baseline handling,
  and refusal to replace an active capture.
- Consumer-side MIDI staging with an interleaved stop before audio publication,
  complete-block ordering, and explicit incomplete-tail reporting.
- Injected short writes at header, audio record and footer: capture fails visibly
  even when the stream's status remains OK. The ordinary writer also checks that
  its header is immediately visible without a JUCE buffer/explicit flush.
- Recovered post-overflow MIDI/audio truncation counters agree. Parser controls
  reject mismatched counters, non-note traffic substituted for notes, unmatched
  note pairs, controller-only offsets and unreleased final diagnostic keys.
- Parser negative controls for incomplete capture, sequence gaps, loss, bad MIDI
  offsets/block associations, unknown note state, bad summaries, missing required
  audio/MIDI, and dry-route mismatch.
- Repeatable generated WAV/MIDI bytes and refusal to overwrite existing test kits.
- Existing dependency-source integrity, installer ownership/rollback, component
  identity, source-state compatibility, and generated privacy metadata regressions.
- Installed `auval` output must report the expected identity/version and success,
  not merely exit zero. A stale registry is not an installed-host acceptance pass.

The source queue is fixed-capacity and its record is trivially copyable; formatting
and disk writes are in the editor consumer, not the render path. This is source
inspection plus the stated tests, not a universal audit of all JUCE/host locks or
allocator calls. Queue overflow during faster-than-real-time rendering is surfaced
as lost evidence rather than blocking audio.

## Private test materials and environment

- `evaluation/pr-01/logic-routing-001/`: generated routing WAV/MIDI and hashes.
  These are synthetic signals, not a recorded vocal or proof of Logic playback.
- `evaluation/pr-01/environment-001.json`: explicit read-only CoreAudio/CoreMIDI
  property capture, no device start/recording/default changes.
- Observed machine: Apple M4 Max, model Mac16,6, 36 GiB RAM, macOS 27.0.1.
  Installed Logic is 12.4 (6707). Native Logic execution/configuration is not qualified.
- Reported CoreAudio defaults were MacBook Pro Microphone and LG UltraFine Display
  Audio, 48 kHz/512 frames. These are not measured delays or Logic settings. The
  initial Logic New Track sheet displayed MacBook Pro Speakers instead, illustrating
  why system-default queries must not be presented as DAW configuration evidence.
- No hostname, serial, device UID, or endpoint unique identifier is queried by the
  environment tool. Raw project/audio/log evidence remains ignored and is not uploaded.

## Abandoned UI attempt — not acceptance evidence

Accessibility was enabled by the user after a failed permission-prompt attempt.
The agent launched Logic, selected Empty Project, and reached its unsaved New Track
sheet. No track was created, no fixture was played, no microphone was captured, no
project was saved/recalled, and Low Latency Mode was not tested. The user then
approved abandoning UI scripting; its experimental script was removed. No UI
automation is left running. The native development loop needs no Accessibility
permission; the user may revoke the earlier grant if desired.

An explicit install placed the early 0.1.0 diagnostic bundle in the user AU directory.
`auval` returned success but reported cached 0.0.1, despite the built/installed plist
reporting 0.1.0. That result is **not** counted as correct new-build discovery.
The output-verification guard now catches this mismatch. There was no global cache
reset, registrar termination, or further scripted Logic operation. Use an explicit
reload and a human Voxide-only rescan before the manual test; confirm routing-003.

## Independent review follow-up

The existing `voxide-review` agent in the right-hand Herdr pane reviewed the full
uncommitted PR 01 diff and new files read-only. Its first turn was interrupted;
it subsequently consolidated these source-supported findings (not runtime repros):

1. **P2 — Stop could split a diagnostic block.** MIDI was written before the audio
   summary arrived. Fixed with bounded consumer-side staging, complete-block writes,
   and a footer count for the discarded incomplete tail; interleaving regression added.
2. **P2 — Buffered short writes could be missed.** Confirmed in pinned JUCE's
   `FileOutputStream::flush()`, which ignores `flushBuffer()`'s false result.
   Fixed by disabling JUCE buffering and checking each write; injected partial
   writes now exercise header/event/footer failures without a status error.
3. **P3 — MIDI truncation counters were always zero.** Confirmed the event was copied
   before its counter was populated. Fixed by populating the prior cumulative count
   before MIDI publication; regression covers a later recovered MIDI block.

Additional implementation-side hardening: arbitrary MIDI traffic previously met
`--require-midi` even when the checklist needed notes. Retain that flag's general
meaning and add `--require-notes`/`--require-released`; the manual guide uses both.
No musical DSP, installation, Logic operation, recording or device changes resulted
from this review. Host acceptance remains pending.

The same reviewer then read the focused fixes and regressions, reporting **no
remaining concrete issues**. That follow-up used file reads only, not test execution;
the post-review qualification above was run separately by the implementing agent.

## User-operated Logic observations — 2026-10-21

The user tested with their own audio/MIDI, not the generated probes. They report
audible sidechain playback with no Side-meter activity, Low Latency Mode silencing
the route, and a successful live-source recording without visible signal in Voxide.
These are partial observations, not a completed checklist or a verified root cause.

The retained private capture is
`evaluation/pr-01/telemetry/4c17869be7df4aaf91b0405e78f5c6ce.jsonl`
(SHA-256 `ac23c3631307caa909c66befbbfdadff2093367068b7994914ae2755c2d82e1f`).
Read-only analysis found:

- Release 0.1.0 / routing-003, approximately 8.85 seconds, 3,319 audio blocks and
  37 MIDI records, with nonzero MIDI offsets and 17 matching note pairs.
- The selected source was Main throughout; Main and output were nonzero in 3,106
  blocks, Side in none. Selected-source and both output hashes matched throughout.
  This establishes delivered bus behavior, not the upstream Logic graph.
- No records dropped during capture, a complete footer, and no discarded tail.
  The 9,143 lifetime drops were already present before this capture.
- Final diagnostic held-key count was two; the strict `--require-released` check
  fails. This may reflect stopping capture before releases and is not yet evidence
  of a stuck-note bug. General audio/MIDI analysis returns `valid_capture`.
- No Low Latency Mode labels or live-test attribution exist in the log. Callbacks
  continued across its short silent interval; the cause of that interval is unknown.

The log file still exists. Its displayed path is owned by the current editor, so
recreating the editor can lose the displayed path without deleting the file. Recover
captures by opening the telemetry directory directly. No source changes, plug-in
installation, Logic automation, or audio-recording access followed this report.

### Follow-up: Low Latency Mode capture and direct physical input

The user repeated the Low Latency Mode test and reported no gray/orange slot
indications. Separately, choosing the physical input directly in Logic's Side Chain
selector worked and recorded as expected. This supports a working direct-input
route, not the previously unsuccessful live audio-track feed or every monitoring
state. In a subsequent comparison the user confirmed audible monitoring through
Voxide with the physical input selected and Low Latency Mode both off and on,
while the Live Source track remained set to No Output. This is user-observed
support for the direct-input route in both modes, not a latency measurement or
proof the track-fed route works. There is no separately attributed capture of
that comparison; no new microphone recording was accessed by the agent.

The new private log is
`evaluation/pr-01/telemetry/d4ef2ab3768b4bf9a823d3e064e143bb.jsonl`
(SHA-256 `ede8712234dcde217b2e086aacb4c45e81fccf9866f5ca382f34907335fcfe84`).
Read-only analysis found 4,523 audio blocks and 49 MIDI records over 12.06 seconds,
with no dropped records or incomplete tail. Main/output were nonzero from about
0.54–2.45 seconds after the first logged callback; Main, Side and output were silent
thereafter through capture end while transport remained playing. Callbacks continued
without a gap over 20 ms, and selected-source/output hashes matched throughout;
the processor reported no bypass. Thus the silence in this capture was already
present at Voxide's input, not a failure to copy nonzero input to output.

The log has no Low Latency Mode markers, so the exact toggle time, upstream cause,
and whether switching the mode off restored the source remain unverified. Its 23
matching note pairs and nonzero MIDI offsets establish activity, but one diagnostic
held key remains at capture end, so release-to-zero is still not qualified.

### Follow-up: project recall

The user reports save/quit/reopen worked for the working direct-input setup.
Record this as user-observed recall success, not a fresh post-recall telemetry
capture or proof that the track-fed Low Latency Mode failure is resolved.

## Completion policy

Engineering completion requires the automated checks and reproducible test kit.
Host acceptance closes only to the extent supported by the user observations and
logs above. The complete focus/monitoring state matrix, single-lead isolation,
release-to-zero and fresh post-recall MIDI telemetry remain unconfirmed; the
track-fed Low Latency Mode failure remains a known route limitation.
Do not advance to a Logic-compatibility claim or close the corresponding plan gates
from the native report. This split is the user-approved workflow, not a claim that
unperformed tests passed.
