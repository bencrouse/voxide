# Incomplete PR06A checkpoint — local review and handoff

The user authorized reviewing and committing the current work as an **incomplete
PR06A checkpoint**, leaving it unmerged, then branching evaluation-AU work from it.
This is not PR06A completion, final engine selection, PR06B/product acceptance,
permission to rerun consumed experiments or permission to install/operate Logic.

## Review scope

Self-review covers the tracked diff and new calibration/native verification,
allocation diagnosis, worker proxy/probe, tests and evidence documents. The worker
ownership/queue/lifecycle paths, synthetic-only source routes, one-use claims,
fixed case caps, unchanged calibrated meter and failure reporting were checked.
This is **not an independent review**; that remains outstanding before merging or
promoting this experimental code as qualified product implementation.

The checkpoint intentionally retains:

- A1's 36 passing calibration fixtures and A2's **34/72 failed pitch cases**;
  no A3 captures or weakened accuracy/support requirements.
- The rejected Signalsmith configuration and rejected Rubber Band preparation,
  including the disclosed diagnostic retrieval-warning artifact and its repair.
- The working normal-case worker prototype: zero callback allocations, identical
  reference audio/controls and 100 ms software alignment in its normal samples.
- The worker screen's **overall failed status**, including the first-callback
  scheduled-finish miss; no epoch shift, retry, regrading or acceptance waiver.
- Research-only lifecycle restrictions: construction/finish/join and offline
  coordination stay outside the callback. Host lifecycle/bounce/PDC, musical
  qualification and final engine/licensing decisions remain unqualified.

Raw synthetic evidence and consumed claims remain under ignored `build/`; private
recordings/approvals/derivatives remain under ignored `evaluation/`. Neither is
included in the commit. Tracked reports retain paths, hashes and interpretation
limits. No new native captures, private reads or playback are part of checkpointing.

## Validation and next task

Checkpoint validation uses the existing Python regression suite and the isolated
Release/ASan/TSan **fake-engine** worker contracts, not another feasibility matrix.
Whitespace, staged file scope, calibrated driver identity and retained evidence
are checked before commit. These checks do not change the failed experiment grades.

**Checkpoint results:** all 199 Python regressions, Release/ASan/TSan fake-engine
worker contracts and the corrected allocation-probe controls pass. No native
experiment is rerun. CTest's build-local `LastTest.log` files now describe these
reruns; their current copies are archived separately for this checkpoint. Earlier
qualification records/digests are historical and are not rewritten to match the
mutable build logs. Original experiment artifact manifests, reports and consumed
claims are checked independently and remain unchanged.
Checkpoint audit and copied test logs:
`build/checkpoint-review/20261025T151516Z-6e002064/report.json`.

Preserve this work on `pr-06a-completion`, then create `evaluation-au-prototype`
from that checkpoint. Freeze further engine research; the next implementation
task is a minimal **evaluation-only** AU using the current worker direction,
user-selected key/scale, three harmonies and unchanged lead. Keep known failures
and qualification gates visible. This checkpoint operation does not build,
install, launch, merge or push that AU.
