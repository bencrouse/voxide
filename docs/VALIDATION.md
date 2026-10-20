# Validation

## Commands and evidence boundaries

```sh
make check
python3 scripts/check.py --full --offline
python3 scripts/check.py --full --fresh --offline
make reload-au
```

The last command is an explicit user-library installation, unlike ordinary checks.
`build/checks/<run>/environment.json` lists profiles, file fingerprints, commands,
exit codes, and tool/OS metadata. `build/au-checks/<run>/` contains component
fingerprints, identity, signing/install result or `auval.log`, and exit status.
No evidence is uploaded; build reports are ignored by Git.

### What is tested in PR 00

- DSP exact copy, in-place alias, silence, zero frames.
- Shared production processor: explicit Main input/Sidechain choice, mono/stereo
  main, disabled/mono/stereo sidechain (channel 1 source; other channels have
  different sentinel data), normal and bypass stereo output,
  44.1/48 kHz, zero/one/32/64/128/257/512/1024 frames, zero latency/tail,
  MIDI acceptance/no output, invalid bus layouts, routing-choice recall, invalid
  state rejection, and legacy stateless shell-v1 migration to Main input.
- Actual built AU: process-local registration plus 96 sample-level source/bypass
  cases without installed-component lookup, Logic, or audio devices.
- Generated standalone microphone privacy description and AU identity metadata.
- Dependency checksum rejection/positive control, missing offline-cache rejection,
  incorrect revision rejection, tracked/staged/untracked checkout edits, and a
  clean synthetic-checkout positive control. Reused extraction is checked against
  archive-derived content; edits, added/hidden files, and symlinks are rejected
  without overwriting them, including adoption of older unverified trees.
- Safe installer using fake bundles/temporary roots: fresh install, recognized
  replacement, unrelated plugin preservation, unknown/edited/symlink refusal,
  signing failure preservation, signing-window appearances/edits, atomic no-clobber
  renames, late-collision preservation, and rollback despite pending-cleanup failure.
- Focused ASan/TSan versions of the DSP/processor tests (not an editor-concurrency,
  allocation-audit, or performance certification).
- Explicit ad-hoc signing and GUI-user-context `auval` for the installed AU shell.

### Not established by PR 00

Actual Logic sidechain/MIDI routing, physical input, microphone access, editor
interaction, total monitoring delay, PDC in Logic, offline bounce, independent
listening, or any quality/performance/range claim about generated harmonies.
The Standalone app is built but not automatically opened because it can request
audio-device/microphone access. Later PRs own those observations.

## Execution record

### PR 00 — original pre-review bootstrap results

Environment: arm64, macOS 27.0.1, AppleClang 21.0.0, SDK 27.0, CMake 4.4.3,
Python 3.13.16. Deployment target is macOS 15.0; this run does **not** qualify an
actual macOS 15 machine. Source is the uncommitted PR 00 work on `pr-00-bootstrap`
over base `6e9847a`; per-file and binary hashes distinguish it from that plan-only
commit. Documentation completion notes were added after execution.

| Check | Actual outcome / raw evidence under repository root |
| --- | --- |
| Initial acquisition | Clean initial Debug configuration fetched and SHA-256 verified Voxide's own JUCE archive; no sibling dependency |
| Fresh offline/cache builds | `python3 scripts/check.py --full --fresh --offline`: pass; `build/checks/20261020T154831Z-cbca9832/` |
| Debug + Release | Each passed DSP, processor, and tooling CTest suites; AU and development Standalone built; fresh build logs had no compiler warnings |
| ASan + TSan | Each passed DSP and processor smoke suites in fresh directories; no claims of allocation auditing, editor concurrency, or live deadlines |
| Final incremental confirmation | `python3 scripts/check.py --full --offline`: pass; `build/checks/20261020T155429Z-746ec989/`; includes strengthened isolated wrong-revision/nested-root dependency tests |
| Tooling | All 12 unittest cases passed; fake installs preserve other plugins; dependency controls reject checksum/pin/dirty/missing-offline-cache errors |
| Full-project negative control | Invalid explicit archive rejected offline with `JUCE checksum mismatch`; `build/dependency-negative-controls/result.json` and `wrong-archive.log` |
| Fresh Release AU install/sign | `python3 scripts/au.py install --build-dir build/checks/20261020T154831Z-cbca9832/build/release`: pass; `build/au-checks/20261020T155337Z-a97a2a3f/` |
| Installed AU validation | `python3 scripts/au.py validate`: pass, `AU VALIDATION SUCCEEDED`; `build/au-checks/20261020T155340Z-86986293/` |
| Identity/buses | `aumf / Vx00 / Vxid`, version 0.0.1; two input buses (Input/Vocal sidechain), stereo output; AU validator reported 1→2 and 2→2 capabilities and passed MIDI/render tests |
| Architecture/runtime links | `lipo -archs` reported arm64; `otool -L` showed only Apple system frameworks/libraries for Release AU; Release CMake cache had no Nitride/Carbide paths |
| Ordinary checks versus install | Ordinary full checks left installed component matching its ownership ledger; no Logic launch, microphone capture, or device changes were performed |

Actual installed component: `~/Library/Audio/Plug-Ins/Components/voxide.component`.
An earlier owned shell is preserved in `~/.local/state/voxide/backups/`; no Nitride
component was replaced and no broad AU-cache reset was used. Validation's extra
sample-rate checks do not extend Voxide's future harmonizer support envelope.

Initial diagnostic: the first manually invoked Debug CTest run passed DSP/processor
but failed installer test fixtures because macOS's default temporary path traversed
the `/var` symlink, which the installer intentionally refuses. Test roots now resolve
that system alias before creating fixture paths; explicit user/bundle symlink
refusal remains tested. Subsequent full/fresh runs passed. The check runner retains
unique logs and refuses source changes during a run rather than attributing results
to a moving snapshot.

These results close **PR 00 bootstrap gates only**. No actual Logic project was
opened/recalled/bounced, no independent listening occurred, and no vocal quality,
tracking accuracy, CPU headroom, or monitoring-latency finding is claimed.

### Independent-review fixes

See `docs/CODE_REVIEW.md` for the five findings, accepted changes, and baseline
AU sample failure. The original test/auval successes above did not prove audio
source selection or bypass correctness. The new device-free AU tests now check
those samples directly. Final stable-input validation passed:

| Check | Actual outcome / raw evidence |
| --- | --- |
| `python3 scripts/check.py --full --fresh --offline` | Pass; `build/checks/20261020T163531Z-fa1273f6/`; all 12 configure/build/test steps exited 0, `source_unchanged: true`, overall status `pass` |
| Debug + Release | Each 5/5 CTest suites: DSP, processor, actual built AU, tooling, bundle metadata; clean build logs contained no compiler warnings |
| Actual built AU samples | Each Debug/Release run passed 96 source/sidechain/bypass/rate/block combinations, without devices or installed-component lookup |
| Python tooling | Each ordinary-profile run passed all 20 cases, including follow-up rollback replacement preservation |
| ASan + TSan | Each 2/2 focused DSP/processor suites; no memory/race diagnostic failures observed in these smoke scenarios |
| Dependency provenance | All four profiles recorded the verified archive and extracted-tree content digests in `environment.json` |
| Updated AU install/sign | Pass using that fresh Release bundle; `build/au-checks/20261020T164000Z-82fe8e57/`; recognized previous install retained outside discovery |
| Updated installed `auval` | Pass; `build/au-checks/20261020T164003Z-df235dee/`; reports Vocal source as indexed parameter `449045605`, Main input default, Sidechain alternate, and successful reset/initialization retention |

No actual Logic launch, device capture, UI interaction, or listening is inferred
from these results. Review and validation updates are documented after execution;
the preserved manifests identify the exact code/artifact snapshots tested.

The concurrent fresh run at `build/checks/20261020T163037Z-5247aa1f/` completed its
build/test commands but ended with `source_unchanged: false` after the follow-up
rollback fix changed Python sources. Its overall status is **fail**, not a passing
qualification. A stable-input rerun is required and will be recorded separately.

The independent agent confirmed the four other fixes and then confirmed the final
rollback preservation change after a focused file-only re-review. That is code
review evidence, not a substitute for the stable-input build/test rerun.
