# PR10 local engineering handoff — 001

Branch `pr-10-local-handoff`, based on merged PR09 `ef80f07`.
Outcome: **studio-first scale-mode engineering / negative-qualification handoff**.
Not qualified studio use, a public release, or completion of deferred live/MIDI/±24.

## Scope

- Concise [build/install/use/recall/bounce/uninstall guide](../../PR10_LOCAL_HANDOFF.md)
  and complete scoped [evidence index](handoff-index.json). Current requirements,
  functional/user-reported acceptance and failed/missing qualification are separate.
- Explicit recovery-preserving uninstall under the installer lock, with ownership,
  identity, inode/bytes/mode checks, no-clobber moves, rollback of known entries only,
  no recursive deletion and conservative manual recovery for uncertain collisions.
  Exact preserved-component install avoids an unwanted rebuild of a candidate.
- Local-only candidate/artifact identity verifier and clean local Git-clone,
  cache-only four-profile reproduction. No downloads, actual installed operations,
  Logic/devices/playback, private-source reads/renders, timing reruns or corpus sweeps.
- Corrected current product dependency inventory: the same pinned Rubber Band
  source is product-linked since PR07, not evaluator-only. No pin/upstream changes,
  new paid requirement, public/proprietary license grant or distribution clearance.

Original PR09 variable-block failure remains unresolved. V2 observation fixes do
not create new timing evidence. Actual Logic/whole-host/soak results, independent
final listening and revised PR06B rubric, full-support accuracy/challenge c and
licensing/final studio go remain open. PR08 user-reported acceptance stands without
another worksheet or repeated audition. No merged engineering result is regraded.

Execution, cache/license audit, preservation and final delivery evidence are
recorded below when completed. All real installed/user operations remain separate.
