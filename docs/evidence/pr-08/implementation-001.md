# PR08 engineering implementation — 001

Branch: `pr-08-host-bounce-integration`, based on merged PR07 `f36e5d8`.
Product **0.3.0**; no merge, push, installation or Logic operation.

## Implemented contract

Same-engine offline harmony rendering now coordinates completion of the existing
worker commands and waits for an off-render spare after rapid offline resets.
Both waits are bounded and restricted to explicit non-realtime processing. The
100 ms lead/voice alignment, three voices, source-time musical controls, output-time
gain ramps, explicit key/scale, ±12 limits and existing state/parameter meanings
remain unchanged. Failures retain finite original audio but are not successful
harmony bounces. See [the contract](../../PR08_HOST_INTEGRATION.md).

New processor and exact-bundle AU tests compare actual wet output, automation,
partitions, first sample and tails against healthy production references. Native
ClassInfo recall is compared across distinct processes with immutable state,
binary/bundle hashes and exact finite/nonzero audio. These tests do not pretend to
operate Logic or establish musical/full-support qualification.

The coordinator refuses installed-file/`auval` work before access without both
explicit approvals. It never installs or operates Logic. The generated synthetic
kit and [checklist](../../PR08_LOGIC_CHECKLIST.md) retain all actual-host cases as
pending, including recorded-vocal routing/PDC, re-acquisition, real project reopen/
duplicate, Low Latency Mode restrictions and actual host bounces.

## Development corrections retained

- `build/pr-08-validation/development-001/`: new CMake target was not regenerated;
  the attempted build failed before tests. Reconfiguration fixed the setup.
- `development-002/`: AU/reference comparison failed because the new harness sent
  physical degrees/dB to JUCE's normalized/indexed AU parameter API. At 44.1 kHz,
  the diagnostic mismatch began at sample 5690, ended at 48881, had 36,918 differing
  samples and max error 0.0093949. The harness now maps through production ranges
  and actual AU metadata and checks readback. DSP and tolerances were not changed.
- Two initial Python fixtures supplied macOS `/var` temporary paths through a
  symlink; fixtures now canonicalize their roots. Production symlink rejection
  remains strict, with new negative tests for kit roots and native executables.
- `development-003/`: corrected exact-AU and fresh-process tests passed.
  `development-004/`: full Release 11/11 passed before the last two Python symlink
  tests were added; all ten new coordinator tests subsequently passed individually.
- `final-001/`: Release 11/11 passed, but Debug exact-AU and fresh-process cases
  aborted during AU construction. LLDB evidence in `debug-abort-001/` identifies
  an invalid free of JUCE's empty-string storage: the harness executable's exported
  weak symbols interposed its own JUCE on the loaded bundle's separate JUCE copy.
  The harness now links with `-no_exported_symbols` to isolate those copies. This
  changes only the test executable, not the AU, DSP, pinned JUCE or tolerances.
  The failed run and backtrace remain preserved; final validation is a new run.
- Self-review found the installed-operation report marked `auval` executed only
  after success. It now records the attempt before invocation so a failed approved
  operation is not hidden. An eleventh mocked coordinator regression checks this;
  no real installed operation was run. This Python-only change occurred during
  `final-002`, so tooling is revalidated afterward against the final source.

No historical evaluator failure is overwritten or regraded by these corrections.

## Self-review and source boundaries

This is author self-review, **not an independent PR08 review**.

- Inspected worker/spare ownership and offline guards. Worker completion polling
  is called from the graph only when offline; spare polling is under the same
  explicit guard. Worker creation/destruction remains on preparation/builder
  threads, not rendering. Realtime callback wait-call and allocation assertions
  are retained. Whole pinned-JUCE-wrapper lock freedom is still unqualified.
- Inspected fresh-process state/audio and failure-report requirements, installed
  consent-before-access, append-only output destinations and synthetic-only kits.
  Exact process-local registration is not installed-registry or Logic acceptance.
- Visually inspected current offscreen native editor captures at 720×600 and
  1000×760: playback/offline wording and qualification warning remain readable
  without clipping. No window, audio device or playback was opened.
- Verified all four preserved PR06B/PR07 artifact manifests: **1,009 file entries**
  match. Thirty-six protected evaluator/worker/pin/meter files match `f36e5d8`.
  Evidence: `build/pr-08-validation/protected-001.json`. No private recording or
  consumed render claim was opened, replayed, copied or rendered.
- A broader scope check verifies **250 baseline files** outside the twelve-path
  PR08 modification allowlist byte-for-byte, including all dependency declarations,
  frozen contracts/fixtures/meters and historical evaluator/worker sources:
  `build/pr-08-validation/source-scope-001.json`.
- Product static symbol check finds no evaluation/Signalsmith/allocation-audit/
  interpose symbols. Signed-bundle linkage checks remain part of normal validation.

## Validation and delivery

- `build/pr-08-validation/final-002/`: **11/11 Release, 11/11 Debug, 4/4 ASan and
  4/4 TSan** passed. No build warnings, sanitizer errors or JUCE assertions.
  Release tooling ran 219 tests before the reporting regression was added;
  Debug tooling ran all 220 afterward. The final stable-source rerun is separate.
- `build/pr-08-validation/final-003/`: **11/11 Release, 11/11 Debug, 4/4 ASan and
  4/4 TSan** pass again, including **220 Python tests** in each normal tooling run.
  Non-documentation source hashes are unchanged throughout execution; compiled
  sources are unchanged since `final-002`. No sanitizer errors or JUCE assertions.
- The final full build-only coordinator passes **14 exact-AU cases** plus fresh-
  process ClassInfo/audio recall: distinct PIDs, exact finite/nonzero 76,800-frame
  float audio at 48 kHz including tail, unchanged state/binary/bundle. Report:
  `final-003/exact-au-check/report.json`. The original 96-route/35,136-block built-AU
  regression also passes; its aligned-original scope is not harmony qualification.
- Sanitizers exercise DSP/fake product/native UI/fake reference contracts. ASan
  uses `detect_leaks=0:halt_on_error=1`, TSan `halt_on_error=1`; process-wide leak
  freedom, native realtime performance and whole-AU lock freedom are not claimed.
- Preserved signed delivery path: `build/pr-08-artifacts/ready-20261026-01/`.
  It contains the exact 0.3.0 component and native harness, source snapshot,
  dependency/build identity, failure/final logs, offscreen UI images and SHA-256
  manifest. Product linkage is arm64/system-only, with no evaluation, Signalsmith,
  allocator-audit or static interpose linkage. No installation or re-sign is needed
  to preserve the already signed build.
  Compiled BuildInfo honestly records `f36e5d8d635d-dirty`; exact source and binary
  hashes bind the delivery instead of pretending that pre-commit build embedded
  a later commit. The artifact remains separate from all four old deliveries.

## Acceptance boundaries

Prior user-reported evaluation-AU acceptance remains accepted, without requiring
the same audition again. It does not certify this new product binary. Actual
installed identity/`auval`, Logic routing/PDC/LLM, recorded-vocal onset and
re-acquisition, real reopen/duplicate and real host bounce acceptance remain
required and pending. Formal accuracy/full-support, expressive challenge c,
performance/soak, licensing and final studio go also remain open. Historical pitch,
preparation and worker-startup failures and consumed claims are unchanged.
