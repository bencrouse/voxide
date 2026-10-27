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

## Static safety, license, cost and preservation audit

- Standalone Python suite: **275/275 pass** (245 existing + 17 uninstall + 13
  local-handoff tests). Test roots/signers are synthetic; printed private-style
  paths belong to temporary fixtures, not the user's recordings.
- Exact preserved PR09 `ready-20261026-02` candidate/artifact passes the local
  signature/arm64/system-linkage/symbol/layout/file-hash and evidence-index check:
  `build/pr-10-checks/20261026T201638Z-b7bb59c7/report.json`.
- `build/pr-10-audit/before-002/` verifies **nine manifests / 2,674 file entries**:
  all eight ready PR06B/07/08/09 deliveries (2,425 entries) plus the earlier PR06B
  archive (249). The first attempted generic verifier refused the oldest manifest's
  missing schema field; no bytes were changed. The compatibility audit checks the
  exact file set/hashes without rewriting historical schemas or regrading results.
- `build/pr-10-audit/static-001/` records the existing cache's two product archive
  SHA-256s and exact in-archive license/build-material hashes: JUCE `LICENSE.md`,
  Rubber Band `COPYING`, `README.md`, `COMPILING.md`, `single/RubberBandSingle.cpp`.
  Full original archives remain locally retained, including complete notices and
  hidden source inventories. The fresh build separately verifies extracted trees.
- Source/DSP, evaluation/reference/worker engines, CMake pins/dependency wiring and
  prior tracked PR06A–09 evidence match `ef80f07`. No new dependency, upstream patch,
  package install, download, purchase, paid signing/notarization, upload or push.
  New expenditure **0**. Current product linkage is JUCE AGPLv3 plus Rubber Band
  GPL-2.0-or-later; public/proprietary distribution remains **not cleared**.
- No actual installed-AU validation/uninstall, Logic/device/playback operation,
  private recording read/render, consumed-claim reuse or historical timing/corpus
  rerun. Private evidence remains unavailable without new source-bound consent.

## Execution and delivery

Clean committed build source: `7207af726d55cefe58b9f24f7a3512adcc2bad0a`;
Git tree `cca9352f98b541ef1df0032e69f77b2cf91c3f34`. Execution:
`build/pr-10-reproduction/final-001/`. Local-clone checkout hooks disabled, no
hardlinks/submodules, verified existing cache, every configure explicitly offline.

| Profile | CTest | Python tooling |
| --- | --- | --- |
| Release | **11/11 pass** | **275/275 pass** |
| Debug | **11/11 pass** | **275/275 pass** |
| ASan | **4/4 pass** | Not rerun in focused selection |
| TSan | **4/4 pass** | Not rerun in focused selection |

ASan uses `detect_leaks=0:halt_on_error=1`; TSan uses `halt_on_error=1`. These are
functional/safety tests, not performance observations. No timing screen was rerun.
Existing local toolchain: arm64 macOS 27.0.1, Apple Clang 21.0.0, SDK 27.0,
CMake 4.4.3, Python 3.13.16; macOS 15.0 deployment target is not a claim of a
separate macOS 15 runtime test. Checkout and cache were verified unchanged on exit.

Additional exact fresh Release check:
`build/pr-10-checks/final-host-001/` passes 14 native AU functional cases plus
distinct save/reopen processes with byte-identical finite non-silent generated
audio/state checks. The report explicitly records build-only operation, no installed
`auval`, no Logic and no private recordings. Its pending actual-session fields do
not revoke PR08's historical user acceptance or invent new PR09/10 acceptance.

Signed 0.4.0 Release binary SHA-256:
`c4c156e1cd034b1b2b1b862aa719424a23bd5f9b60ad62fb848dd4164e6a0006`.
No post-test rebuild or re-sign is used for delivery. The preserved component is
`build/pr-10-artifacts/ready-20261026-01/voxide.component`; its sibling
`artifacts.json` binds the exact file set. It retains committed build-source and
final handoff-source snapshots, native harness, four-profile logs/build metadata,
synthetic host-check output, audit records and the complete two pinned dependency
archives. Final handoff changes after the build checkpoint are **documentation
only**; both source identities are recorded, not presented as the same Git tree.
The original checkout/builds are also retained.

Post-validation audit `build/pr-10-audit/after-001/preservation.json` confirms all
nine historical manifests / 2,674 entries, pinned archives and protected sources
unchanged. `main` remains `ef80f07`; no merge or push is performed.

## Final go / no-go and next-agent handoff

- **PASS — implementation:** reproducible local build/use/evidence guide,
  explicit exact-component installation, safe reversible uninstall, negative
  qualification report, zero-spend/license/privacy audit and scoped evidence index.
- **PASS — synthetic engineering:** fresh four-profile tests and exact signed
  build-only identity/reference/bounce/recall checks. Prior failures are retained.
- **FAIL / NO-GO — qualified studio milestone:** unresolved original 44.1 kHz
  variable-block wet-output failure. The root cause is still unestablished; cheap
  failed/dry callbacks are not three-harmony performance evidence. Old v1 passing
  observations cannot be promoted into corrected-v2 passes.
- **PENDING — actual operations and acceptance:** exact PR10 installed-AU checks,
  actual Logic soak/whole-host timing/allocation evidence, independent listening/
  revised rubric, formal full-support accuracy and challenge c, final studio/user
  acceptance and licensing/distribution clearance. No gate is waived or fabricated.
- **NOT AUTHORIZED / NOT PERFORMED:** public release, proprietary distribution,
  upload/push/merge, new purchases/downloads/packages/engines/upstream patches,
  automatic actual installed operations or private-recording access/replay.

PR10 implementation is complete as a **local engineering / negative-qualification
handoff**, not a successful studio qualification or final merge acceptance.
At this original closeout, independent PR10 review had not been requested or
claimed. The subsequent user-requested [review](review-001.md) and
[repairs](review-fixes-001.md) are separate follow-up evidence. Stop here for the user:
do not start new DSP research, rerun failed/consumed studies, demand a repeated
PR08 audition, or operate their installed AU/Logic/private sources automatically.
