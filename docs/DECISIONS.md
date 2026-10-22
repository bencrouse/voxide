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
- **Host gates:** the agent's abandoned automation reached only an unsaved empty
  project's New Track sheet and performed no capture/monitoring. Subsequent user
  testing supports direct physical-input monitoring with Low Latency Mode off/on
  and save/quit/reopen; the track-fed mode limitation and remaining checks are in
  `docs/ROUTING_VALIDATION.md`. No external-controller qualification is claimed.
- **Discovery:** initial `auval` returned success while reporting cached 0.0.1 for
  the installed 0.1.0 bundle. This is not a discovery pass; validation now checks
  the reported version. No broad cache reset/registrar kill is permitted.
- **Review hardening:** stage MIDI only on the consumer until its matching audio
  summary; report/discard a partial tail at capture stop. Use checked unbuffered
  JSONL writes to detect short writes. Include prior truncation counts in MIDI
  records. Analysis has explicit note-pair and final-release requirements rather
  than treating arbitrary MIDI traffic as evidence of note-on/off delivery.

## PR 02

- **Numerical contract:** user accepted the plan's numerical targets on 2026-10-21,
  requesting **±24 semitones**, not the original ±12. E2–C6 input, 44.1/48 kHz and
  all three harmony voices remain required. Mathematical output endpoints are
  approximately 20.60–4,186.01 Hz. No automatic reduction if engines fail; no claim
  of achieved performance. Contract and reports are versioned/hashed.
- **Boundary:** only offline evaluation tooling, analytic assets and protocols;
  no production tracking, musical mapping, harmony synthesis or engine integration.
  Musical/source behavior and new listening/protocol details remain unapproved.
- **Dependencies/privacy:** standard-library Python only. No package installation,
  download, audio-library scan, recording, AU install or DAW automation. Private
  recordings/consent/reviewer identities never enter Git. The user offered resources
  but had not supplied locations, usage references or reviewer IDs at engineering
  qualification. Subsequently the user supplied three private AIFF pilots and
  explicitly approved local mono copies/excerpts. Original hashes and PCM samples
  are preserved. The user confirms one singer, solo and untuned; dry status remains
  provisional and actual reviewer IDs remain pending. See the private pilot intake
  record in `docs/EVALUATION_VALIDATION.md`.
- **Evidence:** candidate-independent analytic references; ordinary tests never
  rewrite them. Positive controls and deliberate pitch/octave/resonance/delay faults
  exercise measurements. PCM output is decoded before null comparison. Missing
  observations, all-uncertain references, missing listeners or corpus inputs cannot
  become a pass. Offline autocorrelation is not a live tracker or human pitch truth.
- **Holdout:** singer-separated splits, exact source/annotation/settings hashes,
  explicit complete-corpus/settings approval and opt-in access. Metadata QA is not
  candidate tuning; this is a workflow guard rather than file access security.
- **Independent review hardening:** v2 control/annotation metadata binds the source
  PCM/timebase; all 28 WAV bytes remain unchanged. Analytic burst/silence onset
  references were explicitly corrected under generator v2, not regenerated from
  candidate output. Shared contract policy governs grading and all holdout approval
  prerequisites; `pr02-contract-002` changes no approved numerical targets and
  leaves all outstanding protocol/resource approvals pending. See the review
  record and final qualification in `docs/EVALUATION_VALIDATION.md`.
- **Sequencing revision (2026-10-22):** user approved committing/merging PR 02's
  reviewed engineering foundation and deferring detailed manual annotations to
  actual tracker development. This explicitly permits PR 03 implementation without
  pretending the human gates passed. Numerical targets, independent reference/
  listening requirements, holdout locks and final qualification gates are unchanged;
  remaining musical semantics are not implicitly approved by this merge.

## PR 03

- **Approved musical defaults (2026-10-22):** user accepted scale third/fifth/octave
  defaults, continuous scale-source expression with hysteresis, absolute MIDI
  newest-three/stable-slot targets with repeat counts/sustain, inactive uncertain
  targets, unchanged lead and disabling rather than clamping out-of-range shifts.
  User additionally requested broad exotic scales. Implemented 41 built-in 12-TET
  sets plus any custom pitch-class set and all roots; do not claim microtonal/raga/
  maqam completeness. Octaves are independent of degree cardinality. See the
  versioned `docs/evidence/pr-03/musical-contract.json` and `docs/TRACKING.md`.
- **Algorithm boundary:** fixed-storage causal YIN baseline and bounded
  multi-candidate variant; no offline Viterbi, future context or correction of lead.
  Thresholds/hysteresis/window constants are engineering choices, not perceptually
  approved numbers. Multi-candidate is an experimental default, not a proven winner.
- **Research versus acceptance:** final candidate analytic stable-frame results do
  not establish actual vocal accuracy. Recognition timing misses remain architecture
  blockers. All permitted development vocals, including rhythmic/bending c, remain
  required and ungraded without human reference truth; no holdout or live-quality
  gate is unlocked. No new dependencies, purchase, install, recording or Logic use.
- **Engineering/research merge approval (2026-10-22):** after independent review,
  fixes, rereviews and full qualification, the user approved a local commit and
  merge of PR 03. Recognition timing misses and deferred reference/listening/Logic
  gates remain open; this is not architecture or product acceptance. Nothing is
  pushed or installed, and private evaluation data remains excluded from Git.
