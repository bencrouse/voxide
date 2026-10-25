# Evaluation-AU independent-review fixes — 001

Follow-up to [the original independent review](review-001.md) of
`8f3a982..358b0fb`. Runtime changes are confined to the evaluation AU; product
source, frozen meters/contracts and historical experiment outcomes stay unchanged.

## Fixes and regression scope

- **R1:** separate manual/state harmony requests from host resets. Manual recovery
  and recall retain lead history. A reset accompanying an ordinary bypass
  transition retains dry history; an observed source discontinuity overrides that
  exception. A host reset without bypass clears history. Fake-engine contracts
  exercise manual restart/recall and reset-plus-bypass with exact delayed lead at
  both rates/variable partitions. The exact uninstalled AU harness toggles the
  bypass property four times while checking impulse plus continuous delayed input.
- **R2:** average finite voices in double, validate wet and final lead/wet mix for
  finite float representability. A failed result latches an explicit session fault
  and returns aligned finite lead; no clipping/limiting/normalization. Fake engines
  return individually finite ~0.9 × float maximum samples: safe averaging, zero wet,
  and final output overflow with continued bit-exact dry fallback are covered.
- **R3:** stop and resume delimit streams; even same-position resume discards
  stopped callbacks. Tests feed a distinguishable stopped tone at fixed position,
  resume both there and forward, require a pristine graph and zero stale lead/wet.
  Unknown-position and backward-seek checks remain.
- **R4:** three fixed, distinct fake-engine output markers establish exact
  independently identifiable contributions. Three negative controls each silence
  one engine while all control bits remain active; the missing contribution is
  measured and cannot meet the all-voices reference. Native smoke establishes
  aggregate audibility/control activation only, **not each native voice's sound**.
- **R5:** malformed-state payload changes earlier valid key/scale/enable values
  before corrupting its final field. Installed state must remain byte-identical.
  Production all-fields-first validation remains unchanged.
- **Additional:** output-time enable/trim versus source-time key/scale is explicit;
  bundle verification rejects Mach-O `__interpose` sections, including with only
  system dynamic dependencies. Tests cover `__DATA` and `__DATA_CONST` placements.

## Scope boundaries

Pinned JUCE wrapper `getCallbackLock()` remains an unqualified integration risk;
processor allocation checks are not a claim of whole-AU lock freedom. No changes
to pinned upstream code or qualification requirements are made. A host reset
coinciding with a bypass transition is treated as bypass unless host transport
information independently reveals a discontinuity. Unreported transport changes
cannot be inferred. These are explicit prototype limits, not observed Logic results.

No installation, Logic/device access, automatic playback, private recording read/
render, engine sweep, consumed research rerun, merge or push is part of these fixes.
Original artifact `ready-20261025-01` and original failure reports stay preserved.

## Executed validation

- Five Release CTest checks pass: processor, audited worker, aggregate native-tone
  audibility (two rates), exact uninstalled AU bypass/lead/latency and bundle guards.
- Both fake-engine processor/worker contracts pass under ASan and TSan.
- Python suite: **205 tests pass**. Its private-workflow unit cases use temporary
  synthetic fixtures; they do not replay or inspect authorized/private recordings.
- Logs: `build/pr-06b-review-fixes/20261025-01/` (build logs, CTest output and full
  `LastTest.log` for each profile, plus Python output).
- New signed delivery, source snapshot and hash manifest:
  `build/pr-06b-artifacts/ready-20261025-02/`. Original delivery remains unchanged.

These are implementation regressions, not retries/regrades of A1/A2, allocation
diagnosis or worker-feasibility experiments. They are not formal pitch, individual
native-voice, actual Logic/PDC or whole-wrapper lock-freedom qualification.

## Independent fix verification

The same reviewer/session in `wE:p4` re-read the complete diff against `358b0fb`
without editing or executing anything. **R1–R5 were all judged addressed at source
level; no remaining verified runtime/ownership regression was found.** Execution
results above are the parent's, not an independent test run.

The follow-up identified one P3 documentation ambiguity: the newly expanded
validation scope could be mistaken as covered by original pre-fix artifacts.
The documentation now explicitly labels the `358b0fb` validation as historical,
retains its links, and separately identifies review-fixed tests/artifact `-02`.
The same reviewer then re-read only those documentation changes and explicitly
confirmed the P3 ambiguity resolved; no additional code/artifact/test inspection
was claimed for that final documentation-only confirmation.
Optional extra stop/seek-plus-bypass assertions were suggested; current code handles
those cases, but no additional claim of observed Logic behavior is made.

This verification is scoped code review, not formal qualification or authorization
to merge/push/install.
