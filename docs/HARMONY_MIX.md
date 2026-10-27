# Harmony mix — product 0.5.0

The user reported harmonies too quiet relative to the original and requested a
mix control. The editor now has a prominent **Mix: Original ↔ Harmonies** slider
above the musical controls. Try **75–90%** for stronger harmonies relative to the
lead; **100%** removes the original. Individual voice enables/trims stay intact.

## Gain law and compatibility

- **0%:** aligned original only, at its existing trim.
- **50% (default):** exactly the previous original-plus-harmonies blend.
- **75%:** original gain halved (about −6 dB), harmonies unchanged.
- **100%:** harmonies only.

This is a centre-unity balance: `dry = min(1, 2*(1-mix))`,
`wet = min(1, 2*mix)`, where `mix` is normalized to 0–1. It makes harmonies more
prominent by reducing the lead, not by adding gain to a potentially clipping sum.
The existing one-third gain per harmony, independent dB trims and 10 ms output-time
ramps remain. There is no limiter, normalization, extra latency or promise of
constant perceived loudness as pitch/content/active voice count changes. Host bypass
still returns the unity aligned original, regardless of Mix or trims. Wet-only
with inactive/faulted harmonies can be silent; a fault is not a passing render.

**Original trim** remains available below the voice controls; it multiplies the
Mix original gain. Each **Voice trim** multiplies its contribution to the wet group.
Mix is one genuine automatable/saved host parameter (`harmonyMix`, version hint 4),
not a UI macro that rewrites all the existing trims. Output-time changes are
callback-granular and smoothed, like the existing levels.

The previous 30 host parameter IDs/order/defaults/ranges/version hints stay intact;
Mix is appended as parameter 31. State is now `voxide-studio-v5`. Product v4 states
load with Mix at 50%, preserving the previous sound. Tracking-v3/shell-v1/v2 states
retain their dry-only migration. A v5 state should not be expected to load in an
older binary. Reopen/recall must update Mix without the editor rewriting automation.

Build/test/use remain local and offline. No actual AU installation, `auval`, Logic,
audio device, playback or private-source access is automatic. Existing engine,
scale/range/latency requirements and PR09's unresolved variable-block failure and
negative studio qualification remain unchanged. This change is a mixing/UI fix,
not a new measured vocal-quality or studio-qualification pass.

Validation and exact built-candidate evidence:
[implementation-001](evidence/harmony-mix/implementation-001.md).

If a prior `make reload-au` installed 0.5.0 but validation still saw 0.3.0, the
updated helper now refreshes Voxide's bundle timestamp and retries stale-version
validation automatically. See [the reload repair](evidence/harmony-mix/reload-001.md).
