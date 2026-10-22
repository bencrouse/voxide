# PR 03 — independent Herdr review and fixes

The user requested the existing Herdr `voxide-review` agent on 2026-10-22. It
reviewed the entire uncommitted PR 03 tracked diff and new files against `dc91812`,
contracts and existing evidence, read-only. It reported **six actionable findings**
and requested changes. It did not build/test, edit, access private recordings,
operate Logic/devices or install anything. Known timing misses and pending human
qualification were correctly kept separate from code defects.

## Verified findings and implemented fixes

1. **P1 — AU automation order:** new parameters reused source's version hint 1,
   allowing JUCE's hash sort to move Logic's existing source automation index.
   Keep source ID 449045605/hint 1; all new parameters use hint 2. Native tests now
   assert the **unsorted** actual AU parameter-list prefix, plus processor hints.
2. **P2 — unrelated edits reset hysteresis:** changing another voice or unused custom
   controls could move the source anchor and change untouched harmony intervals.
   Preserve it unless root, active set or mode changes. Regressions cover offset/
   inactive-custom edits and intentional defining-root changes.
3. **P2 — mixed source history:** a playhead callback could mutate controls after
   source selection but before a reset reread them. Capture source, tracker variant,
   harmony config and recall generation once; every reset uses that snapshot.
   Deterministic fake-host regressions inject source/variant, voice and recall
   changes at that exact point and verify next-callback application/history reset.
4. **P2 — false release diagnostics:** the legacy bitset cleared on the first release
   of repeated note-ons, even when a musical note remained held. Export authoritative
   repeated-press, physical-key, sustained-key and sounding-pitch counts, independently
   of diagnostic MIDI truncation. Release analysis requires known, unbypassed musical
   counts, with both presses and sounding pitches zero. Legacy logs remain usable for
   routing analysis, **not** repeat/sustain-aware release qualification. Tests cover
   insufficient note-offs, pedal-only sustain, missing/inconsistent counters and
   unknown/bypass state. These counters describe plug-in state, not external hardware.
5. **P2 — missing decisions falsely score well:** a stale correct estimate could
   indefinitely score later frames, and dwell could bridge observation gaps.
   Validate exact compiled probe cadence/support/coverage, expire stale estimates,
   and restart dwell on missing decisions. Tests cover missing middle, truncated
   tail, no-output and gap-spanning dwell; unavailable estimates remain failures.
6. **P2 — private-file byte binding:** validated paths alone did not bind later audio
   to registered hashes. Retain the validated manifest's digests, check manifest
   stability, and hash/decode one immutable WAV byte snapshot. Refuse replacements
   before consumption; synthetic tests also prove swap-and-restore during decoding
   cannot substitute different PCM. The existing permission/split validator and
   development-only selection remain mandatory. No holdout mode is added.

## Additional directly related corrections

- A frame whose exclusive end equals source onset has not consumed the event: it
  cannot start that event's settling dwell. Added the off-by-one regression.
- The analytic rhythmic generator had a one-sample floating-point onset discrepancy
  and clipped some E2 bends flat. Onsets now use the same integer arithmetic as PCM;
  edge-register bends are continuously shaped within support, never clamped. Version
  `pr03-analytic-v2-unclipped-bends` and research schema v2 distinguish these runs.
  Original exploratory evidence and all expressive user audio remain unchanged.
- Recognition limits now use the event's actual source F0 at onset, not the case's
  starting register label. In particular C3→E-flat3 crosses 150 Hz and requires the
  high-register 30 ms limit, not the low-register 50 ms limit. Per-band p95 groups
  and a boundary-crossing regression prevent incorrectly relaxing this requirement.

## Validation and rereview

Targeted Debug **5/5** suites and the expanded metric/routing unit tests pass.
Revised analytic research at
`build/tracking-checks/20261022T191209Z-a0fec7a4/report.json` completes with 140
case/variant runs, 3,264/3,264 supported stable voiced frames within 25 cents and no
observed stable octave errors. Recognition timing still misses requirements; no
vocal/live or architecture pass is implied. This intermediate run is not a substitute
for final full-profile qualification.

The reviewer re-read all six fixes/regressions and the onset/generator corrections
and reported **no remaining concrete issues**. This was file-read review only;
Debug/Release 5/5 and ASan/TSan 2/2 then passed with a stable source snapshot at
`build/checks/20261022T191434Z-57318c27/environment.json`, plus PR 02 calibration at
`build/evaluation-checks/20261022T191436Z-6c6e7959/report.json`.
The reviewer also re-read the final source-register classification correction and
its regression and reported **no remaining concrete issues**. It confirmed that
C3→E-flat3 correctly receives the 30 ms limit and fails at a 40 ms response. Again,
this was read-only file review, not test execution.

### Final post-review qualification

- **Full native checks:** `build/checks/20261022T191729Z-d1d453c9/environment.json`
  is **pass**, with source unchanged throughout. Debug/Release **5/5** suites each;
  focused ASan/TSan **2/2** each. The tooling suite now has **83 Python tests**.
  Ordinary Debug/Release allocation self-tests detect deliberate C/C++ allocation
  controls and report zero allocations in exercised callbacks. Sanitizer profiles
  explicitly do not substitute for that separate allocation audit.
- **Foundation regressions/calibration:**
  `build/evaluation-checks/20261022T191732Z-b5c88f9d/report.json` is **pass**, with a
  stable source snapshot. Frozen analytic assets and the PR 02 contract are unchanged.
- **Compiled research:** `build/tracking-checks/20261022T191754Z-1b046b23/report.json`
  is the final full-workflow research run. The additional repeat at
  `build/tracking-checks/20261022T191837Z-e08aa2c3/report.json` exercises the same
  final source/binary and registered private-input path: 140 analytic case/variant
  runs; 3,264/3,264 supported stable voiced frames within 25 cents; six private
  development traces remain **ungraded**, under
  `evaluation/pr-03/20261022T191837Z-e08aa2c3/`. Source-onset register classification
  is explicit, including the 30 ms C3→E-flat3 requirement.

Recognition timing misses, voicing hangover and deferred human/Logic/product gates
remain open. No actual-vocal accuracy or architecture acceptance is inferred.
Original recordings, canonical excerpts and earlier failed/exploratory evidence
are retained unchanged. After these stable-source checks only evidence/handoff
documentation was updated, not implementation, tests, fixtures or contracts.
Review/fix work did not stage, commit, merge, push or install anything. The user
subsequently approved local commit/merge as an engineering/research milestone,
retaining all timing, human and host qualification gaps. No push or install is
authorized; private evaluation data remains excluded.
