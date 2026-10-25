# Independent evaluation-AU review — 001

2026-10-25; OpenCode reviewer `pr06b-review`, Herdr bottom-right pane `wE:p4`,
session `ses_e8c02db3dffexP5ooVvqdf46fm`. Reviewed all 19 changed files in
`8f3a982..358b0fb` and relevant supporting source. This records the original
source-level findings, not a passing qualification or a retrospective regrade.

The reviewer ran read-only: no edits, tests/builds/native renders, delegation,
private artifact reads, installation, devices, Logic, merge or push.

## Findings (original locations at 358b0fb)

1. **R1 / P2: harmony restart and actual AU bypass interrupt the lead.**
   `EvaluationAU/Processor.cpp:80–83`, `Processor.h:16–17`: every restart clears
   the lead delay. The pinned JUCE AU wrapper also calls `reset()` on enabling
   bypass, so the actual AU drops 100 ms of queued dry audio. Direct bypass
   tests miss that wrapper callback. Distinguish harmony recovery from source
   discontinuities; regress button requests and actual AU bypass transitions.
2. **R2 / P2: finite samples can yield nonfinite host output.**
   `EvaluationAU/Session.cpp:132`, `Processor.cpp:98–99`: float voice accumulation
   can overflow before division (including zero wet times infinity), and finite
   lead plus wet can independently overflow. Use safe accumulation/result checks,
   latch a visible fault and preserve finite lead without adding limiting.
3. **R3 / P2: forward relocation on resume retains stopped-stream history.**
   `EvaluationAU/Processor.cpp:69–75`: forward continuity is checked only when
   both callbacks are playing. Fixed-position stopped callbacks followed by
   forward resume retain old dry/worker history. Define resume policy; test
   distinguishable stopped input followed by relocation and exclude stale output.
4. **R4 / P2: all-three-voice audibility assertion can pass with silent voices.**
   `EvaluationAU/Tests.cpp:174–177`: aggregate difference plus active control bits
   does not establish each voice's contribution. Add identifiable fake voice
   contributions and each-voice-silenced controls; narrow native smoke claims.
5. **R5 / P3: malformed-state regression cannot detect partial application.**
   `EvaluationAU/Tests.cpp:101–105`: earlier valid fields equal installed values.
   Change those fields before corrupting the final field and assert no change.
   Production parser already validates all fields first; this is a test defect.

## Risks and optional improvements

- Enable/trim apply at output time; key/scale are source-time controls, ~100 ms
  apart. Document the intended control-clock contract rather than imply alignment.
- Dynamic dependency checks cannot detect a statically linked allocator interposer.
  Check Mach-O interpose sections too. No actual linkage contamination was found.
- Pinned JUCE takes `getCallbackLock()` around processing. Processor tests do not
  qualify whole-AU lock freedom or lifecycle contention; host qualification stays open.

No verified SPSC/lifetime defect was found under the single-render-owner/stopped
lifecycle contract; no current identity/parser/signature/allocator-linkage defect
was found. Historical musical/timing failures remain unchanged. Fixes and subsequent
verification are recorded separately; these original findings remain preserved.
