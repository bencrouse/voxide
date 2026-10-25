# Signalsmith studio verification — bounded proposal

**Status: PR06A blocked by A2 output-pitch failure, 2026-10-24.** The user requested completion
of the outstanding PR06A work after the partial research/tooling merge. This does
not authorize another private render, installing an AU or operating Logic.
The user subsequently approved **synthetic-only execution**. The
[independent code review](evidence/pr-06a/review-001.md) found five tooling defects;
their [repairs, negative regressions and follow-up review](evidence/pr-06a/review-fixes-001.md)
are now complete. A1's synthetic calibration driver and regressions are implemented;
the bounded [execution contract](evidence/pr-06a/signalsmith-verification-execution.json)
freezes generator, meter hashes, support/eligibility and stopping rules before
execution. Calibration runs before any A2/A3 capture; no new approval is needed
for the already approved synthetic scope. **A1 passed all 36 fixtures** (28 positive,
eight negative) at `build/studio-verification/20261024T200210Z-edb48fa4/report.json`;
all positive fixtures have 100% eligible observations within 25 cents. The meter
and driver/provenance remain bound by hash. A2 executed with independent generated
targets, input/control hash verification, oracle/tracked timelines and dense output
measurement. **34/72 cases fail output-pitch gates**: the same 17 conditions per
mode, despite passing source/control/safety checks. A3 is correctly stopped. See
[the results and PR stop decision](STUDIO_VERIFICATION_RESULTS.md).
A failed mandatory gate remains a stop,
not permission to tune the meter or silently mark PR06A complete.
[Machine-readable proposal](evidence/pr-06a/signalsmith-verification-proposal.json):
`pr06a-signalsmith-verification-001`. No new DSP executions or private source-audio reads
were performed for the original gap review; retained synthetic JSON and implementation
contracts were inspected. Historical protocols, results and consumed approvals
remain unchanged. No engine has received final selection or a studio go.

## 1. Evidence and gaps

Signalsmith 2048/512 with the existing Accelerate backend is the provisional
engineering lead. Native consonants, existing formant preservation, three voices,
scale semantics and the inclusive ±12/inactive-uncertain guards stay fixed.
Rubber Band remains a sonic reference, not an additional test-matrix dimension.
The user's slight preferences on a and c are explicitly non-decisive; do not run
another tiny subjective comparison to force a ranking.

| Gate | Retained evidence | Remaining obligation |
| --- | --- | --- |
| Pitch/target correctness | PR05 Signalsmith cases 0136/0137/0396/0397 deliver upper/lower scale output at both rates, but every voice misses the historical sparse stable-pitch target | Isolate reference/observer, tracker/control and shifter contributions; do not mark accuracy passed because delivery or listening passes |
| E2–C6 / inclusive ±12 | Guard tests exercise accepted octave targets, rejected outside targets and uncertainty; the engineering workload includes low/high registers | Demonstrate musical output, not just bounded telemetry; separately freeze full-envelope/scale-catalog coverage before PR06B |
| Complete studio delay | Lead is exactly delayed 4,410/4,800 samples; selected synthetic cases meet fixed 100 ms delivery | Verify actual output/decision clocks and first-syllable/transition/tail behavior; a declared delay or available sample is not proof of correct-pitch settling |
| Callback cost/allocation | 24 Signalsmith synthetic captures: zero allocation calls/overdue callbacks, worst per-capture p99.9 occupancy 9.64% | Retain the passing sampled result, not universal host certification; assess novel dynamic workloads without concurrent builds/profilers |
| Repeatability | 30/30 exact synthetic cold/reconstructed/warm-fresh/process/partition comparisons | Same checks on approved actual vocal a/c need new receipts; native reset and realtime state handoff are separate questions |
| Lifecycle | Finalized restart rejection and stopped reconstruction pass; all owners must be stopped/joined | No callback-safe swap/reset/seek implementation is established; off-render allocation is not an audio-thread-safe state-handoff design |
| Recorded-vocal character | Both listening trials yield only a small Rubber Band preference | Development feedback is not independent timbre, pitch, articulation or bend qualification; c did not receive a separate artifact-absence rating |
| Host/PDC/bounce | Existing dry AU/routing evidence only; research processor has a software delay query | Real three-voice compensation, transport/recall/bounce and representative-session evidence are missing |
| Resources/licensing | Pinned free engines; one singer/three development excerpts, no completed human pitch references | Formal resources, independent review/listeners, studio rubric, license/distribution decision and explicit PR06B go still block product integration |

### The first blocker is accuracy attribution, not another CPU contest

Retained synthetic metadata gives these **within-25-cent counts out of 21 stable
observations per voice**. These are historical sparse observations, not new vocal
measurements or a regrade under the current studio guard settings.

| PR05 case | Rate / voicing | Voice 1 | Voice 2 | Voice 3 |
| --- | --- | ---: | ---: | ---: |
| 0136 | 44.1 kHz / upper | 16/21 | 12/21 | 10/21 |
| 0137 | 44.1 kHz / lower | 16/21 | 15/21 | 15/21 |
| 0396 | 48 kHz / upper | 15/21 | 10/21 | 12/21 |
| 0397 | 48 kHz / lower | 16/21 | 15/21 | 17/21 |

Thus all 12 voice/case groups are below 99%; “sparse misses” must not be read as
already negligible. These captures use the historical ±24/uncertainty-ablation
defaults, not the pilot's explicit ±12/inactive-uncertain settings. The independent
8192-sample observer, short/transition-adjacent synthetic regions and low-register
octave ambiguity limit attribution. They do **not** justify deleting the failures,
assuming the meter is wrong, or concluding every audible frame is wrong.
The report hashes/case IDs are bound in the proposal for later verification.

## 2. Stage A — synthetic attribution, then eventful delivery

**A1 passed; A2 completed with failed output-pitch gates; A3 not executed under the stop rule.**
One candidate, no DSP tuning, no playback,
no private sources, no new backend/window/policy or engine sweep. Freeze the driver,
fixture definitions and measurement protocol before execution. Preserve current
historical contracts; changes to observer instrumentation require their own
calibration and explicit labels, never retrospective replacement of old results.

### A1. Check the meter before using it to blame tracker or engine

- **36 measurement-only fixtures:** two rates × seven known output pitches
  (MIDI 28/40/45/57/69/84/96, covering E1–C7) × sine/six-harmonic shapes = **28**
  positives; four negative controls per rate = **8**. No shifter executions.
- Analytic fundamental/phase and source time are generator truth, not values
  obtained from the product tracker. Six-harmonic input is deterministic, with
  amplitudes proportional to 1/h and no partial above Nyquist. Include the full
  output range implied by E2 down an octave and C6 up an octave.
- Keep the existing independent full-range pitch instrument and unconstrained
  search; do not narrow its search around the expected answer. Check known
  semitone and octave errors against deliberately mismatched references.
  Silence/noise must never earn a correct-pitch/voiced-accuracy pass merely because
  there is no usable reference or output; retain false detections diagnostically.
- Use a known three-second primary signal plus 0.6-second zero tail. Record all
  windows/support, eligible counts, missing estimates and exclusions. Use the
  existing 10 ms reference grid and 50 ms stable-boundary exclusion, and disclose
  complete observer support. A clean inner region may help attribution but may
  not replace the accuracy denominator or remove an error from the full record.
- **Stop if calibration cannot recover correct pitch or expose wrong controls.**
  Diagnose the instrument before any engine accuracy claim; do not retune its
  thresholds against candidate output or quietly substitute a new favorable meter.

### A2. Match prescribed controls against the full tracked-scale path

**72 native captures maximum:** two rates × E2/A3/C6 × two source shapes × three
voicings × two modes. Use 128-sample callbacks, three-second primaries and the
same supplied 0.6-second tail. Both paths retain the same fixed 100 ms reserve.

Voicings are octave/unity/octave (`degrees [0,0,0]`, octaves `[-1,0,1]`), existing
upper (`[2,4,0]`, `[0,0,1]`) and lower (`[-2,-4,0]`, `[0,0,-1]`). For steady
C-major E/A/C sources, derive target intervals independently from analytic source
pitch and the approved scale rules; never use measured selector output as its
own expected target. Include all three active voices, exact ±12 endpoints and
unchanged lead. Reject outside shifts rather than clamping into another note.

1. **Analytic F0 + prescribed targets:** bypass tracking for diagnosis only. Oracle
   events carry explicit source and actual availability times; do not invent a
   future pitch frame or backdate a decision. Record this bypass in every result.
2. **Tracked C-major scale:** actual tracker/selector, source deviation preserved,
   no lead tuning/key detection. Only this path exercises the intended architecture.

Store all ten raw channels, input/control hashes, event/settings files, native
stats and telemetry. Use the same source-derived attenuation and lead 1 / harmony
1/3 gains; no output normalization, clipping or changed thresholds. No playable
exports are needed. Nonfinite output, missing/late delivery, bad lead null/fixed
sum, invalid controls, wrong duration or nonzero unrendered tail stops the stage.

Separate analytic target error, measured tracker error, requested/applied native
ratios and output pitch. Retain per-voice/register/rate failures, octave errors,
missing observations and continuous wrong-note duration. The existing ±25 cents,
≥99% stable accuracy, <0.1% octave-error fraction and ≤50 ms wrong-note duration
remain; small correlated frame samples cannot establish full vocal qualification.

**Checkpoint:** meter failure → stop instrument attribution; prescribed failure →
investigate native/control path; tracked-only failure → investigate tracker/selector
or timing; both pass → proceed only within the approved staged protocol. Historical
failures stay failed. No parameter correction or automatic retry is included.

### A3. Check events, not just sustained vowels

Only after A1/A2 are credible: **16 tracked-scale captures** = two rates × 128/512
callbacks × four fixed eventful scenarios, five-second primaries + 0.6-second tail:

1. Cold first syllable, with no hidden future pre-roll. Fresh mid-phrase/seek
   reacquisition stays a separate host/lifecycle check, not an extra uncounted
   graph/capture inside this scenario.
2. Continuous bends/vibrato through scale-anchor boundaries, with analytic
   generator truth and the approved tie/hysteresis policy.
3. Voiced → consonant/noise → silence → voiced reentry; inactive uncertain targets
   and preserved rhythm, not held old pitch or manufactured dry-copy processing.
4. Scale voicing changes including accepted ±12 endpoints and out-of-range target
   disable/reentry; at least one scenario uses asymmetric voice intervals.

For each event retain source onset, tracker support/end/availability, requested
control, native API application, output source index, packet availability and final
callback delivery. Measure complete delay without subtracting analysis, observer,
callback or adaptation time. Report the lead's 100 ms alignment separately from
correct-pitch acquisition/settling; the ≤100 ms processing ceiling is **not** a
new ≤100 ms settling allowance. Retain the historical response diagnostics and
unresolved events; recorded onset/transition acceptance still needs approval.

Report callback allocations, all cold/body/tail observations, nearest-rank p99.9,
maximum and overdue count from optimized audited Release only, after safety builds
finish. Retain zero allocations, p99.9 occupancy <50% and zero overdue callbacks as
sampled engineering gates. Sanitizers qualify safety, not performance. Do not count
audio absent due to an intentional inactive target as lost primary delivery.

**Total Stage A cap:** 36 calibration fixtures + **88 native captures**. Stop at
each substage on a failed mandatory gate; there is no automatic tuning cycle.
This samples registers/intervals; it does not qualify all E2–C6 pitches, continuous
ratios, all 42 scale entries/12 roots or custom sets. A full support-coverage
protocol must still be approved before PR06B acceptance; C-major diagnostics do
not silently shrink the promised scale scope.

## 3. Stage B — actual-vocal repeatability, separately authorized

**Blocked on new source/protocol-bound receipts.** Propose only existing a and c,
at native 48 kHz; exact identities/permissions stay in ignored `evaluation/`.
Do not search for more recordings or access holdout. Consumed a/c render and
half-level export receipts cannot authorize these runs. No audio was read in
preparing this proposal.

- **8 native invocations / 24 captures:** two sources × two partitions (128/512)
  × two independent processes, each capturing cold, stopped-reconstructed and
  warm-process fresh graphs. Original diagnostic C-major/upper settings, source
  attenuation, ±12 guards, three-voice mix and tails remain identical.
- **30 comparisons across all ten raw channels:** per source, 12 within-process
  pairings, two independent-process pairings and one cold partition pairing.
  Matching native input/control hashes and exact lengths precede waveform claims;
  mismatch is not attributed to engine nondeterminism. Retain max 1e-6 / RMS 1e-7.
- Compare **raw pre-playback-trim** samples, not quieter previews. Check the original
  archive/source/settings/provenance bindings and record current binary/compiled
  identity; do not assume historical and newly instrumented builds are identical.
- No pitch grade without trustworthy references. A separate unannotated
  engineering-replay exception must be explicit; equal outputs can both be wrong.
  No playable exports, new A/B ranking, source repairs or DSP correction are proposed.
- Stopped reconstruction requires all render/producer/telemetry owners stopped
  and joined. Passing it does not qualify native `reset()` or a realtime swap.

## 4. Stage C — host/PDC contract, then explicitly approved evaluation host

**Planning only.** The current AU is dry and cannot establish three-voice Logic
compensation. Do not test that shell and label its success a harmonizer pass.
Product integration (PR07) stays blocked until PR06B go, yet actual host evidence
is needed for a credible studio decision. Resolve this dependency explicitly:

1. First specify a single aligned-lead/three-voice timeline, integer latency
   reporting/notifications, supported recorded-vocal bus, automation clock and
   stopped-state lifecycle. The native delay/null results establish feasibility
   only; host evidence remains pending.
2. If native/formal prerequisites are credible, seek separate approval for a
   **research-only AU adapter with its own component identity** and independent
   review, using the same shared DSP path. This is a proposed bounded evaluation
   exception, **not** authorization to integrate/select the product engine, install
   anything now or operate the user's Logic/device. If not authorized, keep the
   host gate blocked; never issue a full studio go from native evidence alone.
3. Only with test-component/source/session approval: **24 synthetic host captures**
   = two rates × two buffers × realtime/offline × three disclosed scenes:
   known delayed-lead compensation reference; active three-voice octave/scale
   blend; and an expression/automation/transport sequence. Compare **12** matched
   realtime/offline pairs with the retained waveform tolerances, not manual gain
   matching, dynamic re-trimming or a hidden offline-quality mode.
4. Test cycle/seek, stop/resume, mid-phrase start, bypass and key/degree changes,
   save/reopen, tail flush and correct epoch reset. No reconstruction/allocation,
   locks, files or unsafe ownership replacement on the callback. Render-safe state
   handoff is an implementation/review prerequisite, not a promise derived from
   stopped graph reconstruction.
5. Disclose actual installed binary, Logic/macOS identity, route, buffer/rate,
   PDC settings and Low Latency Mode behavior; do not infer successful harmonizing
   from a bypassed/silent route. The known direct/track-fed routing limitation stays
   visible. A true lead-only reference can check compensation; the separate active
   scene must prove three voices were actually processing.
6. Measure integer reported vs observed delay and compensated lead null against
   original max 1e-6 / RMS 1e-7 tolerances. Do not use phase/correlation of a
   pitch-shifted vowel as a perfect sample reference or excuse missing syllables
   with PDC. The complete ≤100 ms ceiling still includes all processing buffers.
7. Separately approve one representative recorded-vocal session: the retained
   **30-minute, zero-dropout** screen is one disclosed workload, not universal host
   or multi-instance certification. Its private source and actual owner workflow
   must be specified first; no new corpus or session is assumed available.

## 5. Decisions and stopping rules

- **Current checkpoint:** the user approved at most one evidence-backed wrapper/
  configuration correction and regression, not tracker changes. The subsequent
  [audit](evidence/pr-06a/wrapper-audit-001.md) found no justified correction. Stop/
  reject the current configuration; no new native run or allowance was consumed.
  A3 and PR06B remain blocked. Original consumed stage claims are not reusable.
  The five tooling defects are repaired/regressed and independently closed; see
  the linked repair record. The original proposal
  JSON remains a historical proposal, not a private-source execution receipt.
  Stage B and C require separate approvals regardless of
  a successful A result; no private-audio exception is inherited or broadened.
- No spend, engine shopping, new backend, package installation, upstream patches,
  uploads, automatic playback, AU/product integration or commit/merge/push.
- The subsequently approved correction/regression allowance is **unspent** because
  no evidence-backed change was identified. No configuration sweep, speculative
  rerender or tracker change follows from that approval. Any actual correction
  still needs its exact diagnosed change and single-use regression protocol frozen
  before execution; this audit does not create or consume such a claim.
- Full human references, independent listening, processed-character/formant and
  recorded-onset criteria remain approval/resource gates. Existing formant/response
  diagnostics stay visible; they are not silently replaced by informal preference.
- If mandatory blockers persist, retain an explicit studio no-go/pending decision;
  do not keep rewriting the plan until a green checkbox appears. PR06B go and final
  engine selection require explicit user approval. Live/MIDI/±24 remain deferred.
