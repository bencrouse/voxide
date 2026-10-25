# PR07 independent code review — original findings

Reviewed `fb233d8..330fe8fb8c9f5d30670b3ab3a8ce5c3e5874e61e` (all 29 files),
relevant DSP/reference/JUCE source and permitted existing validation logs.
Reviewer: separate OpenCode `pr07-review`, Herdr bottom-right `wE:p4`, session
`ses_e8b3243afffeA6umXlJGjPpbpt`. Read-only source review: no edits, test/build/
native experiment execution, private recording access, delegation or host/device
operations. Existing results were inspected, not independently reproduced.

## Original actionable findings (locations at 330fe8f)

1. **R1 / P2 — preparation can seed rendering with partial recall.**
   `Source/PluginProcessor.cpp:67–68`: preparation calls `captureSettings()` rather
   than transaction-aware snapshot acquisition. Concurrent stopped preparation
   and paused recall can seed routing/configuration/gains from mixed parameters,
   even an odd generation. Serialize off-render acquisition or initialize from
   a complete committed snapshot; keep rendering nonblocking. Regress a paused
   recall overlapping preparation and subsequent rendering.
2. **R2 / P2 — reentrant state callbacks defeat transaction isolation.**
   `Source/PluginProcessor.cpp:399–407,423–427`, `PluginProcessor.h:67`: synchronous
   notifications under a recursive mutex allow a listener to save partially
   applied parameters or recursively restore, exposing an even generation during
   partial application and leaving hybrid final state. Define bounded reentrancy,
   publish complete states and regress recursive save/restore/render callbacks.
   Reachability follows JUCE inline listeners, not an observed Logic incident.
3. **R3 / P2 — recovery button cannot recover setup/rebuild failures.**
   `Source/PluginProcessor.cpp:73–74,246–247`, `Source/Studio/Session.cpp:167–170`:
   failed initial construction leaves a null session which render never recreates;
   failed spare construction permanently latches `buildFailed`. A transient
   failure cannot recover via the offered restart. Route explicit retries to
   bounded off-render construction; clearly distinguish initialization failures
   requiring host re-preparation. Regress fail-once initial and spare factories,
   restored harmony processing and preserved queued original audio.

## Additional test gaps

- Restore removed `voxide-shell-v1` migration regression; implementation accepts
  it but the claimed all-format coverage did not include v1.
- UI concurrency test checked finite output, allowing failed/preparing harmonies
  throughout. Require eventual healthy audible processing and graph handoffs.

No additional verified SPSC/availability or graph-reclamation defect was found.
No merge or qualification approval was given. Deferred formal accuracy/support,
challenge c, native scheduling/stress, licensing and wrapper callback-lock gates
are not new findings, are not regraded, and require no repeated manual audition
as part of this review. Original findings remain preserved separately from fixes.
