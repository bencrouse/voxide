# PR10 independent-review repairs — 001

Follow-up to [review-001.md](review-001.md). No product C++/DSP, parameters/state,
dependency pins, frozen meters or qualification gates change.

## Repairs and regressions

- **R1:** uninstall catches interruption as well as ordinary exceptions. A move
  attempt is marked before entering the kernel rename, so interruption immediately
  after a successful rename cannot hide it from recovery. Restoration still
  requires verified original identity/bytes/modes and vacant destinations, with
  no deletion/overwrite. A second interruption during rollback is recorded as
  manual recovery when needed. Failure receipts carry the exception type; the
  original interrupt is re-raised. The CLI records `fail`, not `running`.
- **R2:** every reproduction configure explicitly selects `-G "Unix Makefiles"`,
  matching the existing repository presets and single-config artifact/test paths.
  It does not install a generator or change the pinned build toolchain.
- Five new uninstall test methods cover interruption immediately after either
  rename, partial/complete result writing (failure takes precedence), a second
  interruption during rollback, collision preservation and CLI failure reporting.
  One mocked complete four-profile orchestration test covers inherited **Xcode**
  and **Ninja Multi-Config**, checking generator/profile/offline command arguments.
  Its fixture logs/results are synthetic, not real compilation evidence.

Initial targeted validation: **36/36 tests pass** (22 uninstall, 14 handoff).
Complete Python tooling suite: **281/281 pass**, recorded in
`build/pr-10-review-python-001.log`.

## Independent follow-up

The same bottom-right `pr10-reviewer` independently re-read the repairs and ran
the **36 targeted tests** successfully. It explicitly closed **R1 and R2 at
source/test level**, finding no new actionable defect. Its proposed extra
fault-injection probe was interrupted and not executed; no success is claimed
for that optional probe. Closure instead rests on inspected source and the
executed move/result-write/repeated-interruption/collision/CLI regressions.
The reviewer performed no full builds or actual installed operations.

## Preservation and execution

`build/pr-10-review-fixes/protected-001/preservation.json` verifies **ten prior
manifests / 2,805 entries**, including the original PR10 `ready-20261026-01`, and
unchanged protected product/evaluation sources, dependency pins and cache archives.
No actual installed operations, private reads, timing or historical study reruns.
Fresh offline reproduction of the repaired script under inherited
`CMAKE_GENERATOR=Xcode` **passed**:
`build/pr-10-review-fixes/reproduction-001/`. Source checkpoint
`f232d393a11503f82eb8b771fffe4d7b29440c5c`, tree
`bc4cd1ba2ddf40a5b0c0c44d77cc86f20a4c627a`; every actual configure selects
Unix Makefiles, and the original checkout/cache are retained.

- Release and Debug: **11/11 CTest checks each**, including **281 Python tests
  each**. No mocked orchestration result is counted as compilation evidence.
- Focused ASan and TSan: **4/4 each**, with the existing sanitizer options.
- `build/pr-10-review-fixes/host-001/`: exact fresh signed AU passes the 14 native
  functional cases and distinct save/reopen processes with identical generated
  audio/state checks; no installed AU/auval, Logic or private source operation.
- `protected-after-001/preservation.json` confirms all ten previous manifests /
  2,805 entries, pinned archives and protected sources remain unchanged after
  execution. `main` remains `ef80f07`; no merge or push.

Separate review-fixed delivery:
`build/pr-10-artifacts/ready-20261026-02/`. It preserves the exact signed tested
component/native harness, committed build-source/final documentation snapshots,
logs/build metadata, generated host output, audit records and complete pinned
archives, without a post-test rebuild or re-sign. Binary SHA-256:
`33b51208dc8d40933ffd6a3aed82ebaa385a17af5e1663d37647a646145ee40d`.
Changes after the build checkpoint are documentation-only and separately identified.

Both implementation findings are independently closed. Product **0.4.0 remains
not qualified**: the original PR09 44.1 kHz variable-block failure, unmeasured v2
screen and pending actual host/soak/whole-host/listening/full-support/challenge-c/
licensing/final acceptance gates are unchanged. No new audition/worksheet is
required to preserve the user's historical PR08 acceptance.
