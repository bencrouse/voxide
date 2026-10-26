# PR09 independent code review — 001

User requested a fresh OpenCode review in the bottom-right Herdr pane. Reviewer
`pr09-review`, pane `wE:p4`, session `ses_e866e3e47ffe4ShHFc8rK4hdWG` independently
reviewed exactly `8aa76c6..4de958d`, including surrounding source/tests/contracts.
This is a parent-authored summary of the returned pane findings.

## Findings

1. **R1 / P2 — Silent output passes the screen's wet-output gate.**
   `Source/Tests/HostBounceTests.cpp:329–331` and
   `scripts/studio_session.py:68–70` at the reviewed commit. All-zero AU output
   differs from the nonzero delayed-lead reference, so almost every sample can
   count as wet; peak zero passes headroom. A successful silent render can thus
   pass all screen gates while losing both lead and harmonies. The prior Python
   dry-output test supplied zero counters directly, rather than testing the native
   counter against silence, and missed this regression.
2. **R2 / P2 — Wet samples can cover the wrong second.**
   `scripts/studio_session.py:61–62`. Assigning a whole callback's aggregate count
   to its starting second credits post-boundary wet samples to the prior second.
   The 44.1 kHz variable callback `[88045,88302)` crosses sample 88200; output wet
   only after that boundary could hide an entirely dry `[44100,88200)` interval.
   The old record has no within-block locations, so per-second coverage cannot be
   reconstructed faithfully from it. Whole-block positive fixtures missed this.
3. **R3 / P2 — Unvalidated header values bypass strict schema/finite checks.**
   `scripts/studio_session.py:122–126`. Revision, instance, module path, OS and CPU
   values were not type/content checked. A nested `module_path: {"pcm": [...]}`
   or `cpu: 1e999` could be accepted; the latter becomes infinity without invoking
   Python's `parse_constant`. Neither is emitted by the declared native v1 logger.
   Tests covered callback fields and literal NaN, not those header-value cases.

The stop/start handshake was judged sound under the documented producer/consumer
contract. These findings do not regrade the disclosed failed variable screen,
missing actual-host/listening qualification, or accepted PR08 user report.

Reviewer executed **no builds, tests or benchmarks**, edited no files, spawned no
additional agents and accessed no private `evaluation/` content or installed/Logic/
device/playback resources. Fix follow-up: [review-fixes-001](review-fixes-001.md).
