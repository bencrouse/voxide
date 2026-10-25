# PR07 product integration — implementation closeout

Branch `pr-07-product-integration`, base `fb233d8`; explicit sequencing approval
and user-reported evaluation-AU acceptance are recorded in
[the decision](../../DECISIONS.md#pr07-sequencing-approval-and-manual-logic-acceptance-2026-10-25).
Formal measured qualification is **deferred, not passed**. Original failed
experiments and archived evaluation components remain unchanged.

## Delivered scope

- Product AU 0.2.0, same bundle/type/subtype/manufacturer and first 23 host
  parameters. Only the pinned Rubber Band studio worker implementation enters
  normal linkage; no alternative evaluator or allocator interposer.
- Minimal keyboard-accessible native editor, explicit key/scale/source, three
  degree/octave/enable/trim rows, original gain, recovery and modest atomic status.
  Offscreen snapshots inspected at minimum and maximum size; labels, values and
  controls fit. Initial text encoding/formatting was corrected before delivery.
- Versioned v4 state, all-fields-first validation, dry-safe legacy v1/v2/v3
  migration, renderer-side bounded generation snapshots, host-notified attachments
  and concurrent automation/recall/editor-lifecycle contracts.
- Fixed 100 ms aligned selected original, worker-only native ownership,
  off-render spare rebuilding/reclamation, finite mixing and explicit latched
  fault fallback. Bypass, stop/resume, source changes and recall retain the
  documented reset precedence; no source tuning or automatic key detection.
- Real-time-only and MIDI/unsupported-rate limitations are explicit. Custom/legacy
  parameter meanings and ranges remain; unsupported requested shifts mute rather
  than being folded/clamped into accepted musical output.

Full frozen parameter/state/behavior contract: [PR07](../../PR07_PRODUCT_INTEGRATION.md).

## Review scope

Self-review covers native/render ownership and SPSC publication, graph lifetime,
dry routing/aliasing, source/output control clocks, scale/shift policy, state
compatibility and concurrent publication, editor attachment lifetimes, AU identity
and isolation, bundle contents and test claims. No independent PR07 review is
claimed; the independent PR06B findings and their verification remain preserved.

The reference executable alone compiles historical evaluator implementation.
Production target linkage is separate. Fake per-voice markers and each-missing-
voice controls establish independent mixer contributions; native comparison is
aggregate functional output/reference agreement, **not individual native pitch or
full vocal-range accuracy proof**. UI and headless audio use one production
processor and match under gestures, automation and state recall.

## Development corrections preserved

- `development-001` passes the first eight-check Release set.
- `development-002` retains one failing additional boundary assertion: it demanded
  positive-zero bits from a muted negative sample. Muting legitimately yields
  negative zero. The assertion now requires exact **numerical** zero of either
  sign; no DSP/range/accuracy threshold changed. Its other tests pass.
- Initial screenshot writes appended PNG streams to old paths. Snapshot capture
  now uses unique directories, checks writes, and retains previous files. Only
  fresh complete images are used as visual evidence.
- `final-002` retains a failing extra enable-gesture assertion: it requested
  false-to-false after automation stored a valid normalized `.25` (semantic false),
  then incorrectly demanded canonical `0`. The fixture now forces an actual toggle
  before checking readback; production attachment behavior was already correct.
- These are implementation/test corrections, not retries of frozen quality or
  feasibility experiments. No private recording was used.

## Qualification and operations not inferred

All old pitch/timing failures, E2–C6, inclusive ±12, three-voice and required
expressive challenge-c requirements remain. Whole-wrapper lock freedom is still
unqualified because pinned JUCE locks its callback. Host prepare/release require
rendering stopped. Source changes invisible to host transport cannot be inferred.

User-reported Logic acceptance applies to the evaluation AU, not an invented test
of this new product binary. No private source read/render, installation, Logic/
device operation, playback, upstream patch, dependency shopping, spend, upload,
merge or push is part of this branch implementation. Actual product Logic work
belongs to the separately coordinated PR08 session; formal native/musical/license
qualification stays open under the approved sequencing exception.

## Final executed results

`build/pr-07-validation/final-003/` preserves all build/CTest logs and full
`LastTest.log` files. Final production/test sources are stable for these runs:

- **Debug 8/8; Release 8/8**, each including all **209 Python unit tests**.
- **ASan 4/4; TSan 4/4** focused DSP, fake product, native UI/concurrency and fake
  reference contracts. ASan process-wide leak detection is disabled
  (`detect_leaks=0`); explicit fake-native ownership/live-instance
  assertions remain. No sanitizer errors, JUCE assertions or build warnings.
- UI gestures/readback for key/degree/enable/level, byte-identical headless/UI
  render agreement through automation/recall, at least 70 callbacks interleaved
  with 20 editor create/destroy/automation/recall cycles. Native snapshots use
  unique directories at 720×600, 780×620 and 1000×760; minimum/maximum inspected.
- Exact built AU: **96 routes / 35,136 blocks**, both rates, fixed 100 ms
  property/sample alignment, bypass toggles before/after warmup, stopped-to-forward
  resume, seek/reset and fresh-instance state. 70,272 MIDI API calls exercised,
  **not** an observed host MIDI-offset claim.
- Fake and paced native production/evaluation stream comparisons pass at both
  rates through key/scale changes. Native scope is aggregate functionality only.
- Product 0.2.0 arm64/signature/dependencies/static interpose checked; global
  symbols contain no evaluator, Signalsmith or allocator-audit implementation.
- Both `ready-20261025-01`/`-02` evaluation artifacts verify unchanged. Historical
  evaluator/worker code, pins and frozen calibrated meters are unmodified.

Preserved product delivery: `build/pr-07-artifacts/ready-20261025-01/`, including
the signed component, current source snapshot, copied validation logs/images and
file hashes. Original development corrections and failed assertions remain in
their separate logs; they are not hidden by the final passing run.

**Closed scope: branch implementation and focused regression validation.** Formal
qualification remains explicitly deferred, with no automatic merge/push/install.
