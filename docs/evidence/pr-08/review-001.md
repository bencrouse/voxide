# PR08 independent review — 001

User requested a fresh OpenCode code review in the bottom-right Herdr pane.
Reviewer: `pr08-review`, pane `wE:p4`, session
`ses_e877c962dffeMxuzwIDtcU8iT7` (GPT-6.1 Sol).

Reviewed range: `f36e5d8..6d751fa`, read-only, including surrounding production,
tests and intended contracts. No builds/tests, installed operations, Logic/devices,
playback or private-source access were performed. No files were changed by the
reviewer. This record summarizes the returned pane findings; it is not a claim
that the reviewer authored this document.

## Findings

1. **R1 / P2 — Offline spare timeout does not remain latched.**
   `Source/Studio/Session.cpp:195–212` at the reviewed commit. If the builder takes
   over five seconds after ready-spare exhaustion, failure leaves `active` null.
   The next callback's replacement branch clears the fault, then waits again or
   adopts a late spare without explicit restart. A bounce can lose harmonies for
   a block and later appear healthy; a stalled builder causes repeated waits.
   Existing reset/nonfinite tests do not cover the null-active timeout path.
2. **R2 / P2 — Installed check can accept a different requested-build identity.**
   `scripts/host_integration.py:79–81,100`, interacting with `42–44,64`. A normal
   installer can replace bundle A after preflight, for example during `auval`.
   Native execution then establishes a new baseline B and only checks B stays
   unchanged; the command holds no installer lock and never binds B back to A.
   A same-version/audio-equivalent replacement can pass for the wrong build.
   This is on-disk identity, separate from the documented registry-cache caveat.
3. **R3 / P2 — Recall test can pass missing key/scale restoration.**
   `Source/Tests/HostBounceTests.cpp:114–118,264–271`, automation at `189`. The saved
   F-minor fixture and default C major both command 0/+7/+12 on the initial 220 Hz
   source. At sample 4096 automation overwrites both root and scale. Dropping either
   ClassInfo field can therefore preserve exact complete audio; no restored-value
   readback detects it. This is a test false acceptance, not a demonstrated defect
   in current production restoration.

All three are actionable P2 findings. Existing deferred accuracy/full-support,
challenge c, performance/soak, licensing and whole-wrapper lock-freedom gaps were
not reclassified as introduced regressions or passed gates.

User requested implementing the feedback. Follow-up:
[review-fixes-001](review-fixes-001.md). Original source/evidence/artifact
`build/pr-08-artifacts/ready-20261026-01/` remains preserved unchanged.
