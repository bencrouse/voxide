# voxide

A vocal harmonizer project for Logic Pro, keeping the original lead and generating
three harmony voices. **Current priority: recorded vocals, scale mode, inclusive
±12-semitone support and an intentionally processed vocal character.** Live use,
MIDI-mode qualification and ±24 coverage are deferred, not achieved or cancelled.

**The product AU remains dry pass-through. A separate, uninstalled
[PR06B evaluation AU](docs/PR06B_EVALUATION_AU.md) now builds with audible harmonies**
on `pr-06b-evaluation-au`: explicit key/scale, three fixed scale-derived voices,
unchanged aligned lead and 100 ms declared latency. It is real-time playback only,
locally ad-hoc signed and unqualified—not product acceptance or a PR07 merge.
See the linked document for its build path, limitations and focused test results.
PR 00 establishes builds and the AU; PR 01 adds routing diagnostics and native
automated checks, with a separate human-operated Logic checklist. Nothing here
demonstrates professional vocal quality or acceptable live-monitoring latency.

PR 02 adds offline evaluation fixtures and measurement/corpus tooling. Its original
±24-semitone contract/results are preserved as historical baselines; they are not
silently regraded against the new first-milestone scope. No product pitch shifter
is integrated or qualified. Human reference/listening approvals remain separate.

PR 03 adds two causal YIN variants, 41 built-in 12-TET scale sets plus custom pitch
classes, all roots, independent degree/octave offsets, and sustained absolute-MIDI
targets. Tracking response requirements are **not met**; real-vocal accuracy and
Logic/live monitoring remain unqualified. See [tracking research](docs/TRACKING.md).

PR 04 adds **isolated** Signalsmith/Rubber Band evaluators, oracle-controlled file
renders and honest quality/timing/allocation comparisons. Neither dependency is
linked into the AU or Standalone. Candidate failures are retained, not product
passes; no engine is selected. See [engine comparison](docs/ENGINE_EVALUATION.md).

PR 05 adds an isolated three-voice interaction processor: oracle/live/scale/MIDI
ablations, fixed-deadline delivery, direct/aligned lead stems, and a common
consonant-policy comparison. The product AU remains dry; no engine or treatment
is selected. See [interaction research](docs/INTERACTION_EVALUATION.md).

The subsequent [bounded architecture investigation](docs/ARCHITECTURE_INVESTIGATION.md)
found a faster schedule but no configuration meeting live timing, quality and
safety together. That combined-scope no-go remains. The user's subsequent
2026-10-24 decision prioritizes a separate studio milestone; it does not select
an engine or erase quality/safety failures.

The artistic reference is Brian Eno's **“Bottomliners,” 1:30–2:00**, primarily its
processed vocal character, not exact harmony notes or a verified hardware recipe.
Current phase is **PR06A: a small, safely prepared development listening prototype**,
followed by **PR06B: formal studio qualification** if warranted. AU integration
remains blocked until an explicit studio go-decision. The new preview has not
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
checks fail in 34/72 native cases despite correct controls. **PR06A is blocked;
formal qualification/product go remain blocked.** The separately approved
evaluation-AU exception does not waive those gates. A3 is stopped under the approved rule.
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
host qualification, PR06A completion and product integration remain gated.

## Local development

Requires Apple Silicon, macOS 15+, a macOS SDK/Clang (Command Line Tools), CMake
3.24+, Git, and Python 3.9+. The initial download is checksum-pinned JUCE 8.0.15.
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

After the first dependency download, use the verified local cache offline:

```sh
python3 scripts/check.py --full --offline
```

To include PR 04 in the same full source-snapshot check, add `--engines`. On first
use only, explicitly acquire the three free pinned evaluator-source archives:
`python3 scripts/engine_dependencies.py --destination build/engine-release/_deps`.
No pip/Homebrew package, paid license, AU installation or audio-device access is
needed. Subsequent `make engine-check` runs offline from that verified cache.

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

Choose **Vocal source: Main input** (default) or **Sidechain** explicitly. The shell
sends channel 1 of that bus to both outputs, including in bypass. A stereo source's
second channel is deliberately ignored. A selected silent/disconnected sidechain
produces silence, not automatic fallback: JUCE's AU wrapper enables both buses, so
enablement cannot identify a connection. The user's Logic captures deliver audio
on Main while Side remains silent, despite selecting a source in Logic's Side Chain menu.
All musical/source parameters are saved in plug-in state; legacy shell states load
with musical defaults. MIDI controls target decisions but generates no sound or
MIDI output. The editor's optional local metadata log
contains bounded audio/MIDI summaries, not PCM; logging stops when the editor closes.
The editor exposes target controls and callback snapshots, not audible harmonies.

## Routing development loop

Use `make routing-check` rather than scripting Logic's UI. It runs the actual built
AU in a device-free native host plus production-processor/tooling tests and saves
a machine-readable report under `build/routing-checks/`.

Use `make routing-fixtures` to create a new private WAV/MIDI probe kit, then follow
the [manual Logic checklist](docs/LOGIC_ROUTING.md) when convenient. Native success
does not claim Logic monitoring, Low Latency Mode, or project recall acceptance.

## License and project boundaries

The user chose **local-only use for now**, using JUCE's AGPLv3 option with no
commercial license. This is not a public distribution setup. Before sharing any
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
