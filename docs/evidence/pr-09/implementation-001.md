# PR09 engineering implementation and negative qualification — 001

Branch `pr-09-studio-session-qualification`, based on merged PR08 `8aa76c6`.
Product **0.4.0**; not merged, installed or operated in Logic by the agent.

**Outcome: engineering implementation complete; studio qualification NOT PASSED.**
The controlled screen found two failed variable-block cases. Actual Logic soak,
whole-host timing/allocation observations and independent final listening remain
missing. PR08 user acceptance is retained, not repeated or transferred into a PR09
performance/soak result. See [the operator handoff](../../PR09_STUDIO_SESSION.md).

## Implementation

- Default-off, fixed-capacity 8,192-record metadata queue. Render only uses bounded
  lock-free atomics and preallocated records; it performs no file IO, locks,
  native graph/worker construction/destruction or waits for the collector. A sequentially consistent
  stop handshake accounts for an in-flight callback before finalization.
- An explicitly started off-render writer survives editor close/reopen. UI/writer
  ownership is serialized outside rendering; destruction joins the writer and
  writes aborted rather than manufacturing a completed capture. Exclusive unique
  files use mode 0600 and reject symlink output paths. PCM, MIDI events, source
  hashes/paths and pitch traces are not recorded. The SHA-256 is of the on-disk
  module file at capture start, not cryptographic proof of a cached loaded image.
- Logged timing covers the processor render body only; collection/peak scan,
  wrapper/host work and file IO are outside that interval. Actual Logic allocation
  counts are explicitly unavailable. The logger cannot certify whole-wrapper cost,
  allocation freedom, dropouts, pitch quality or a studio go.
- The separate synthetic native screen wraps full exact-built `AudioUnitRender`
  calls, including input callbacks, with self-tested caller-thread allocation
  interposition. It keeps all startup/outlier records and completed-case sidecars.
  Two fresh processes each cover both rates and 128/512/variable blocks for five
  seconds per point, three enabled changing scale voices, no hidden quality mode.
- Strict metadata analysis requires selected-file consent before path access;
  rejects unknown/duplicate fields, nonfinite values, malformed timelines, module
  mismatch, Debug captures, missing/aborted footers, drops and changed rates.
  Zero-frame control callbacks are retained without inventing an audio deadline.
  Wall time, monotonic span and host-reported non-bypassed playing frames are
  separate; stopped/unknown transport cannot fabricate 30 minutes of playback.
- Existing 30 parameters, v4 state, explicit musical controls, three voices,
  inclusive ±12 requirements, worker/native engine, source clock, original gain/
  alignment and 100 ms latency are unchanged. The frozen PR02 meters/contracts
  are imported, not edited. PR08's active coordinator now checks current 0.4.0;
  archived 0.3.0 artifacts/acceptance remain untouched.

## Executed engineering validation

`build/pr-09-validation/final-001/`: **11/11 Release and 11/11 Debug** CTest checks,
including **238 Python tests** per tooling run; **4/4 ASan and 4/4 TSan** focused
checks. No build warnings, sanitizer errors or JUCE assertions. Non-documentation
source hashes remain unchanged across configuration/build/execution/screening.
ASan uses `detect_leaks=0:halt_on_error=1`, TSan `halt_on_error=1`; process-wide leak
freedom, native real-time performance and whole-AU lock freedom are not claimed
from sanitized fake-engine contracts.

New regressions cover concurrent capture stop/start, overflow/loss, in-flight stop,
aborted destruction, editor lifetime, armed-render allocation/wait auditing,
bit-identical logged/unlogged fake audio and output-only peak measurement with a
hot unselected sidechain. Fifteen new Python tests include failure retention,
consent/path restrictions, misleading elapsed time, unknown/stopped transport,
scope/identity changes, malformed captures and deliberately dry/failed screens.

The exact-built-AU 14 cases and distinct-process ClassInfo/audio recall pass for
0.4.0. Original 96-route/35,136-block aligned-original AU regressions also pass.
`native-metadata-roundtrip-001.json` verifies actual current native synthetic
50-callback metadata parses against the independently hashed test executable,
while correctly refusing any soak/qualification claim.

Development history: `development-001/` failed compilation because a new harness
reference omitted the `voxide::` namespace. `development-002/` passed the initial
four focused checks after correction. Before final validation the collector was
changed from a message timer to an explicitly owned off-render writer to avoid
timer/destruction lifetime races; stop/start, stereo sidechain, audio-invariance
and parser regressions were strengthened. Earlier evidence is retained.

## Single planned controlled screen — failures retained

All builds/tests/profilers/sanitizers launched by this task had finished, followed
by a recorded 30-second cooldown. Other machine activity was not independently
controlled; start load/platform are in the report. No selective timing rerun was
used. Report: `final-001/screen/report.json`; command exit **2** correctly signals
failed measured gates, not a green studio qualification.

| Rate / blocks | P99.9 occupancy, processes 0 / 1 | Outcome |
| --- | --- | --- |
| 44.1 kHz / 128 | 6.0896% / 6.2705% | Both pass this screen only |
| 44.1 kHz / 512 | 4.3185% / 4.1782% | Both pass this screen only |
| 44.1 kHz / variable | 20.5513% / 20.4766% | **Both fail aggregate wet coverage** |
| 48 kHz / 128 | 7.1687% / 6.8062% | Both pass this screen only |
| 48 kHz / 512 | 4.9891% / 4.8320% | Both pass this screen only |
| 48 kHz / variable | 25.6439% / 25.6500% | Both pass this screen only |

Across **11,356 callbacks**, the screen observes **zero caller-thread allocations,
zero CPU-cost overdue callbacks**, finite output and safe peak values. Nevertheless,
both 44.1 kHz variable sequences detect **zero wet samples** in every second using
the declared 1e-4 deviation-from-delayed-lead test; output peak is 0.02. This is
consistent with lead-only fallback and is **not a successful three-voice render**.
Root cause is not established by these aggregate observations. Low CPU occupancy
cannot turn dry output into success; timing distributions from failed/dry cases
are not evidence of three-voice performance. Startup, scheduler lag and all raw records
are retained. The variable sequence remains required/open; it is not silently
removed, declared unsupported, compensated with extra latency or regraded.

## Self-review, preservation and remaining gates

This is author self-review, **not an independent PR09 code review**. Inspected the
single-producer/serialized-consumer handshake, writer lifetime and consent paths;
checked render only touches telemetry, never logger locks/IO; visually inspected
720×600 and 1000×760 native captures without a window/device. The opt-in button
and qualification warning fit. Actual module-file identity limitations remain
explicit. No evaluator, pin, frozen metric or research outcome is altered.

`build/pr-09-validation/protected-001.json` verifies all **six** prior artifact
manifests (**1,696 file entries**) and **258 baseline files** outside the intended
PR09 edit paths. Original PR06B/PR07/PR08 deliveries stay unchanged. During work
the requested branch reference was renamed to main externally while its base
commit remained `8aa76c6`; the requested feature branch was recreated without
discarding source changes. The agent did not push or change main's commit.

A separate signed 0.4.0/source/log/image/hash delivery uses
`build/pr-09-artifacts/ready-20261026-01/`. BuildInfo records `8aa76c67990e-dirty`,
not a fabricated later commit. Exact source
and binary hashes bind that pre-commit build.

Still required: resolve/explain the failed variable-block delivery gate; actual
representative Logic performance/30-minute playback soak and workload/overload/
dropout/editor/multiple-instance observations; appropriate whole-host timing/
allocation evidence; explicit revised PR06B rubric approval and independent final
listening including required c/±12 material. The underlying studio-scope protocol
still marks that rubric/listening pending. Formal pitch/full-support, expressive
challenge c, licensing, whole-wrapper lock freedom and final studio go remain open.
No worksheet is demanded; user observations may be supplied in chat. Private
recordings/consumed approvals were not read, copied, rendered or reopened.

Explicit negative machine-readable outcome:
`build/pr-09-validation/qualification-001.json`. The user-session instruction kit
is `evaluation/pr-09/session-kit-20261026T161427Z-872520bc/`; its actual soak and
independent-listening status remains pending. It contains no recording/project.
