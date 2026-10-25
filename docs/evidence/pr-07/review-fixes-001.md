# PR07 independent-review fixes — 001

Follow-up to [the original review](review-001.md) of `fb233d8..330fe8f` on
`pr-07-product-integration`. User explicitly requested implementation of the fixes.
This does not authorize merge/push/install or erase deferred qualification.

## Fixes and regression contract

- **R1:** preparation locks the state mutex only for its off-render settings
  snapshot. It cannot seed the render cache or initial gain ramps from a partial
  transaction. A listener/barrier test pauses recall while another thread prepares,
  checks serialized completion, then checks complete routing/key/scale/gain and
  even generation on rendering. No render mutex/spin/wait is added.
- **R2:** install all validated parameter values quietly while generation is odd,
  then publish even generation **before** any synchronous listener notifications.
  Reentrant saves therefore see a complete state. Reentrant restores coalesce
  last-wins into one deferred recall processed after the outer notification batch.
  Requests made by the deferred batch's own listeners are ignored, explicitly
  bounding recursive notification cycles. The externally requested state and at
  most one deferred state are each complete, never hybrids. Recursive one-shot
  save/restore/render listeners test complete serialized states, even generations,
  complete render snapshots and the defined final deferred state/cycle bound.
- **R3:** preserve a recovery coordinator when native/worker graph setup fails.
  Explicit restart publishes an atomic retry generation; only the off-render
  builder clears the failed-build latch and constructs another graph. Ordinary
  callbacks, transport changes and recall do not repeatedly retry failed builds.
  Initial and spare fail-once factories test latched failure, explicit retry,
  healthy audible harmony recovery and bit-identical queued original through it.
  If the session/coordinator itself cannot initialize, show **Re-prepare required**
  and disable the ineffective restart action instead of suggesting it can recover.
- **Test gaps:** restore direct v1 migration/defaults/dry-safe-voices and truncated
  state assertions. UI concurrency now requires actual graph handoffs and eventual
  ready/three-active/aggregate-wet output after stress, not just finite dry output.

No host IDs, parameter ranges/defaults, persisted v4 bytes or native engine/profile
choices change. The first product artifact and original review/validation outcomes
remain preserved. Native failure injections use fake engines; no private source or
consumed quality/feasibility experiment is rerun.

## Independent fix verification — first follow-up

The same `pr07-review` agent in `wE:p4` re-read the changed source/tests read-only.
R1/R2/R3 were judged fixed at source level, including the declared bounded nested
recall policy; UI concurrency's handoff/healthy-wet assertion was judged closed.
No additional concrete production defect was found. No execution was claimed.

Two P3 test-design findings were retained and corrected separately:

- The first v1 fixture already matched expected migration defaults. It now installs
  distinct nondefault routing/musical/mixer values before **each** valid/truncated
  case: valid v1 must reset them; truncated v1 must retain exact state bytes.
- Counting injected failures did not count unauthorized successful retries. The
  fake factory now counts **every invocation** and asserts unchanged attempts plus
  failed status/latch during ordinary callbacks and recall, before explicit retry.

These strengthen regression detection without changing production behavior or
frozen metric thresholds. Original review and earlier validation logs stay intact.

## Independent verification — final fixture follow-up

The same reviewer re-read the two corrected fixtures and confirmed **both P3 gaps
closed by source inspection**, with no further concrete fixture defect found.
Production code was unchanged since its R1/R2/R3 verification and was not claimed
as re-reviewed during that final test-only check. No execution or artifact/private/
host access was performed by the reviewer. Original three production findings,
both original test gaps and the additional retry-policy assertion finding are now
addressed at source level. This is not formal qualification or merge approval.

## Executed validation and preserved delivery

- `build/pr-07-review-fixes/validation-002/`: **8/8 Debug and 8/8 Release** checks,
  including **209 Python tests** per tooling run; **4/4 ASan and 4/4 TSan** focused
  checks. Build logs and complete CTest logs are preserved; no warnings, sanitizer
  errors or JUCE assertions. ASan uses `detect_leaks=0`, so process-wide leak
  freedom is not claimed; explicit fake-native ownership/lifetime checks remain.
- New tests exercise paused recall/preparation, recursive save/restore/render,
  bounded recall cycles, initial/spare setup failures, no implicit retry attempts,
  explicit recovery with bit-identical original, and eventual healthy wet output.
- Existing native aggregate reference and exact uninstalled AU checks still pass:
  96 routes / 35,136 blocks, 100 ms original alignment, bypass, resume and recall.
  These are functional regressions, not musical/full-support or host qualification.
- New signed product/source/log/image artifact:
  `build/pr-07-artifacts/ready-20261025-02/`. The original product `-01` and both
  archived evaluation artifacts remain unchanged. No artifact is overwritten.

No private recording operation, consumed experiment rerun, installation, Logic/
device operation, playback, merge or push occurs. Formal measured qualification
remains deferred under the user's existing sequencing approval.
