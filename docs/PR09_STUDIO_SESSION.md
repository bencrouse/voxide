# PR09 — studio session measurement and final-listening handoff

Branch `pr-09-studio-session-qualification`, from merged PR08 `8aa76c6`.
Product **0.4.0** adds opt-in metadata capture; DSP, 30 host parameter IDs/defaults,
v4 state, three voices, inclusive ±12 requirements and 100 ms alignment stay intact.
No engine/profile/quality switch, lead tuning, key detection or bend flattening.

**Status: engineering implementation, not completed studio qualification.**
PR08 is accepted on the user's report; no repeated PR08 worksheet is requested.
That acceptance is not a 30-minute PR09 soak, native callback measurement or
independent final listening. Missing actual session observations and the still-
unapproved PR06B processed-character rubric produce an explicitly incomplete/
negative qualification outcome, not a fabricated pass.

The [engineering closeout](evidence/pr-09/implementation-001.md) records passing
functional validation and the **failed 44.1 kHz variable-block wet-output gate**
in both controlled repeats. Passing CPU numbers or fixed-buffer points do not
erase that failure or qualify the limited studio milestone.

## Safe automated engineering screen

```sh
cmake -S . -B build/pr-09-release -DCMAKE_BUILD_TYPE=Release -DVOXIDE_OFFLINE=ON
cmake --build build/pr-09-release --parallel 6
ctest --test-dir build/pr-09-release --output-on-failure
# Run only after builds/tests/profilers/sanitizers have finished:
python3 scripts/studio_session.py screen --build-dir build/pr-09-release
```

This runs two fresh native processes. Each loads the exact **uninstalled** AU
through process-local registration and exercises three enabled, changing scale
voices on a generated continuous low-level tone, both rates and 128/512/variable
32/128/257/512/1024 blocks, five seconds per point. Timing wraps the complete
`AudioUnitRender` invocation, including its input callbacks. Allocation interposing
is test-only, self-tested, and confined to the render caller's thread. It does not
prove worker allocation freedom or whole-wrapper lock freedom. No PCM is exported.
The declared synthetic workload uses zero octave offsets and degree steps starting
at 2/4/6, alternating to -2/3/5, with key/scale changes once per second. Requested
musical controls are retained and checked against that timeline; all three enables
are read back. It is not full-range musical/pitch qualification.

Every callback's cost/allocation/API/nonfinite/peak/wet observations and scheduling
lag are retained, including cold startup and outliers. Each finished point also
gets a sidecar CSV so a later abort does not erase earlier points; an interrupted
point is incomplete, never passed. The frozen PR02 meter/limits are used unchanged:
P99.9 occupancy **<50%**, **zero overdue** callbacks, **zero callback allocations**,
finite output and peak **<1**. At least some aggregate wet output must appear in
every voiced body second; this is not each voice's pitch proof. A variable/small-
block failure is retained separately from passing larger-buffer points.

Do not run the timing screen alongside another build/profiler/sanitizer. The
report records starting load/platform but cannot independently guarantee all other
machine activity is idle. No selective reruns, trimming or best-run promotion.
The report is a controlled functional/performance screen, **not Logic qualification**.
Exit 2 means measured failed/incomplete gates; investigate the retained report.

## Explicit user-operated Logic capture

These instructions do not authorize the agent to install or operate Logic/devices,
play audio, inspect a recording or reuse a consumed private-source approval.

1. Quit Logic, then deliberately install the current product yourself with
   `make reload-au`. Use **voxide**, not Studio Eval. Keep the existing ownership/
   rollback protections; rescan only voxide if required. Record version **0.4.0**
   and the actual installed binary hash. Do not transfer a cached older binary's
   results to this candidate. The module path/hash below is an **on-disk file at
   capture start**, not cryptographic proof of a previously cached loaded image.
2. Open a disposable copy of your representative recorded-vocal project. Initially
   use PDC **All**, Low Latency Mode **Off**, I/O **128**, Process Buffer **Small**.
   Keep the accepted single-lead route and explicitly chosen key/scale. Record
   Logic/macOS versions, Mac, rate, I/O/process buffers, route and instance count.
   Measure both 44.1/48 kHz at settings you intend to support; do not infer the
   device rate or stability of an untested buffer. MIDI/live/±24 remain deferred.
3. Choose your own recorded material **inside Logic**. The agent has no source-
   read/render approval. Include sustained and changing notes, phrase entries,
   silence and expressive material, rather than a pitch-tracker-friendly subset.
   Keep all three voices enabled and changing; leave headroom without limiting,
   normalizing or changing the approved mix policy to hide a fault.
4. On each tested instance click **Log session metadata**. This is explicit consent
   to local performance/status metadata and module-file identity capture only.
   No PCM, MIDI events, pitch traces, source hashes or source file paths are logged.
   Logs go to `evaluation/pr-09/telemetry/` in this checkout, mode 0600, exclusive
   unique names; no upload. The button's tooltip shows the path/error.
5. Run **at least 30 minutes of active playback**, plus time for transport trials.
   Exercise cycle/forward-back seek, stop/resume, phrase entries, scale/degree/level
   automation, bypass, silence, editor close/reopen and multiple instances. Capture
   continues with the editor closed. Preparation/release remains stopped-render
   only. Pause/stop/offline/bypass time does not count as active-playback exposure.
   Do not change sample rate mid-capture; stop and create a new log for that setup.
6. Watch/listen for overload alerts, dropouts, stuck/old phrases, missing voices,
   nonfinite/unsafe output and first-syllable/re-acquisition defects. Record actual
   observations and timestamps, including failures. A silent/bypassed harmonizer
   is not success; an active-target lamp does not prove each audible contribution.
   Keep the known Low Latency Mode restriction, not a live-monitoring claim.
7. Reopen each editor and click **Stop session log** before removing the instance
   or closing the project. Wait for finishing to complete. Destruction without an
   explicit stop writes **aborted**, not success. Slow disks/writer-thread stalls
   can overflow the bounded 8,192-record queue; dropped records invalidate evidence.
8. Share observations **in chat if preferred**; no manual JSON worksheet is required.
   A separate approval is needed before the agent reads the generated metadata.
   This is not approval to read or render the vocal recording itself.

Optional metadata-only analysis, explicitly selected by the user:

```sh
python3 scripts/studio_session.py analyse \
  evaluation/pr-09/telemetry/session-SELECTED.jsonl \
  --expected-binary-sha256 YOUR_EXACT_CANDIDATE_HASH --allow-session-log
```

The parser refuses outside/symlink paths, PCM/unknown fields, Debug captures,
changed candidate identity, missing/aborted footers, sequence gaps, dropped records,
nonfinite metadata and changed-rate timelines. It retains failed reports under
ignored `evaluation/pr-09/`. Timing percentiles include every callback, not only
voiced/steady windows. Wall time, monotonic span and host-reported playing exposure
are separate; wall time alone cannot claim a soak. Host transport reporting is
not independently observed playback or dropout detection.

**Timing scope:** the in-product logger measures the processor render body. AU
wrapper/host scheduling, metadata collection and file IO are outside that interval;
no allocation interposer is installed in Logic. These are lower-bound diagnostics,
not proof of whole Logic-AU callback occupancy/allocations. The synthetic screen
measures the full AU invocation in its own host, not the user's Logic session.
Actual full-host timing/allocation evidence remains unmeasured without separately
coordinated suitable profiling; no whole-wrapper lock-freedom claim is introduced.
Even metadata gates passing leave qualification explicitly **incomplete**.

## Independent final listening — approval/resources still required

The plan's reference to PR06B's *approved* revised processed-character rubric is
not supported by a completed approval in the repository: the PR06A studio-scope
and PR06B protocol/reference/listener gates still mark it pending. Do not relabel
pilot preference or the PR08 user pass as independent final qualification.

Before formal grading, coordinate the actual rubric, independent listener(s),
source handling and exact excerpts/versions. Keep the frozen numerical gates:
median **≥4/5** per required main attribute, **≥80% usable without repair**, and
no critical defect confirmed independently by two listeners. A new subjective
attribute set or listening protocol is a proposal until explicitly approved.

The retained processed-character direction is deliberate electronic vocals, not
three indistinguishable natural singers. Required checks still include intended
notes/stability, articulation/consonants, rhythm and expressive bends, entry/
re-acquisition, tails, formant/character usefulness and production usability.
Required expressive/rhythmic **challenge c**, E2–C6 and inclusive **±12** cannot be
silently omitted, retuned or declared unsupported. Do not reopen a holdout, read
private audio, rerender consumed claims or substitute Voxide's tracker for human
pitch truth without a separately approved protocol/source-bound authorization.

PR09 cannot declare a qualified studio go until required technical observations,
actual soak and independent final listening exist. Licensing and outstanding
formal/full-support accuracy remain open under the existing deferral; nothing in
this instrumentation weakens those requirements. PR10 remains a separate handoff.
