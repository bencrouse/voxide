# voxide

A vocal harmonizer project for Logic Pro, intended to keep the original lead and
generate three harmony voices with key/scale and MIDI control.

**Currently only a pass-through shell. No pitch tracking or harmonies yet.**
PR 00 establishes builds, tests, and an AU music-effect component. Nothing here
demonstrates professional vocal quality or acceptable live-monitoring latency.

## Local development

Requires Apple Silicon, macOS 15+, a macOS SDK/Clang (Command Line Tools), CMake
3.24+, Git, and Python 3.9+. The initial download is checksum-pinned JUCE 8.0.15.
No paid SDK, signing membership, Python package, or Nitride checkout is required.

```sh
make check
make check-full
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
slot. Actual Logic routing and monitoring are **PR 01 validation, not yet proven**.

Choose **Vocal source: Main input** (default) or **Sidechain** explicitly. The shell
sends channel 1 of that bus to both outputs, including in bypass. A stereo source's
second channel is deliberately ignored. A selected silent/disconnected sidechain
produces silence, not automatic fallback: JUCE's AU wrapper enables both buses, so
enablement cannot identify a connection. PR 01 must prove which bus Logic routes.
The source choice is saved in plug-in state; MIDI is accepted but ignored, with no
MIDI output. This routing control is not a harmony feature.

## License and project boundaries

The user chose **local-only use for now**, using JUCE's AGPLv3 option with no
commercial license. This is not a public distribution setup. Before sharing any
source/binary, review the applicable license and corresponding-source/notice
obligations; no proprietary distribution entitlement is implied.

- [Third-party terms and pins](THIRD_PARTY_NOTICES.md)
- [Decisions](docs/DECISIONS.md)
- [Validation and evidence](docs/VALIDATION.md)
- [Independent review and fixes](docs/CODE_REVIEW.md)
- [PR-by-PR project plan](docs/PROJECT_PLAN.md)

`../nitride` is a read-only reference for engineering conventions, never a build
dependency. No Nitride code, assets, identity, or private evaluation data is copied.
