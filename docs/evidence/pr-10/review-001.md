# PR10 independent code review — 001

User requested a fresh agent in the bottom-right Herdr pane, followed by repairs.
Reviewer `pr10-reviewer`, pane `wE:p4`, session
`ses_e85ed0517ffe0FKZht0dWItB69`, reviewed `ef80f07..ab4c1ed` read-only.
It ran the 30 new targeted temporary-fixture tests, then additional temporary
fault-injection/command-capture probes. Repository files were unchanged.

## Findings

1. **R1 / P2 — Ctrl-C bypasses uninstall rollback and failure reporting**
   (`scripts/au.py:280` at reviewed revision). The transaction and CLI catch
   `Exception`, not `KeyboardInterrupt`. An interruption between the component
   and receipt moves leaves the component quarantined, an active ownership ledger
   and no failure receipt; the outer report can retain `running`. Handle
   interruption, perform conservative rollback or manual-recovery reporting,
   re-raise and test interruption after each move and during result writing.
2. **R2 / P2 — Reproduction inherits incompatible multi-config generators**
   (`scripts/local_handoff.py:144–150` at reviewed revision). Configure inherits
   `CMAKE_GENERATOR`, but build/test lack configuration selection and assume
   single-config paths. With Xcode or Ninja Multi-Config, `CMAKE_BUILD_TYPE` cannot
   select Release and CTest cannot run the intended configuration. Pin the existing
   Unix Makefiles generator or consistently support multi-config; add regression.

The reviewer reported no other actionable finding in this pass. It performed no
full builds, actual installed-AU/Logic/device/playback operation, private-source
access, download/package install or timing/corpus rerun. Existing build evidence
correctly names `7207af7` and documentation-only changes through `ab4c1ed`.

These findings concern implementation safety/reproducibility, not qualification.
PR08's user pass stands without another worksheet/audition; PR09's original
44.1 kHz variable wet-output failure, unmeasured corrected-v2 screen and all
remaining formal/host/listening/licensing gates are unchanged.

Repairs and follow-up: [review-fixes-001.md](review-fixes-001.md).
