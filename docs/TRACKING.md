# PR 03 — causal tracking and target selection

Engineering implementation, not a qualified live harmonizer. Audio remains a
bit-preserving mono-source copy to both outputs, including bypass, with zero added
audio delay. **Zero audio delay does not mean zero pitch-decision delay.** No
shifter, automatic key detection, lead tuning or audible harmony is included.

## Musical contract and controls

The user approved starter scale/MIDI/uncertainty policies on 2026-10-22, requesting
broad exotic-scale support. The versioned record is
`docs/evidence/pr-03/musical-contract.json`. PR 02's frozen numerical/protocol
contract is unchanged; its historical pending musical field is superseded for
these starter rules only, not for listening/resource/measurement approvals.

- 41 built-in **12-TET pitch-class sets** plus Custom, all 12 roots. Includes seven
  diatonic modes, harmonic/melodic minor, melodic-minor modes, harmonic major,
  double harmonic, Hungarian/Neapolitan sets, Phrygian dominant, Ukrainian Dorian,
  Persian/Enigmatic, pentatonics, blues, Hirajoshi/Insen/Iwato/Kumoi/Pelog sets,
  whole-tone/diminished/augmented, bebop and chromatic. Ascending melodic minor is
  a static set, not direction-dependent classical melodic minor.
- Traditional named sets are **12-TET approximations**, not complete raga/maqam,
  intonation or microtonal support. Exact IDs/masks live in `HarmonySelector.cpp`;
  the compiled probe exports the catalog with `--scales`.
- Custom exposes 12 root-relative pitch-class switches. Any set, including sets
  without the root, is allowed. Empty custom sets deactivate scale targets.
- Each voice has signed **degree steps** (zero-based displacement, not conventional
  ordinal interval numbers) and **octaves** separately. Defaults `(2,0)`, `(4,0)`,
  `(0,1)` mean third, fifth, octave above in major. On pentatonic, degree steps
  follow that set's members; `(0,1)` always remains an octave.
- Anchor the continuous source pitch to its nearest scale member, with downward
  exact ties. Keep that anchor until a competitor is 30 cents closer: a 15-cent
  midpoint hysteresis band, no dwell. Target = continuous source pitch + interval.
  Accidentals, vibrato, scoops and bends remain in the targets and unchanged lead;
  this is not source-note correction. Crossing a real degree boundary may change
  the interval. The hysteresis magnitude is an engineering choice, not perceptually
  qualified; it does not smooth away source expression.
  Offset edits and unused custom switches retain the anchor; changes to the defining
  root, active pitch-class set or mode invalidate it.
- MIDI uses **absolute sounding pitches**, newest three distinct pitches, with
  surviving targets in stable slots. Newest unassigned pitches fill lowest free
  slots; older held pitches return when room opens. Counts are per channel/pitch;
  duplicates occupy one voice. Repeated note-ons need matching note-offs.
- Per-channel CC64 sustain, CC120 immediate channel kill, CC123 all notes off
  respecting sustain, CC121 release pedal without releasing physical keys,
  velocity-zero note-on as note-off, and system reset are handled. MIDI pitch bend,
  aftertouch and MPE interpretation are not implemented. Absolute MIDI targets
  intentionally do not copy source bends; their shift relative to the lead changes.
- Uncertain/unvoiced source disables every pitched target. Silence clears the
  source anchor but keeps actually held MIDI. Each target outside an inclusive
  ±24-semitone shift is disabled, never clamped. No out-of-range target changes
  the original lead.

## Causal algorithms and timing

`PitchTracker` uses fixed arrays, no heap, locks or future samples. Both variants
run the same streaming, cumulative-mean-normalized YIN difference functions:

| Property | 44.1 kHz | 48 kHz |
| --- | ---: | ---: |
| Internal rate, after 2-sample box averaging | 22,050 Hz | 24,000 Hz |
| Comparison segment | 512 internal samples | 512 internal samples |
| Maximum lag (including interpolation margin) | 269 | 293 |
| Total source support | 1,562 samples / 35.42 ms | 1,610 samples / 33.54 ms |
| Hop | 220 source samples / 4.989 ms | 240 source samples / 5 ms |
| Lookahead | 0 | 0 |
| First eligible frame after reset | 39.91 ms | 35 ms |
| Earliest voiced decision (two good frames) | 44.90 ms | 40 ms |

Candidate comparisons are anchored at the newest comparison segment. Baseline
chooses the first local minimum below 0.15. Multi-candidate scores all bounded
local minima with a weak shortest-period/previous-pitch prior; it is **not** offline
Viterbi/path optimisation and is not proven superior. Parabolic lag interpolation
produces unsmoothed continuous F0. Entry requires two good analysis frames;
confidence <0.85, nonfinite support or AC RMS below −55 dBFS immediately marks the
next analysis decision unvoiced. Confidence is a periodicity score, not a calibrated
probability. There is no extra hold-last-pitch smoothing or gap filling.

The two-sample box prefilter is not a brick-wall anti-alias filter. Both variants
remain research trackers for monophonic E2–C6 input at 44.1/48 kHz. Unsupported
sample rates emit no pitched decisions while preserving the dry lead. Out-of-range
or polyphonic sources may produce in-range octave/harmonic aliases; no reliable
unsupported-source detector is claimed. A windowed detector may remain voiced
briefly after an actual source offset; native traces retain these false triggers.

Every frame carries epoch-local `[begin,end)` source support and `available`, the
consumed-sample count when the decision exists. `end == available`; no backdating
to a window center or target onset. These timestamps identify source history, not
host PDC or audible harmony onset. Processor telemetry adds `tracking_epoch`, F0,
confidence, voicing, targets and MIDI validity to existing bounded block snapshots.
It does not log every target event or PCM. Logs may drop metadata under queue
pressure; this cannot alter the musical state.
Authoritative block counters separately report physical channel/pitch keys,
repeated key presses, pedal-sustained keys and distinct sounding pitches. The old
`held_keys` bitset remains legacy metadata, not proof of musical release.

## Integration, reset and persistence

Analysis reads the selected source's first channel **before** aliased output writes.
Musical MIDI is delivered at its sample offset, before that sample's analysis,
preserving host ordering for equal offsets. The old 64-record diagnostic limit
never limits musical delivery. A separate 4,096-event/callback ceiling fails closed
on overflow or invalid offsets: clear notes and mark MIDI unknown until processor
or system reset. Repeated-key count overflow also fails closed. This safety ceiling
is intentionally not partition invariant when exceeded; normal event delivery is.
Channel-only panic cannot certify other channels after global event loss.

Reset/release, sample-rate preparation, source/tracker changes, state recall,
bypass transitions, known transport stop, backward seek or playing discontinuity
clear tracker history and transient MIDI. Live input continues while stopped after
the stop transition. Controls are sampled at callback boundaries; this is not a
claim of sample-accurate host parameter automation. State loading does not restore
held notes/history. Source parameter ID **449045605** and AU identity are unchanged.
`voxide-shell-v1`/`v2` load with musical defaults; v3 stores all 23 normalized
parameters in frozen order with little-endian float encoding, validating the entire
payload before applying it. Later parameter-layout changes need a new state version.
Source, tracker variant, harmony settings and recall generation are captured once
per callback and reused for every reset decision, preventing mixed-source history
when a host callback changes parameters. New PR 03 AU parameters use version hint 2;
the legacy source retains hint 1 and the first unsorted AU automation-list position.

The existing editor retains routing/logging diagnostics and adds the generic
parameter panel plus target readouts. Those are callback snapshots, not an audible
result or a substitute for event traces. No AU is automatically installed or opened.

## Reproduction and evidence boundaries

```sh
python3 scripts/check.py --full --offline
make tracking-check
```

Full checks include tracker/selector tests in the existing `dsp`/`processor` suites,
so the focused ASan/TSan selection cannot omit them. Release also evaluates the
compiled probe on frozen read-only PR 02 fixtures and deterministic development
stress cases. `build/checks/*/environment.json` captures source/binary hashes and
logs; `build/tracking-checks/*/report.json` retains raw frame CSVs, per-register
accuracy/octave/voicing counts and cold/continuous response distributions for both
variants. Failed research measurements do **not** become a passing product gate.

Accuracy uses source-grid decisions actually available at that point; missing
estimates stay in the voiced denominator, uncertainty is excluded and reported.
Stable-frame scoring excludes 50 ms around reference boundaries. Voicing counts
also include boundary frames deliberately, showing offset hangover rather than
hiding it. Recognition response is when a correct **20 ms dwell completes**, never
backdated to the first correct estimate. Nearest-rank percentiles and descriptive
Wilson intervals are not independent-singer statistical evidence.
The probe exports its exact hop/support/startup timing. Evaluation rejects missing,
extra or truncated decisions, expires estimates when their next decision is due,
and restarts dwell across gaps. A decision ending exactly at an event's source onset
cannot count toward that event's dwell. Development edge-register bends are shaped
inside E2–C6 without clipping their trajectory; integer onsets match the exact PCM
generator. These revised stress probes are versioned separately from frozen PR 02
fixtures. Private WAVs are hashed and decoded from the same byte snapshot against
their registered digest, not merely against a second read of a mutable path.

Allocation tests use a test-only dyld interposer for common C/C++ heap allocation
entry points; deliberate malloc/new controls must be detected before exercised
callbacks can pass. Cold/warm processor renders, routing partitions, resets and
event overflow are exercised. This audit is separate from ASan/TSan: sanitizer
malloc interception takes precedence, so interposition is **disabled in sanitizer
builds**, explicitly reported, and mandatory in ordinary Debug/Release. It is not
a proof against every possible VM allocator or every unexercised host path. The
audit dylib is never linked into the product.

Tests cover all 4,095 nonempty custom masks/all roots, signed degree and octave
wrap, built-in accidental/tie mapping, boundary vibrato and immediate deliberate
changes, repeated/channel-duplicate MIDI, sustain/controllers, ordering, overflow,
inclusive shift limits, state validation/legacy loading, causality by changed future
suffix, and fixed/mixed partitions 1/32/64/128/257/512/1024.

### Research result, not architecture acceptance

The revised two-sample/newest-segment implementation resolves the first exploratory
probe's C6 harmonic-mixture accuracy problem on these analytic cases. Original
exploratory reports are retained, not overwritten. Current development stable-frame
accuracy is 100% on the exercised analytic cases, including missing fundamentals
and rhythmic bends, but **recognition timing fails the approved limits**: cold
20-ms-dwell completion is approximately 60 ms at 48 kHz and 69.84 ms at 44.1 kHz;
continuous transitions and rhythmic entries also expose response lag. Voicing
hangover remains measurable at rhythmic offsets. A stable-frame pass excludes
transitions and must not be presented as preserving every rapid articulation.

The required real rhythmic/bending clip c is retained, not tuned, discarded or
promoted to reference truth. Optional approved development audio is traced only
after existing corpus permission/split/hash validation; there is no holdout mode.
All vocal traces/derived private evidence stay under ignored `evaluation/pr-03/`.
No real-vocal accuracy, intended-note, listening or live-monitoring pass is claimed
without trustworthy human references. Two actual annotators, full corpus/listeners,
remaining approvals, native-to-Logic validation and architecture acceptance remain
open. **PR 03 can be an engineering/reproducible research milestone, not evidence
that the harmonizer requirements are achieved.**

### Pre-review qualification — 2026-10-22 (historical)

- `build/checks/20261022T184815Z-2f9d18f8/environment.json`: **pass**, source unchanged
  throughout; Debug/Release **5/5** suites each, focused ASan/TSan **2/2** each.
  The tooling suite contains **72 Python tests**; native suites also exercise the
  exhaustive selector/tracker/processor regressions. Debug and Release deliberate
  C/C++ allocation controls were detected; exercised callbacks allocated zero.
- `build/evaluation-checks/20261022T184819Z-52b195b6/report.json`: PR 02 foundation
  regression/calibration **pass**, with unchanged source snapshot and all frozen
  analytic assets intact. This does not close PR 02 human acceptance.
- `build/tracking-checks/20261022T184844Z-b9622515/report.json`: research run included
  by the full workflow; `build/tracking-checks/20261022T184949Z-1d67e5d9/report.json`
  repeats it and adds explicitly registered private development traces. Both retain
  source/binary fingerprints and 140 analytic case/variant runs. The latter has
  **3,244 supported stable voiced frames across both variants, all within 25 cents**,
  no observed stable-frame octave errors on these cases. This is analytic evidence,
  not independently annotated vocal accuracy. Cold recognition p95 is 69.84 ms
  for every sampled register when pooling the two rates; continuous p95 is roughly
  49.43–54.42 ms, still failing the relevant recognition limits.
- Six private traces (three unchanged development vocals × two variants) and their
  ungraded report are under `evaluation/pr-03/20261022T184949Z-1d67e5d9/`. Clip c is
  retained with its rhythm/bends; no listening request, pitch-truth claim or holdout
  access. The first exploratory report containing private source metadata is
  preserved under `evaluation/pr-03/exploratory-first-pass-20261022T184234Z-d4555675/`;
  the intermediate revised analytic run remains under `build/tracking-checks/`.

These runs predate the independent review below. They remain historical evidence,
not qualification of the subsequent fixes. Their earlier edge-register development
generator clipped excursions; v2 instead shapes continuous in-range bends. No user
recording or frozen fixture was changed. See `docs/PR03_CODE_REVIEW.md` for review,
regressions and the superseding final qualification. Implementation/review did not
commit, merge, push, install or operate Logic.

### Final post-review qualification — 2026-10-22

Herdr `voxide-review` found six concrete issues. All were fixed with regressions;
focused rereviews of those fixes and the final register-boundary metric correction
reported **no remaining concrete issues**. See `docs/PR03_CODE_REVIEW.md` for the
finding/fix mapping and review boundaries.

Superseding full qualification:
`build/checks/20261022T191729Z-d1d453c9/environment.json` — **pass**, Debug/Release
5/5 each, ASan/TSan 2/2 each, 83 Python tests and stable source fingerprints.
PR 02 calibration/regression also passes. Final compiled research is at
`build/tracking-checks/20261022T191837Z-e08aa2c3/report.json`: 140 case/variant runs,
3,264/3,264 analytic stable voiced frames within 25 cents, no observed stable
octave errors, and six private **ungraded** traces. Actual recognition timing still
fails the approved limits; corrected metrics and native checks do not close human,
Logic, architecture or product acceptance. Only evidence/handoff docs changed after
the stable-source runs; nothing was committed, merged, pushed or installed.

The user subsequently approved local commit/merge of this engineering/research
milestone on 2026-10-22, with those qualification gaps retained. This does not
authorize pushing, AU installation or Logic operation; private data stays excluded.
