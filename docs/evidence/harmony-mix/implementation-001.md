# Harmony Mix implementation — 001

Branch `fix-harmony-mix` from merged PR10 `cade436`, product **0.5.0**.
User requested louder harmonies relative to the original and a mix-style UI.
This is a mixing/UI follow-up, not a new studio-qualification result.

## Implementation

- Prominent native **Mix: Original ↔ Harmonies** slider, keyboard-accessible and
  attached to one genuine automatable/saved parameter. Individual trims are not
  rewritten. Centre-unity attenuation makes harmonies more prominent by reducing
  the original; no added wet gain, limiter/normalization or headroom requirement.
- 0% original only; 50% exact previous blend; 75% halves original gain; 100%
  harmonies only. Existing independent gains and 10 ms smoothing remain.
- Appended parameter 31 (`harmonyMix`, version hint 4), preserving the old 30
  IDs/order/defaults/ranges. State v5 reads v4 at centre, preserving sound; earlier
  dry-only state migrations remain. Host bypass still yields unity aligned lead.
- Existing local tooling recognizes 0.5.0 without relabeling 0.4.0 artifacts or
  granting qualification. No engine, pitch/scale/latency/range or dependency change.

## Execution

Final evidence `build/harmony-mix-validation/run-003/`: Release/Debug **11/11
each**, including **284 Python tests each**; focused ASan/TSan **4/4 each**.
No final build warnings/errors. Non-ignored source hashes stayed fixed during
execution; subsequent edits are documentation only. Builds use cached pins,
offline configuration and existing tooling. No package installs/downloads.

The initial `run-001` retained a failing UI regression: its comparison to a literal
−6 dB exceeded an overly exact tolerance after the existing normalized-float
conversion. The test now compares pre/post slider and host parameter values
exactly, proving Mix does not change the trim. No audio tolerance was relaxed.
`run-002` passed all profiles; `run-003` repeats final-source tests after replacing
raw floating-point equality with the project's explicit exact-comparison helpers.

Regressions cover mix endpoints/intermediates at both rates, unchanged trims,
10 ms gain ramps, bypass, allocation-free rendering, v4 migration/audio identity,
malformed-state refusal, v5/UI recall, host automation and exact-AU/reference
bounce/fresh-process recall with non-default Mix. Native UI snapshots at
720×680, 780×700 and 1000×840 pass bounds/gesture/lifecycle checks; minimum/default
captures were inspected visually without opening a window/device.

`build/harmony-mix-validation/host-001/` passes additional exact signed build-only
native/recall checks. Signed Release binary SHA-256:
`3b7c1248cf91c483f56fb1e6fe9c149f089680b2a6d54a22a7f57e4a03d0ef00`.
Exact bundle/source/log/hash delivery: `build/harmony-mix-artifacts/ready-001/`.
BuildInfo honestly reports the dirty parent revision; source manifests bind the
changed source rather than claiming the old commit contains these changes.

`build/harmony-mix-validation/protected-001/` verifies **11 previous manifests /
2,936 entries**, unchanged engines/pins and prior evidence. New expenditure zero.
No actual installation, installed auval, Logic/device/playback operation,
private-source read/render, historical timing/corpus rerun, merge or push.
PR09's variable-block failure and all outstanding qualification gates remain open.
