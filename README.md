# voxide

A vocal harmonizer project for Logic Pro, keeping the original lead and generating
three harmony voices. **Current priority: recorded vocals, scale mode, inclusive
±12-semitone support and an intentionally processed vocal character.** Live use,
MIDI-mode qualification and ±24 coverage are deferred, not achieved or cancelled.

**PR10 local handoff:** product remains **0.4.0**, **not qualified for studio use
or public release**. PR09's original 44.1 kHz variable-block wet-output failure
remains unresolved; corrected observation logic has not been timed again. See the
[setup/use/uninstall guide](docs/PR10_LOCAL_HANDOFF.md),
[evidence index](docs/evidence/pr-10/handoff-index.json) and
[negative-qualification report](docs/evidence/pr-10/implementation-001.md).
Local engineering completion does not close the missing Logic soak, whole-host,
independent listening/rubric, full-support/challenge-c or licensing gates.

**PR08 host/bounce implementation**, now merged locally, extends the
PR07 product. Version **0.3.0** added same-engine offline harmony
bounce, exact-built-AU tests and fresh-process recall. The user reports completing
the product Logic checklist, declares PR08 a pass and authorizes local merge;
[acceptance is user-reported](docs/evidence/pr-08/user-acceptance-001.md), not
independently measured or inferred from native tests. No worksheet was supplied.
See [PR08](docs/PR08_HOST_INTEGRATION.md) and its [Logic checklist](docs/PR08_LOGIC_CHECKLIST.md).

**PR09 implementation**, now merged locally as a negative qualification, adds opt-in local
session metadata logging and controlled full-AU timing/allocation screens in
product **0.4.0**, without changing musical DSP/state. Actual 30-minute Logic soak,
independent listening/rubric and final studio qualification are not claimed from
engineering tests. See [PR09](docs/PR09_STUDIO_SESSION.md).

PR07 added the auditioned
Rubber Band worker path to the original `voxide` AU: native key/scale and three
degree/octave/level/enable controls, aligned original level and 100 ms latency.
The user explicitly approved advancing after manual Logic/listening acceptance,
while **deferring, not passing, formal measured qualification**. Existing failures
and accuracy requirements stand. Playback and offline bounce use the same studio
path at 44.1/48 kHz; MIDI synthesis/live monitoring remain deferred. See [PR07](docs/PR07_PRODUCT_INTEGRATION.md).
The separate [evaluation AU](docs/PR06B_EVALUATION_AU.md) and original artifacts
are retained unchanged. No automatic installation, host operation or playback.

## Historical milestones and retained outcomes
PR 00 establishes builds and the AU; PR 01 adds routing diagnostics and native
automated checks, with a separate human-operated Logic checklist. Nothing here
demonstrates professional vocal quality or acceptable live-monitoring latency.

PR 02 adds offline evaluation fixtures and measurement/corpus tooling. Its original
±24-semitone contract/results are preserved as historical baselines; they are not
silently regraded against the new first-milestone scope. At that milestone no
product pitch shifter was integrated. Human reference/listening approvals remain separate.

PR 03 adds two causal YIN variants, 41 built-in 12-TET scale sets plus custom pitch
classes, all roots, independent degree/octave offsets, and sustained absolute-MIDI
targets. Tracking response requirements are **not met**; real-vocal accuracy and
Logic/live monitoring remain unqualified. See [tracking research](docs/TRACKING.md).

PR 04 adds **isolated** Signalsmith/Rubber Band evaluators, oracle-controlled file
renders and honest quality/timing/allocation comparisons. At that milestone neither
dependency was linked into the AU or Standalone. Candidate failures are retained, not product
passes; no engine is selected. See [engine comparison](docs/ENGINE_EVALUATION.md).

PR 05 adds an isolated three-voice interaction processor: oracle/live/scale/MIDI
ablations, fixed-deadline delivery, direct/aligned lead stems, and a common
consonant-policy comparison. At that milestone the product AU remained dry; no
engine or treatment was selected. See [interaction research](docs/INTERACTION_EVALUATION.md).

The subsequent [bounded architecture investigation](docs/ARCHITECTURE_INVESTIGATION.md)
found a faster schedule but no configuration meeting live timing, quality and
safety together. That combined-scope no-go remains. The user's subsequent
2026-10-24 decision prioritizes a separate studio milestone; it does not select
an engine or erase quality/safety failures.

The artistic reference is Brian Eno's **“Bottomliners,” 1:30–2:00**, primarily its
processed vocal character, not exact harmony notes or a verified hardware recipe.
That direction led to **PR06A: a development listening prototype**, followed by
**PR06B: formal studio qualification** and its separate evaluation AU. PR07 now has
the explicit sequencing approval above; formal qualification remains deferred.
The private preview has not
been auditioned by the assistant; formal private preflight is unchanged and no
album audio has been copied here.
See [the current plan](docs/PROJECT_PLAN.md) and
[the recorded direction](docs/DECISIONS.md#studio-first-direction--user-clarification-2026-10-24).
The [PR06A pilot protocol](docs/STUDIO_PILOT.md) names two existing candidates and
versions the listening/scope documents. The user explicitly approved excerpt a
in diagnostic C major for a listening-only comparison without pitch annotations.
The metadata command still cannot render/play audio; a separate receipt-gated
renderer must pass safety checks before exporting any local preview. No automatic
playback, formal pitch grade or product acceptance is implied. The approved
comparison is now available under ignored
`evaluation/pr-06a/listening-20261024T151731Z-aecf92a7/previews/`; both candidates
passed export checks. Initial user feedback is positive, with a Rubber Band
preference, a seemingly small difference and no distracting artifacts reported on
this comparison. Formal qualification/engine selection remain pending, and Rubber
Band callback allocations remain a failed product gate. See the pilot note
for the two mix filenames, validation and manual low-volume listening guidance.
The subsequent fixed synthetic engineering comparison favors Signalsmith 2048/512
for further tests: lower observed callback cost and no callback allocations. Both
engines pass stopped-reconstruction/repeat checks in that set; Rubber Band still
allocates during callbacks. This is a provisional engineering lead, not product
selection or Logic qualification. The user has separately approved clip c under
the same diagnostic C-major listening-only settings; it uses a new source-bound
receipt, not the consumed excerpt-a approval. Its initial comparison is withheld:
Signalsmith passes export checks, while the Rubber Band mix exceeds the conservative
preview-level ceiling without observed digital full-scale overs. The user has now
approved a separate common half-level export of the retained comparison, without
DSP rerender or changed relative mix. Its nine validated previews are ready at
`evaluation/pr-06a/playback-half-20261024T183809Z-647c08bb/previews/`. Manually listen
at low volume to `00-dry.wav`, `signalsmith-2048-512-mix.wav` and
`rubberband-r3-short-mix.wav`; report preference and timestamped articulation/bend
or note defects. Clip-c feedback again slightly favors Rubber Band, but the user
finds the difference minimal and non-decisive for choosing an engine. Signalsmith
was the provisional engineering lead before the subsequent pitch failures below;
it is not selected. The original
withheld result stays unchanged; no formal quality decision is implied. See the
pilot note for evidence and limitations.
The [bounded verification](docs/STUDIO_VERIFICATION.md) has now run: meter
calibration passes 36/36 fixtures, but matched prescribed/tracked output-pitch
checks fail in 34/72 native cases despite correct controls. **PR06A remains
incomplete; formal qualification is not passed.** The approved evaluation-AU and
PR07 sequencing exceptions do not regrade those results. A3 is stopped under the approved rule.
See [the results](docs/STUDIO_VERIFICATION_RESULTS.md). No private vocal repeats
or Logic/PDC tests were performed; those remain separately approval-gated.
All five tooling review findings are now fixed and independently closed, with
165 Python/full-product checks passing. See the
[repair record](docs/evidence/pr-06a/review-fixes-001.md). The completion drivers pass
186 Python/full-product checks; this does not turn failing DSP results into passes.
No engine choice or additional tuning/retest is inferred from the listening preference.
The subsequently approved [wrapper audit](docs/evidence/pr-06a/wrapper-audit-001.md)
found no justified correction. The current configuration is rejected for the
retained requirements; no speculative rerender was made.
The separately approved [Rubber Band allocation diagnosis](docs/evidence/pr-06a/rubberband-allocation-diagnosis-001.md)
also rejects its tested workaround: silent preparation removes allocations but
changes output timing/waveforms. Both direct-callback configurations remain
blocked; a worker-owned feasibility prototype needs an explicit architecture decision.
That isolated prototype was subsequently **approved on 2026-10-25** and is now
implemented under a [fixed synthetic protocol](docs/evidence/pr-06a/worker-feasibility-001.json).
Its normal tests now demonstrate **zero callback allocations, exactly unchanged
audio and 100 ms software alignment** at both rates/buffers. The overall timing
screen still fails one first-callback dispatch deadline in a fault test; it is not
waived. See [the results](docs/evidence/pr-06a/worker-feasibility-001.md). Musical/
host qualification and PR06A completion remain open. Product implementation is now
separately authorized under the explicit PR07 exception above.

## Local development

Requires Apple Silicon, macOS 15+, a macOS SDK/Clang (Command Line Tools), CMake
3.24+, Git, and Python 3.9+. Use the existing checksum-pinned JUCE 8.0.15 and
Rubber Band archive cache; default product commands are now offline and fail if it
is absent. PR10 does not authorize downloads, package installs or new dependencies.
No paid SDK, signing membership, Python package, or Nitride checkout is required.

```sh
make check
make check-full
make routing-check
make evaluation-check
make tracking-check
make engine-check        # separate cached native engine checks and oracle matrix
```

Checks do not install plug-ins, launch Logic, access the microphone, or change
audio devices. `make build PROFILE=release` builds the AU and development-only
Standalone app without opening either. See [Contributing](CONTRIBUTING.md).

Use the verified local cache offline:

```sh
python3 scripts/check.py --full --offline
```

To include historical PR04 synthetic checks in the same full source-snapshot
check, add `--engines` only with the existing cached evaluator archives. For the
current product's clean committed local-clone four-profile reproduction instead:
`python3 scripts/local_handoff.py reproduce --cache "$PWD/.cache/dependencies"`.
Neither path authorizes private research or changes a historical qualification.

## Explicit local AU install

With no Voxide session active, run:

```sh
make reload-au
```

This builds Release, copies only `voxide.component` into
`~/Library/Audio/Plug-Ins/Components`, ad-hoc signs it, and runs `auval`.
No Developer ID or notarization is involved. Unknown or edited existing components
are refused; recognized previous builds are preserved outside the AU scan directory
in `~/.local/state/voxide/backups/`.

The identity is `aumf / Vx00 / Vxid`, bundle `com.voxide.audio.voxide`.
Logic is expected to expose it under **AU MIDI-controlled Effects** in an instrument
slot. User testing supports direct physical-input monitoring and project recall;
the track-fed route goes silent with Low Latency Mode. See the recorded limitations
in [routing validation](docs/ROUTING_VALIDATION.md), not a blanket compatibility claim.

Choose **Vocal source: Main input** (default) or **Sidechain** explicitly. The product
sends channel 1 of that bus to both outputs, including in bypass. A stereo source's
second channel is deliberately ignored. A selected silent/disconnected sidechain
produces silence, not automatic fallback: JUCE's AU wrapper enables both buses, so
enablement cannot identify a connection. The user's Logic captures deliver audio
on Main while Side remains silent, despite selecting a source in Logic's Side Chain menu.
All musical/source parameters are saved in plug-in state; legacy shell states load
with musical defaults. Current scale mode generates three worker-owned harmonies;
MIDI synthesis/live monitoring remain deferred. The historical routing diagnostic
log stops when the editor closes. PR09's separate opt-in **session metadata log**
continues with the editor closed and must be stopped explicitly; neither logs PCM.

For reversible removal, quit Logic yourself and explicitly run
`python3 scripts/au.py uninstall --allow-uninstall`. Only the exact owned component
and ledger move outside AU discovery; all bytes/backups and unrelated plug-ins
remain. Unknown/edited installs are refused. See the handoff guide for recovery.

## Routing development loop

Use `make routing-check` rather than scripting Logic's UI. It runs the actual built
AU in a device-free native host plus production-processor/tooling tests and saves
a machine-readable report under `build/routing-checks/`.

Use `make routing-fixtures` to create a new private WAV/MIDI probe kit, then follow
the [manual Logic checklist](docs/LOGIC_ROUTING.md) when convenient. Native success
does not claim Logic monitoring, Low Latency Mode, or project recall acceptance.

## License and project boundaries

The user chose **local-only use for now**, using JUCE's AGPLv3 option with no
commercial license. Current product also links pinned Rubber Band under
GPL-2.0-or-later. This is not a public distribution setup. Before sharing any
source/binary, review the applicable license and corresponding-source/notice
obligations; no proprietary distribution entitlement is implied.

- [Third-party terms and pins](THIRD_PARTY_NOTICES.md)
- [Decisions](docs/DECISIONS.md)
- [Validation and evidence](docs/VALIDATION.md)
- [Independent review and fixes](docs/CODE_REVIEW.md)
- [Routing diagnostics and manual Logic acceptance](docs/LOGIC_ROUTING.md)
- [Evaluation tooling, corpus and measurement protocol](docs/EVALUATION.md)
- [PR-by-PR project plan](docs/PROJECT_PLAN.md)

`../nitride` is a read-only reference for engineering conventions, never a build
dependency. No Nitride code, assets, identity, or private evaluation data is copied.
