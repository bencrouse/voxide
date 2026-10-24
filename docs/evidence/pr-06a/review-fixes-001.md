# PR06A tooling repairs and review closure — 2026-10-24

**Status: all five [initial review](review-001.md) findings repaired, regressed and
closed by the follow-up read-only reviewer. Stage A remains unexecuted.**
The user requested these fixes; their prior synthetic-only execution approval is
still valid. No private render, source search, playback, installation, Logic/device
operation, final engine selection or product go is inferred.

## Repairs

1. **Receipt replay, including legacy relocation:** new renders consume an exclusive
   canonical proposal-digest/trial claim, before provenance/source access or creating
   a listening run. Receipt/proposal copies share that key; failed attempts remain
   consumed. Legacy consumption is resolved from PR06A claim metadata and its
   approval-bound report, or original hash-bound approval if no report exists.
   Relocating both receipt and proposal cannot hide it. Unresolved historical
   consumption fails closed. No old claim/receipt is rewritten or deleted.
   `studio_playback_export.py` supports a bound canonical claim reference in new
   reports, retaining its original legacy fallback for historical reports.
2. **Proposal containment:** destination and ancestor containment is checked before
   private metadata reads. Input paths no longer resolve away symlinks; output
   cannot follow an `evaluation/` or `evaluation/pr-06a/` symlink into public storage.
3. **Telemetry completeness and causality:** the new `scripts/studio_validation.py`
   independently derives the pinned two-candidate tracker/adapter clocks. It requires
   every per-voice control quantum, startup/negative anchors and tail, complete
   request evidence, valid support/availability/epoch/flags, continuous output
   counters, bounded retrievals, causal production and fixed-deadline delivery.
   Signalsmith requires exactly its quantum packets plus finish packet. Rubber Band
   retains legitimate variable/zero-count trim records and final flush, but cannot
   emit meaningful frames at wall zero or outrun supplied input before finish.
   Callback-return clocks are checked, not silently backdated.
4. **Engineering duration:** the frozen v1 five-second primary and 0.6-second tail
   are derived independently of native/file length declarations. The supplied tail
   is checked for actual zeros; shortened or wrongly split captures are rejected.
5. **Both engineering fixed sums:** direct/aligned sums are checked against their
   corresponding lead plus all three voice channels at 1/3, using the retained
   tolerances. Wrong or zero sums remain failed gates even when repeats agree.

No DSP, engine backend/window, gain, source preparation, preview ceiling, musical
policy or historical protocol changed. The timeline validator intentionally covers
the pinned listening contract (tracked scale, one H-at-zero event, one epoch), not
generic MIDI/oracle workflows. Stage A needs its own explicitly checked event/mode
contract rather than loosening this validator to accept a different timeline.

## Review and automated evidence

The first follow-up review closed containment, duration and summing, but retained
two counterexamples: relocating a legacy proposal and forged aggregate/backdated
packets. Both were repaired with additional negatives before the final review.
The final read-only reviewer found **no remaining actionable bugs** and closed all
five findings for the scoped tooling. This is code-review closure, not human pitch
truth, independent vocal listening or product qualification.

- **45 studio tests** pass, **17 more** than the original review's 28. They include
  relocated legacy receipt/proposal entry-point cases with and without an original
  report, unresolved-claim refusal, failed-attempt consumption, symlink ancestors,
  missing control/output/request records, false clocks/epochs, collapsed/backdated
  packets, production/retrieval bounds, shortened duration, nonzero tail and wrong
  fixed sums. Synthetic fixtures use literal clocks independently of the validator.
- Full product **Debug/Release/ASan/TSan** qualification passes, with **165 Python
  tests** and stable source:
  `build/checks/20261024T194129Z-dff8fbbe/environment.json`.
- Additive final repair evidence:
  `build/studio-review-fixes/20261024T194145Z-23a3bc59/qualification.json`,
  `review-closure.json`, `retained-synthetic-revalidation.json` and the exact
  hash-bound repair implementation/test snapshot under `source-snapshot/`.
- All **48 retained engineering captures** pass the added duration, compact-control
  coverage and fixed-sum checks. All **four retained Release synthetic guard
  timelines** pass complete request/control/output coverage and packet-causality
  checks at both rates, using their recorded mixed callback schedule. No candidate
  DSP was rerun. These are retained synthetic artifacts, not private vocal outputs.
- All **921 original synthetic artifact hashes**, original engineering report and
  artifact manifest verify unchanged. Rubber Band's **24 allocating captures stay
  failed**. No original result is reclassified as a product pass or rewritten.
- Engine DSP sources/binaries are unchanged. Earlier implementation/revalidation
  evidence at `build/studio-review-fixes/20261024T193228Z-3c618c60/` records the
  intermediate repair version; it is not substituted for final qualification.

## Next boundary

Proceed to implement/freeze the **already approved synthetic-only Stage A** meter
calibration/attribution protocol, then execute within its 36 measurement-fixture /
88 native-capture cap and staged stopping rules. This repair task has performed
**zero Stage A executions**, zero new engine renders and no private payload reads.
Private a/c repeatability and host evaluation remain separately approval-gated.
Formal support/pitch/human/host requirements and explicit PR06B go remain open.
Changes are uncommitted; no merge/push or musical correction allowance was spent.
