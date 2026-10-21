# Contributing locally

## Build and check

```sh
make check                                  # Debug AU/app and all tests
make check-full                             # Debug/Release; focused ASan/TSan
make routing-check                          # device-free inner loop, no Logic UI
python3 scripts/check.py --profile release --offline
python3 scripts/check.py --full --fresh --offline  # new build trees, no deletion
cmake --preset local-debug
cmake --build --preset local-debug
ctest --preset local-debug
```

`make check` and `make check-full` are incremental; they never remove build trees,
install components, open devices, or regenerate approved audio. For a clean build,
use `--fresh` (new build directories inside that run's evidence folder), or configure
into a **new** directory with `cmake -S . -B build/<new-name>` and the same cache
variables. Do not delete unfamiliar build/evidence directories.

All test checks use explicit conditions, not `assert` disabled in Release.
Tooling tests use temporary fake component/install roots, never the user's AU
directory. ASan disables process-lifetime leak reporting for system/JUCE code;
other memory errors remain fatal. TSan includes the diagnostic queue's concurrent
producer/consumer ordering test as well as DSP/processor checks; this is not a
certification of every host/framework callback or GUI lifecycle.

`scripts/check.py` records per-command logs, exit statuses, compiler/SDK/OS/architecture,
revision, binary hashes, and hashes of non-ignored project files under unique
`build/checks/` runs. A source-file change during checks requires a rerun.
Logs are written before/after failure too. No upload, hostname, or serial collection.

## Dependencies

Default acquisition downloads exactly the pin in `cmake/JucePin.cmake` into
`.cache/dependencies/`, verifies its SHA-256, then extracts into the selected build.
Each configure rechecks the archive and an archive-derived digest of the extracted
tree, including hidden/additional files and symlinks. Reused edited source is rejected
without overwriting it; use a fresh build directory to recover. An older unverified
tree is adopted only if identical to a new canonical extraction. Downloads are
serialized across build profiles. Do not edit the extracted dependency source;
use an explicit checkout for inspection. After fetching:

```sh
cmake --preset local-release -DVOXIDE_OFFLINE=ON
```

An external verified archive can be supplied with
`-DVOXIDE_JUCE_ARCHIVE=/absolute/path/to/archive.tar.gz`. A clean exact Git checkout
can be supplied with `-DJUCE_DIR=/absolute/path/to/JUCE`. Wrong commits, tracked
edits, staged edits, untracked files, and nested non-root checkouts are rejected.
No unpinned bypass option or sibling discovery exists. Do not use another project's
build/source tree as a dependency. Update pins only in a deliberate reviewed change.

There are no Python package dependencies in PR 00: scripts use only the standard
library. DSP engines and NumPy/SciPy belong to later evaluation PRs and must be
pinned/audited when introduced, not speculatively installed now.

## Code boundaries

- `Source/DSP`: small host-independent DSP; currently mono-to-stereo copying only.
- `Source/PluginProcessor.*`: actual shared processor/editor used by AU and tests.
- `Source/PluginEntry.cpp`: JUCE factory for AU/development Standalone wrappers.
- `Source/Tests`: deterministic DSP/processor checks, no microphone/device setup.
- `Source/Tests/AuRenderTests.cpp`: process-local registration/rendering of the exact
  built AU, checking source selection, silent/disconnected sidechain, bypass,
  time-varying samples across transport/reset, MIDI API acceptance, and state into
  a fresh instance. No installed-component lookup or audio device is involved.
- `Source/Diagnostics.h`: fixed-capacity render-producer/editor-consumer telemetry.
- `Source/DiagnosticLog.*`: non-render JSONL formatting/writing, opt-in through the
  editor. No PCM capture; no automatic logging on project recall.
- `scripts/tests`: dependency-policy and installer-safety tests in temporary roots.
- `evaluation/`: ignored private sources/projects/evidence; never auto-record/upload.

Keep audio rendering allocation-free in our code and separate from UI/document
operations. PR 00 does not instrument every framework render allocation/lock.
Preserve the AU identity. Build metadata shows the Git revision, dirty marker,
configuration, and product version; fingerprints in reports identify dirty builds
more precisely than the revision label alone.

## Explicit installation

`make reload-au` is deliberately separate from checks. It builds Release, installs
and ad-hoc signs only Voxide, then invokes `launchctl asuser <uid> auval` in the
logged-in GUI user context. It does not kill Logic or reset broad AU caches.
Ask the user to close Voxide sessions before replacing a loaded build.

Ownership is recorded in `~/.local/state/voxide/au-install.json`; edited/unrecognized
bundles and symlink paths are refused. Prior recognized bundles are retained as
`~/.local/state/voxide/backups/` (outside AU discovery). If signing fails, the current install remains;
ownership is rechecked after signing, and Darwin no-clobber renames protect
publication and restoration. If ledger publication fails after the swap, installation
rolls back before pending-file cleanup. If an external process changes the target
during rollback, the helper refuses destructive restoration and reports the preserved
backup for manual recovery. Rollback checks identity/content again after moving an
entry; uncertain recovery stages under `~/.local/state/voxide/au-stage-*` are kept,
not automatically deleted. Source/destination must support same-volume exclusive
renames; a cross-volume error fails safely, without a clobbering copy fallback.
Do not manually
delete/re-sign an installed bundle then expect the helper to treat it as unchanged.
No automatic uninstall or backup pruning is part of PR 00.

`scripts/au.py validate` requires the reported component identity/version and
success marker, not just `auval` exit status. A stale registry must be handled by
a human rescan of Voxide only. The native routing loop bypasses registry discovery
by registering the exact built component inside the test process.

The Standalone plist declares microphone privacy usage so a manual launch can
request permission normally. Metadata checks never launch it or grant permission.

No commits, pushes, remote creation, purchases, licensing changes, or publication
are implied by running the development commands. Use the project plan's per-PR
validation and agent handoff sections, marking unperformed tests pending.

For PR 01 use `docs/LOGIC_ROUTING.md`: automated engineering validation and manual
Logic acceptance are separate. Do not reinstate scripted DAW UI traversal or close
manual gates using native test results. Environment probing is explicit/read-only,
not part of ordinary checks; it does not identify Logic's selected device settings.
