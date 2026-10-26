# PR08 — user-operated product Logic session

This checklist does not launch Logic, install anything, play audio or read a
recording. Create a **new disposable project yourself**; no generated `.logicx`
file is presented as a real saved/reopened project. The prior evaluation-AU manual
acceptance remains accepted; this session concerns product **voxide 0.3.0**, its
new controls/state and actual offline bounce, not a demand to repeat that audition.
PR08 itself is now user-accepted; this checklist remains its routing reference.
The current PR09-instrumented build is **0.4.0** and uses the same route. For new
session performance/soak work use [PR09_STUDIO_SESSION.md](PR09_STUDIO_SESSION.md),
not a demand to repeat accepted PR08 testing or complete its worksheet.

## 1. Establish exactly what is installed

Quit Logic before an explicitly chosen `make reload-au`. That command builds,
installs/signs only the product AU and runs its scoped `auval` validation. It does
not install Studio Eval. Rescan only voxide in Logic's Plug-in Manager if needed;
never delete broad AU caches. Confirm the requested candidate version (**0.3.0**
for the archived PR08 binary, **0.4.0** for the current PR09 build) and record installed binary
hash, Logic/macOS versions, rate and buffer settings in `worksheet.json`.

Optional installed-file API checks, only when you choose to authorize them:

```sh
python3 scripts/host_integration.py installed --build-dir build/local-release \
  --allow-installed-au --allow-auval
```

That verifies owned installed files and registry identity/version, then loads the
exact installed bundle for synthetic tests. It does **not** prove Logic loaded a
particular cached image or establish real Logic compensation.

## 2. Prepare the recorded-vocal route, not a live-input workaround

- Project 44.1 or 48 kHz; begin with I/O **128**, Process Buffer **Small**, PDC
  **All**, Low Latency Mode **Off**. Record these settings, not OS device defaults.
- Import the generated `first-sample-<rate>.wav` and `preroll-<rate>.wav` probes.
  They are controlled synthetic signals, **not vocal-quality evidence**.
- Product identity remains `aumf / Vx00 / Vxid`. If Logic lists it under
  **AU MIDI-controlled Effects**, use that route rather than assuming Studio Eval's
  ordinary-effect slot is equivalent. Route the recorded track through Logic's
  side-chain selector as appropriate, then explicitly select the delivered **Main
  input** or **Sidechain** in voxide. The selected-input meter must move.
- A silent selected source stays silent: no automatic fallback. Historical Logic
  track-fed/Low Latency Mode failure remains a limitation, not an accepted route.
- Hear only one lead: silence the source track's direct output while keeping its
  feed to the effect active. Verify that changing that routing does not cut the
  feed. Do not accept doubled lead, a bypassed effect or a silent instrument.
- Choose a recorded vocal you own **inside Logic** for musical/phrase checks;
  record physical input first. This does not authorize the agent to inspect,
  copy or render that recording. Any later agent-side analysis needs a new
  source-bound approval; old consumed receipts remain consumed.

## 3. Separate compensation from transformed audio

1. With all three voice enables **off**, Original **0 dB**, no other processing,
   render the unity reference from the same project range. The compensated
   original must align with the unprocessed source with **zero integer-sample
   offset**, max absolute error **≤1e-6**, RMS error **≤1e-7**. Retain actual
   measured numbers/exports; visual alignment alone is not that quantitative pass.
2. Enable all three voices and explicitly select key/scale. Confirm audible harmony
   processing, status ready, and three active targets during suitable voiced notes.
   Active target indicators alone do not prove each voice's audible contribution;
   solo by disabling the other voices if checking individual contributions.
3. Check source-time key/scale/degree automation against the passage it belongs to.
   Mixer levels/enables are output-time with a 10 ms gain ramp; simultaneous edits
   are not promised to affect the same source sample. Automation is callback-
   granular, not an advertised sub-block sample-accurate mode.
4. Do not use correlation/phase of a shifted vowel as an exact unity reference.
   First-syllable harmony onset/pitch and expressive bends require their own
   documented musical measurements; PDC does not excuse missing articulation.

## 4. Transport, recall and Low Latency Mode

- Exercise first-sample start and the pre-roll variant, mid-phrase start, cycle,
  forward/backward seek, stopped callbacks, resume, bypass, silence and reset.
  Check no prior phrase leaks and the original remains intact across harmony
  restart/recall. A real source/transport discontinuity discards old history.
- Save, close, quit Logic, reopen; duplicate the instance; reopen in a fresh Logic
  process. Record project hash/paths and settings/audio observations. A project
  file existing or a device-free native test is not proof Logic was reopened.
- Test Low Latency Mode Off/On separately. If it bypasses/mutes the recorded route,
  mark **unsupported in that setting**, not success. Keep Off as the initial
  supported restriction. Low Latency Mode is inactive during bounce.
- MIDI input/state safety remains regression-tested; MIDI synthesis, live keyboard
  qualification and chase are deferred. Unsent/chased events cannot be inferred.

## 5. Bounce the same deterministic passage

- Retain separate real-time and offline bounces: same project range, automation,
  sample rate, float format, no normalization/dither/hidden quality changes.
- Include the supplied **0.6 s tail** and compare duration, first syllable and tail
  coverage. Test at least the initial and a differing host render-block setting.
- Native tests establish exact functional parity in their synthetic cases, **not**
  an actual Logic bounce pass. Preserve differences; do not dynamically re-align,
  trim, gain-match or accept dry-only output as harmonized parity. Non-exact
  differences need measured explanation and independent listening before acceptance.
- Enter observations and evidence paths in the worksheet. Leave unperformed cases
  pending. Do not mark formal pitch/full-support, expressive challenge c,
  performance/soak or licensing gates passed from this checklist alone.
