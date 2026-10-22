# voxide

A vocal harmonizer project for Logic Pro, intended to keep the original lead and
generate three harmony voices with key/scale and MIDI control.

**Currently only a pass-through shell. No pitch tracking or harmonies yet.**
PR 00 establishes builds and the AU; PR 01 adds routing diagnostics and native
automated checks, with a separate human-operated Logic checklist. Nothing here
demonstrates professional vocal quality or acceptable live-monitoring latency.

PR 02 adds offline evaluation fixtures and measurement/corpus tooling. The numerical
target now includes ±24-semitone shifts; no pitch shifter has been implemented or
qualified. Human corpus/annotation/listening approvals remain separate gates.

## Local development

Requires Apple Silicon, macOS 15+, a macOS SDK/Clang (Command Line Tools), CMake
3.24+, Git, and Python 3.9+. The initial download is checksum-pinned JUCE 8.0.15.
No paid SDK, signing membership, Python package, or Nitride checkout is required.

```sh
make check
make check-full
make routing-check
make evaluation-check
```

Checks do not install plug-ins, launch Logic, access the microphone, or change
audio devices. `make build PROFILE=release` builds the AU and development-only
Standalone app without opening either. See [Contributing](CONTRIBUTING.md).

After the first dependency download, use the verified local cache offline:

```sh
python3 scripts/check.py --full --offline
```

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
The source choice is saved in plug-in state. MIDI is observed for diagnostics but
does not generate sound or MIDI output. The editor's optional local metadata log
contains bounded audio/MIDI summaries, not PCM; logging stops when the editor closes.
These are development diagnostics, not harmony features.

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
