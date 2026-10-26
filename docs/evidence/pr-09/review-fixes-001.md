# PR09 independent-review fixes — 001

Follow-up to [review-001](review-001.md) of `8aa76c6..4de958d`. User requested
addressing all three findings on `pr-09-studio-session-qualification`.

## Fixes and regressions

- **R1:** share the actual native screen sample-observation code with executable
  negative controls. A wet sample must have finite, nonzero above-threshold output
  in both channels **and** differ from the lead reference in both. Silence and a
  lost channel no longer count as harmonies. Native controls cover silent, dry,
  one-channel and genuine nonzero changed output at both rates. The analyzer also
  requires audible output in each body second; a silent screen fails explicitly.
  This is aggregate activity, not proof of correct pitch or unchanged lead.
- **R2:** native capture assigns each observed sample to its absolute output-time
  second. Raw **v2** CSV contains separate wet/audible counters for all five seconds
  in every callback. Analysis sums the right buckets and validates counts against
  the callback's exact overlap with each second, wet≤audible, and finite-frame
  bounds. Native and Python controls use the `[88045,88302)` boundary scenario;
  post-88200 activity cannot cover the preceding dry second. Old aggregate v1
  records cannot establish the stronger gate and are refused by the new analyzer.
- **R3:** validate every header text field as a bounded scalar string, with no NUL;
  require nonempty identities and an absolute module-path string. OS/CPU may be
  empty when native system descriptions are unavailable. Path validation performs
  no access to the module file. A finite `parse_float` hook rejects exponent overflow
  anywhere, in addition to literal NaN/Infinity rejection. Regressions cover nested
  payloads, arrays, booleans/numbers/null in all text fields, overflow, invalid/
  oversized text and retained failed reports for malformed headers.

The shared native observation controls run in normal processor/exact-AU tests and
the focused sanitizer processor tests, outside any measured AU call. New screen
reports require `voxide.pr09-screen.v2` and guard evidence; the producer's session
metadata schema remains v1 because its emitted values/fields are unchanged.

No product DSP, worker/source clock, latency, engine, host parameter/default/state
meaning, musical limit or frozen meter/acceptance threshold is changed. These are
test-observation and parser fixes, not a repair of the known variable-block audio
delivery failure.

## Evidence boundaries

Original signed delivery `build/pr-09-artifacts/ready-20261026-01/`, the entire
`build/pr-09-validation/final-001/` screen and its negative qualification remain
untouched. The timing screen is **not rerun** for this review fix, and historical
passing observations are not relabeled as corrected-v2 measurement passes.
The original 44.1 kHz variable failure remains unresolved; actual Logic soak,
whole-host evidence and independent final listening/rubric remain pending. No
private metadata/audio, consumed approval or actual host operation is accessed.

Initial targeted execution: all **21** session Python tests pass (six new test
methods beyond the original 15). Final four-profile execution, independent source
verification and a separate review-fixed artifact are recorded when complete.

## Independent source verification and follow-up

The same `pr09-review` agent independently re-read the fix diff and new shared
native counter, explicitly closing **R1/R2/R3's reported scenarios at source
level**. It found one additional **P3** malformed-data gap: positive peak alone
allowed impossible activity counts with a reported peak of 0.000001, below the
counter's 1e-4 threshold.

The analyzer now requires an activity-bearing row's peak **≥1e-4**. Equality is
intentional: the native six-decimal serializer can round actual output just above
the threshold to exactly 0.000100. A regression rejects the impossible low peak
and retains this valid rounding edge. This is a parser-consistency check, not a
change to the native detector, DSP, frozen tolerances or historical screen result.
The reviewer's source-only follow-up ran no builds/tests and accessed no artifacts,
private material or host resources. Original validation and review feedback remain
preserved; the final-source Python addition is validated separately.

The same reviewer then inspected the targeted P3 correction and its rounding-edge
regression, explicitly judged **P3 closed at source level**, found no remaining
concrete defect in that change, and retained the prior R1/R2/R3 closures. Again,
no execution, artifact access or timing rerun was claimed by the reviewer.

## Preservation

`build/pr-09-review-fixes/protected-001.json` verifies all **seven** prior artifact
manifests (**2,061 file entries**) and **274 baseline files** outside the intended
fix paths. Product DSP, telemetry producer, native worker/engine, frozen meters,
dependency pins, old source/binaries and original negative screen remain unchanged.
A separate review-fixed delivery uses `build/pr-09-artifacts/ready-20261026-02/`.

## Executed validation and delivery

- `build/pr-09-review-fixes/validation-001/`: Release/Debug **11/11 each**, including
  **244 Python tests** each; focused ASan/TSan **4/4 each**, before the extra P3
  parser consistency regression. Build logs have no warnings or errors.
- `validation-002/`: final-source Release/Debug **11/11 each**, including **245
  Python tests** each; ASan/TSan **4/4 each**. Compiled sources are unchanged since
  the first run, and final non-documentation hashes are stable throughout this run.
  No sanitizer errors or JUCE assertions. ASan uses `detect_leaks=0:halt_on_error=1`,
  TSan `halt_on_error=1`; process-wide leak/native realtime claims are not inferred.
- Exact-built-AU functional checks and fresh-process ClassInfo/audio recall pass;
  the actual shared observation controls execute in the processor and AU harnesses,
  including focused sanitizer processor coverage. No full timing screen is run.
- Separate signed 0.4.0 component/native harness, exact source/logs/UI captures and
  SHA-256 manifest: `build/pr-09-artifacts/ready-20261026-02/`. BuildInfo honestly
  embeds `4de958d72137-dirty`; exact committed source/binary hashes bind that build,
  without a post-validation rebuild, re-sign or installation.

The product remains **not qualified**. Original variable-block audio failure,
missing actual Logic soak/whole-host evidence and independent-listening/rubric
gates remain open. Review closure addresses code defects, not those qualifications.
