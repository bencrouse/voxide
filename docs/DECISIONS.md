# Voxide decisions

## PR 00

- **Budget/license:** user explicitly chose local-only use for now in the licensing
  clarification. Use JUCE's AGPLv3 option; do not buy a license or publish binaries/
  source. Revisit obligations before sharing. No broad Voxide publication license
  is declared by this bootstrap.
- **Profile:** native arm64, macOS 15 deployment, C++20, CMake 3.24+, JUCE 8.0.15
  matching the inspected Nitride pin. This is a build profile, not certification
  that macOS 15 or all Apple Silicon devices have been tested.
- **Identity:** product `voxide`, version `0.0.1`, bundle `com.voxide.audio.voxide`,
  AU type `aumf`, subtype `Vx00`, manufacturer `Vxid`. Not Nitride's identity.
- **Signal contract:** default mono main input, optional disabled-by-default
  mono/stereo sidechain, stereo output. Stereo main input is also accepted for host
  compatibility. Explicit `sourceBus` choice selects Main input (default) or Sidechain;
  channel 1 is the mono source in normal and bypass processing. Do not infer a
  connection from enablement or signal level: AU enables every bus. Explicit
  zero-latency pass-through; no harmony generation or MIDI response yet.
- **State:** shell-v2 persists the routing choice; the previous stateless shell-v1
  restores the safe Main input default. Unknown/malformed state leaves the current
  choice unchanged. Parameter ID `sourceBus`, version hint 1, values Main/Sidechain
  (normalized 0/1); installed AU reported numeric ID `449045605`. Retain its meaning
  in later product work.
- **Targets:** AU product shell, development Standalone, independent DSP target,
  shared actual processor tests. No installed-host or Logic behavior inferred from
  processor tests; Logic proof belongs to PR 01.
- **Dependencies:** own verified archive cache plus explicit clean checkout option.
  Extracted source must match an archive-derived content manifest on every configure;
  mismatches preserve local edits and require a fresh tree. No sibling dependency
  discovery. Python evaluation packages and DSP engines are
  deferred to their scoped PRs; standard-library scripts need no package lockfile.
- **Safety:** no install/device access in ordinary checks. Explicit installer
  requires matching identity/ownership, refuses edited bundles/symlinks, preserves
  previous owned builds, revalidates after signing, and uses Darwin exclusive renames.
  Conflicting external changes are preserved rather than deleted during rollback.
  No paid signing/notarization. Standalone microphone privacy metadata supports a
  future explicit/manual capture test; no device is opened by ordinary checks.
- **Scope:** use Nitride as a read-only reference, not copied code. Minimal editor
  labels the build as a shell and exposes only the necessary routing choice; no
  new musical features or harmonizer claims.
