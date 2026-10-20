# PR 00 independent review and fixes

The user requested a separate agent in a Herdr pane to the right. Reviewer
`voxide-review` runs in `wE:p2` and reviewed the full authored working tree, including
untracked implementation, rather than only the plan diff. It remained read-only;
no builds, installs, devices, downloads, or additional agents were used by it.
The initial verdict was **request changes**, with five actionable findings.

Original locations below refer to the pre-fix working tree over `6e9847a`, not a
separately committed implementation. Review is not evidence of Logic acceptance.

| Finding | Original evidence | Disposition |
| --- | --- | --- |
| P1: automatic main-input fallback fails in AU | `Source/PluginProcessor.cpp:39–45`; pinned JUCE AU wrapper enables every bus, even without a sidechain connection | Accepted. Replaced inferred routing with explicit host-automatable Main input/Sidechain choice, default Main input; selected silence stays silent. Persisted source choice and added a small routing dropdown. No new musical feature. |
| P2: inherited bypass breaks stereo/sidechain behavior | `Source/PluginProcessor.h:11–15`, `.cpp:36–48`; JUCE default bypass retains main input and clears extra output channels | Accepted. Explicit bypass renders the selected dry mono source to both outputs and consumes MIDI, using the same dry path as the current shell. |
| P2: installer ownership race during signing | `scripts/au.py:90–105`; target can appear/change after its first ownership check | Accepted. Revalidate after signing, use Darwin `renamex_np(RENAME_EXCL)` to avoid clobber, verify the moved occupant, and preserve unknown concurrent changes/previous backups during failed restoration. Added signer-hook and late-collision regressions. |
| P2: verified archive does not verify reused extracted source | `cmake/JuceDependency.cmake:28–35`; existing `CMakeLists.txt` caused unchecked reuse | Accepted. Derive a content manifest from canonical verified extraction, validate every reused tree, reject edits/additions/hidden-file changes/symlinks without overwriting them, and serialize initial downloads. Added synthetic archive regressions. |
| P2: standalone lacks microphone privacy description | `CMakeLists.txt:51–65`; generated app plist omitted `NSMicrophoneUsageDescription` | Accepted. Enable JUCE microphone metadata with explicit usage text; inspect generated plist without launching the app or requesting permission. |

Additional implementation hardening: rollback now precedes best-effort pending-file
cleanup, so cleanup failure cannot prevent restoration. Regular presets explicitly
clear the sanitizer cache setting instead of accidentally inheriting an experimental
sanitized configuration.

## Regression evidence

- Before fixes, a new device-free native AU test reproduced the review's main-input
  failure: main source 0.25, disconnected sidechain, normal processing produced 0.0
  on both outputs. Retained log: `build/review-regressions/au-routing-before-fix.log`.
- The native test loads/registers the exact built component inside the test process,
  not the installed component. It checks 96 combinations across two rates, three
  block sizes, both source choices, connected/disconnected and silent/non-silent
  sidechain, and normal/bypass processing. Post-fix Debug test passed.
- Post-fix Debug passed all five CTest suites, including native AU samples and
  generated bundle metadata. The initial 19 Python tooling cases passed, including source
  integrity and installer concurrency/rollback controls.
- Full fresh Debug/Release/sanitizer and installed-AU revalidation passed; exact
  paths and outcomes are in `docs/VALIDATION.md`. The original successes there
  remain historical, not proof
  that these changed paths passed before they were tested.

## Follow-up review

The same independent agent confirmed fixes for routing, bypass, reused JUCE source,
and microphone metadata. It then identified a narrower rollback source race:
another process could replace the public target after the pre-move check, causing
an unverified replacement to enter temporary staging and be deleted by cleanup.

Accepted and fixed: staging now uses explicit `mkdtemp` lifetime outside AU discovery.
Automatic cleanup is disabled before the rollback move and reenabled only after
both identity and content of the moved entry match the verified candidate. A mismatch
or verification failure keeps the uncertain recovery stage and previous backup,
with their paths reported for manual recovery. There is no TemporaryDirectory
finalizer that can subsequently delete the retained entry. The new regression
injects a replacement at exactly that window and checks the retained payload,
original backup, and unchanged ledger. All **20** Python cases pass.

The reviewer then confirmed the last finding is addressed and found no remaining
actionable issue in that specific fix, using file reads only. The right-hand pane
is left available for the user to inspect. One concurrent full build run completed
its commands but was correctly invalidated by the source-stability guard when this
follow-up Python fix changed its input snapshot; it is not counted as a passing run.

Final disposition: all five original findings and the follow-up rollback finding
are addressed. The reviewer confirmed the fixes, and the later stable-input run
passed fresh Debug/Release (5 suites each), ASan/TSan smoke tests (2 each), 20 Python
cases, 96 native AU scenarios per ordinary profile, generated metadata checks, and
explicit signing/validation of the updated installed AU. No Logic/monitoring or
harmonizer-quality qualification is claimed. Implementation and review were performed
on `pr-00-bootstrap`; no remote PR, push, publication, or paid dependency was introduced.
