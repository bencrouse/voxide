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

## PR 01

- **Workflow:** user approved ending scripted Logic UI operation. Native built-AU
  and production-processor tests are the development loop; a reusable human Logic
  checklist is separate acceptance. No automatic project generation, DAW launch,
  recording, UI permission changes, or actual hardware input in ordinary checks.
- **Diagnostics:** version 0.1.0 / routing-003, fixed 2,048-record SPSC queue and at
  most 64 inspected MIDI records/three bytes each per callback. Consumer-side JSONL
  writing is opt-in, local/ignored, stops on editor close, and is never persisted.
  Retain original sample offsets (including invalid values) rather than normalize
  bad host data into apparently valid evidence. Loss/unknown note state is explicit.
- **Identity/state:** `sourceBus` and shell-v2 persistence remain unchanged. Render
  epochs reset on prepare/reset; observed held-key diagnostics also clear on
  stop/seek discontinuities. UUID identifies
  the current processor instance and is not serialized. No harmony synthesis added.
- **Evidence:** actual AU tests can assert buffer routing, host-callback use,
  fresh-instance state and MIDI API acceptance. Exact delivered MIDI offsets are
  asserted in the production processor, not falsely reported as observed inside
  the opaque native AU. Logic delivery still needs a real capture.
- **Host gates:** no microphone capture occurred; no live external controller was
  available. Musical Typing is a labeled manual alternative, not hardware qualification.
  The abandoned automation reached only an unsaved empty project's New Track sheet.
  No project file, recorded vocal, Low Latency Mode result, or recall result exists.
- **Discovery:** initial `auval` returned success while reporting cached 0.0.1 for
  the installed 0.1.0 bundle. This is not a discovery pass; validation now checks
  the reported version. No broad cache reset/registrar kill is permitted.
- **Review hardening:** stage MIDI only on the consumer until its matching audio
  summary; report/discard a partial tail at capture stop. Use checked unbuffered
  JSONL writes to detect short writes. Include prior truncation counts in MIDI
  records. Analysis has explicit note-pair and final-release requirements rather
  than treating arbitrary MIDI traffic as evidence of note-on/off delivery.
