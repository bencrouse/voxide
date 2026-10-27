# Local handoff — studio-first scale-mode milestone

**NO-GO for qualified studio use / public release.** This is a reproducible local
engineering handoff, not completion of the original live/MIDI/±24 brief. Product
0.4.0 is available for deliberately chosen local evaluation only. Both original
44.1 kHz variable-block screen repeats missed wet-output coverage; that failure is
unresolved. Corrected v2 observation logic was reviewed/tested, **not timed again**.
Actual Logic soak/whole-host evidence, independent final listening/rubric, formal
full-support accuracy/challenge c and distribution/licensing clearance remain open.

PR08's user-reported Logic pass remains accepted without requiring a worksheet or
the same audition again. It is not a PR09 performance/soak result. PR09 was merged
with explicit user authorization as a **negative-qualification engineering
milestone**, not as a passed studio qualification.

## 1. Build/check locally without spending or installing anything

Prerequisites are the already available arm64 Mac/macOS 15+ toolchain: Git,
CMake ≥3.24, Python ≥3.9 and Apple's command-line tools/SDK. No package manager,
paid license/account, new engine, notarization or signing service is required.
Preserve the existing pinned archives in `.cache/dependencies/`; if absent/corrupt,
offline configuration stops. Do not silently download, install packages or change
pins to make the build succeed.

From the checkout root:

```sh
cmake -S . -B build/local-release -DCMAKE_BUILD_TYPE=Release -DVOXIDE_OFFLINE=ON
cmake --build build/local-release --parallel 6
ctest --test-dir build/local-release --output-on-failure
python3 scripts/host_integration.py check --build-dir build/local-release
python3 scripts/local_handoff.py verify \
  --component build/local-release/voxide_artefacts/Release/AU/voxide.component
```

Normal checks use exact **uninstalled** bundles and generated signals, not Logic,
audio devices, playback or private recordings. Never launch the development
Standalone as an automated check. It is not a qualified monitoring route.
`make build`, `make check` and `make check-full` now explicitly select offline
dependencies. The full check script also contains historical synthetic research;
the fresh-checkout command below limits execution to the current CTest profiles.

The selected architecture is the existing causal tracker/explicit scale selector
feeding three independent worker-owned Rubber Band R3-short instances, with fixed
100 ms software alignment and an unchanged original path except declared gain/
alignment. No alternate engine or upstream patch is introduced. To locate the
synthetic reference/bounce comparisons without private recordings:

```sh
ctest --test-dir build/local-release --output-on-failure \
  -R '^(studio_reference|studio_native_reference|host_bounce|host_recall)$'
```

These compare generated-signal reference/processor/exact-AU behavior. They do not
replace a vocal-quality judgment or the original failed performance observation.

For a fresh **local Git clone**, no network, no discarded working changes:

```sh
# Requires a committed, clean working tree and the existing verified cache.
python3 scripts/local_handoff.py reproduce --cache "$PWD/.cache/dependencies" --jobs 6
```

This creates a new retained path under `build/pr-10-reproduction/`, clones local
Git objects without hardlinks/submodule recursion, disables Git hooks for checkout,
checks out the exact source commit, pins the existing **Unix Makefiles** generator
(even if `CMAKE_GENERATOR` names Xcode/Ninja Multi-Config), uses offline/cache flags,
and runs full Release/Debug plus focused ASan/TSan tests. It preserves failures and
logs; it never resets/deletes your source. Missing cache fails **before cloning**.
It does not rerun the PR09 timing screen, any private corpus or old consumed study.
Success means reproducible source/cache/build/functionality, **not qualification**.
Absolute build/log paths, toolchains and signatures mean bit-identical binaries
across different checkout locations are not promised.

## 2. Select exactly what you install — explicit user operation only

Quit Logic yourself. Choose either the current local Release build:

```sh
make reload-au
```

or an exact preserved component without rebuilding it:

```sh
python3 scripts/local_handoff.py verify \
  --component build/pr-10-artifacts/ready-20261026-01/voxide.component \
  --artifact build/pr-10-artifacts/ready-20261026-01 \
  --expected-sha256 c4c156e1cd034b1b2b1b862aa719424a23bd5f9b60ad62fb848dd4164e6a0006
python3 scripts/au.py install \
  --component build/pr-10-artifacts/ready-20261026-01/voxide.component
python3 scripts/au.py validate
```

These are instructions, **not authorization for the agent to execute installed
operations automatically**. The installer touches only owned `voxide.component`,
with `aumf / Vx00 / Vxid`, bundle ID `com.voxide.audio.voxide`; unknown/edited files
are refused, previous owned versions retained outside AU discovery. It does not
replace Nitride or Studio Eval. Signing is local ad-hoc, not notarized/public trust.
No broad AU-cache reset, process killing or automatic Logic launch is performed.

Inspect the emitted install report/ownership ledger and exact installed binary
hash. Re-signing/building can change identity; do not assume a newly rebuilt binary
has the preserved artifact's hash. `auval` identity/version is not cryptographic
proof of a cached image. If needed rescan **only voxide** in Logic's Plug-in Manager.
Optional installed exact-file/native checks require both explicit approvals:

```sh
python3 scripts/host_integration.py installed --build-dir build/local-release \
  --allow-installed-au --allow-auval
```

That command requires installed files to match the specified build; do not point
it at an unrelated build after installing a preserved component. It does not prove
actual Logic compensation or close PR09's negative qualification.

## 3. Recorded-vocal scale workflow and limits

- Start with a disposable recorded-vocal Logic project, PDC **All**, Low Latency
  Mode **Off**, I/O **128**, Process Buffer **Small**, 44.1 or 48 kHz. These are
  initial evaluation settings, not universal certified support or live monitoring.
- Product AU remains an **AU MIDI-controlled Effect** (`aumf`), not Studio Eval's
  ordinary-effect slot. Use its instrument/effect route and Logic sidechain selector
  as appropriate. Explicitly choose the delivered **Main input** or **Sidechain**
  in voxide. Selected-input meter must move; silent input has no automatic fallback.
- Keep one lead: remove the source track's direct output while preserving its feed
  to voxide (for example **No Output**, not a mute that cuts the feed). Confirm the
  feed remains active. Physical/live input must be recorded first; no zero-latency
  live-monitoring or MIDI-synthesis workflow is qualified.
- Choose **Key** and **Scale (12-TET)** explicitly. There is no key detection or
  lead tuning. Degree 0 = unison; +2 = a third in seven-note scales. Each of three
  voices has degree/octave/enable/level controls. Combined shifts outside inclusive
  **±12** or uncertain targets fade inactive, rather than clamp to a different note.
  Octave/UI ranges do not imply ±24 support. E2–C6/full ±12 remain requirements,
  not a completed measured accuracy claim.
- Original **0 dB** is unity with declared **100 ms** alignment (4410/4800 samples).
  Each harmony has fixed one-third mix gain plus explicit trim/enable; provide
  headroom. −60 dB is Off. No masking limiter/normalization is added. Selected source
  channel 1 is duplicated to stereo; there is no stereo-source downmix/panning claim.
- Musical controls are source-time, heard approximately 100 ms later; levels and
  enables are output-time with 10 ms ramps. Automation is callback-granular, not
  sub-block sample-accurate. Host bypass preserves aligned original; actual source/
  transport discontinuities clear history. A restart recovers harmonies without
  clearing queued original; missing-spare timeout faults require explicit restart.
- **Delivery fault** mutes harmonies while preserving finite original. Dry fallback
  is not a passing render. Low Latency Mode's known track-fed restriction remains;
  a bypassed/silent harmonizer is not success. LLM is inactive during bounce.
- Legacy MIDI state/delivery safety is regression-tested; MIDI synthesis/chase,
  live playability and ±24 musical qualification are deferred, not achieved. A host
  cannot reconstruct MIDI events it never sends.

## 4. Save/recall/bounce and opt-in session metadata

Use the [PR08 checklist](PR08_LOGIC_CHECKLIST.md) as the retained routing/PDC/recall/
bounce reference, not a demand to repeat its accepted audition. Save/close/quit/
reopen and duplication must not retain old voices. Real-time/offline bounces use
the same R3-short engine/quality/commands. Retain the same project range/automation,
rate/float format, no dither/normalization and the declared **0.6 s tail**. Do not
trim/re-align/gain-match differences into a pass. The frozen unity lead/PDC limits
remain zero integer offset, max error ≤1e-6 and RMS ≤1e-7; shifted-vowel phase is not
a unity reference. The known variable-block failure is not waived by this guide.

For further PR09 work follow [the session protocol](PR09_STUDIO_SESSION.md).
**Log session metadata** is an explicit local-only opt-in: bounded metadata, no
PCM/MIDI/source hashes/paths/pitch traces; it continues with the editor closed.
Stop explicitly before removing the instance/project. The processor-body timer
excludes wrapper/collector/IO and cannot prove whole-host timing/allocations or
dropout freedom. On-disk module hash does not prove a previously cached mapped
image. Captures with drops/aborts/malformed fields are invalid. No private log is
read by the agent without a new selected-file approval; that is not audio approval.
Observations may be provided in chat—**no manual JSON worksheet is required**.

## 5. Safe reversible uninstall

Quit Logic yourself, then explicitly run:

```sh
python3 scripts/au.py uninstall --allow-uninstall
# Equivalent explicit convenience target: make uninstall-au
```

No broad deletion occurs. Under the installer's exclusive lock the command verifies
the exact owned component/ledger, then moves both to a unique receipt folder under
`~/.local/state/voxide/uninstalled/`, outside AU discovery. It retains prior backups,
source builds, Studio Eval, Nitride, private evidence and all unrelated files. It
does not clear AU caches, restore an older version automatically or run `auval`.
Symlink/edited/unknown/missing/inconsistent installs are refused.

The command prints recovery component/receipt paths and writes operation receipts.
If a move/report fails, verified originals are restored only to vacant destinations.
Ctrl-C follows this same recovery/reporting path and is then re-raised; a repeated
interruption during rollback may require manual recovery. This is not crash-proof
atomicity: SIGKILL, power loss or termination that prevents Python cleanup can leave
only the started receipt and retained paths. Inspect them manually; do not delete.
Uncertain files/newcomers are retained, not deleted or overwritten; failures may
need manual recovery. **A failure receipt takes precedence over any partial result
file**; do not infer completion from a result file alone after a failed command.
Stop and inspect the reported paths rather than deleting state or forcing cleanup.

To reinstall a successfully quarantined component, explicitly choose its printed
path; the installer copies it and retains the quarantined original:

```sh
python3 scripts/au.py install --component "/absolute/recovery/path/voxide.component"
python3 scripts/au.py validate
```

## 6. Evidence, privacy and zero-spend/license boundary

[Machine-readable evidence index](evidence/pr-10/handoff-index.json) links every
major milestone and its scope; [PR10 closeout](evidence/pr-10/implementation-001.md)
records execution and final no-go. Tracked documents travel with a checkout; raw
build/artifact logs stay local/ignored and may be absent in another checkout.
Private `evaluation/` material is not in the index's readable artifact set and is
never packaged/read automatically. Missing private/raw evidence stays unavailable,
not invented. Preserve required expressive challenge c and all consumed claims.

The local verifier checks an exact signed arm64/system-only product, forbids
evaluator/Signalsmith/audit/interpose linkage, checks optional artifact manifests
without modifying them, and records evidence availability—not acceptance. It
rejects installed/private input paths and output overlap with verified inputs.

The [notice inventory](../THIRD_PARTY_NOTICES.md) corrects historical evaluator-only
labels: current product links pinned **JUCE AGPLv3** and **Rubber Band GPL-2.0-or-
later**; no commercial license is assumed. Full pinned archives/source inventories,
their licenses/notices and corresponding build materials must be retained. Any
sharing/conveying/covered network use requires its own exact-terms/license review;
this engineering inventory is not legal clearance. No new root public/proprietary
license, paid signing/notarization, installer, package purchase, upload, Git push or
public release is authorized or performed. Total required new expenditure: **zero**.
