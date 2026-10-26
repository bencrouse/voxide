# PR08 independent-review fixes — 001

Follow-up to [review-001](review-001.md) of `f36e5d8..6d751fa` on
`pr-08-host-bounce-integration`. The user requested addressing all three findings.
No merge/push/install, installed `auval`, Logic/device/playback operation or private
recording read/render is authorized or performed by this fix work.

## Fixes and regression contract

- **R1:** latch missing-spare wait failure separately from ordinary graph status.
  A subsequent callback, recall, transport/configuration or realtime/offline mode
  change cannot clear it, re-wait or adopt a late graph. Only an explicit harmony
  restart clears this latch; host re-preparation creates a new session as before.
  A controllably blocked fake factory exercises the real five-second timeout,
  asserts one wait across subsequent callbacks/recall/mode changes, rejects late
  spare adoption, and checks explicit recovery yields healthy three-active wet
  output. Original samples remain bit-identical except declared mode-discontinuity
  clearing; the realtime latched callback retains wait/allocation auditing.
- **R2:** hold the installer's shared publication lock from approved installed
  preflight through final reporting. Normal installer publication takes that same
  lock exclusively. Capture the requested build fingerprint once and pass it into
  native execution; check it around `auval` and every native subprocess, plus the
  source build at completion. Tests prove exclusive publication is blocked, a
  mocked replacement during `auval` fails with retained evidence, initial identity
  cannot be rebased, and bundle/helper mutation fails after the first subprocess.
  All installed-operation regressions are mocks using temporary files, not actual
  installed-file/`auval` operations. Registry-cache limitations remain unchanged.
- **R3:** derive the expected complete 30-value initial fixture from production
  defaults plus explicit test overrides. Read actual AU values after ClassInfo
  restoration and after initialization, before any audio/automation. Key-default
  and scale-default negative controls independently fail the comparison. Successful
  native reports must include the new readback/negative-control evidence; old or
  incomplete reports are refused. Exact audio/finite/nonzero/tail checks remain.

No host IDs, ranges/defaults, persisted v4 meaning, engine/profile, latency or
musical/accuracy tolerance changes. The five-second bound is exercised, not
shortened for tests. Formal accuracy, expressive challenge c and actual Logic
qualification remain open; original failures/consumed claims are not regraded.

## Development validation

`build/pr-08-review-fixes/development-001/`: Release processor, exact-AU and fresh-
process checks pass against the first fixes. The timeout regression was then
strengthened with mode-change and realtime no-wait/allocation assertions. Fourteen
Python coordinator tests pass, including all new identity/lock negative cases.

Final validation, independent fix verification and the new preserved signed
delivery are recorded below. Original artifact `ready-20261026-01` and its passing/
failing historical evidence are not modified.

## Independent fix verification

The same `pr08-review` OpenCode agent/session in `wE:p4` independently inspected
the current fix diff and surrounding source/tests. It explicitly judged **R1, R2
and R3 closed at source level**, with no remaining concrete defect in the fixes:

- Latch check precedes fault clearing/exchange/waits; ordinary restart paths
  preserve it and only explicit recovery clears it. The new blocked-builder test
  covers repeated callbacks, recall, mode changes, late publication and wet recovery.
- Shared installer lock spans approved preflight through final reporting. Original
  requested fingerprint survives every stage, with per-process before/after checks;
  identity replacement, helper/bundle mutation and lock contention/release are tested.
- All 30 expected values are read immediately after restore and after initialization
  before audio/automation; independent root-default and scale-default controls each
  require rejection, closing the original audio-equivalence blind spot.

The reviewer ran **no builds/tests** and accessed no artifacts, private evaluation
material, installed components, devices, Logic, private audio or network resources.
Its source-level verdict is not execution or actual-host acceptance. The review
reply remains in the pane under session `ses_e877c962dffeMxuzwIDtcU8iT7`.

## Executed validation and preserved delivery

- `build/pr-08-review-fixes/validation-001/`: **11/11 Release and 11/11 Debug**
  checks, including **223 Python tests** per normal tooling run; **4/4 ASan and
  4/4 TSan** focused checks. Non-documentation source hashes are unchanged across
  configuration/build/execution. No build warnings, sanitizer errors or JUCE
  assertions. The blocked-builder regression exercises the actual timeout in
  every processor profile, not a shortened test-specific deadline.
- Full build-only coordinator passes 14 exact-AU cases and fresh-process recall,
  requiring complete initial-parameter checks and both key/scale negative controls.
  Distinct PIDs reproduce exact finite/nonzero 76,800-frame 48 kHz audio including
  tail; requested and executed bundle fingerprints agree throughout. Original
  96-route/35,136-block aligned-original AU regressions also still pass.
- Sanitizers retain the focused fake-engine contracts, not native realtime or
  whole-AU lock-freedom evidence. ASan uses `detect_leaks=0:halt_on_error=1`, TSan
  `halt_on_error=1`; process-wide leak freedom is not claimed.
- New preserved signed 0.3.0 component/native harness, exact source, dependency/
  build identity, logs, UI captures and SHA-256 manifest:
  `build/pr-08-artifacts/ready-20261026-02/`. BuildInfo honestly embeds
  `6d751fa3556f-dirty`; committed source/binary hashes bind the pre-commit build.
  No post-validation rebuild, re-sign or installation is used for preservation.

## Preservation and boundaries

`build/pr-08-review-fixes/protected-001.json` verifies all **five** prior artifact
manifests (**1,367 entries**) and **260 baseline files** outside the nine existing
paths intentionally changed by these fixes. Dependency pins, historical evaluators/
workers, frozen contracts/meters/fixtures, host parameter/default/state definitions
and the original signed deliveries remain unchanged. New delivery uses the
separate `build/pr-08-artifacts/ready-20261026-02/` path.

Actual installed identity/`auval`, Logic route/PDC/LLM, recorded-vocal articulation/
re-acquisition, true project reopen/duplicate, actual Logic bounce, performance/soak,
formal full-support accuracy, challenge c and licensing remain pending/open. Prior
evaluation-AU manual acceptance stays accepted but is not transferred to this
product binary. No private source or consumed render approval is used by the fixes.
