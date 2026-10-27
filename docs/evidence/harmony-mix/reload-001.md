# AU reload follow-up — 001

The user ran `make reload-au` and reported an error, then asked why the command
did not handle the complete workflow. Existing user-run reports show installation
of **0.5.0 succeeded** (`build/au-checks/20261027T184204Z-df9ad0b1/result.json`),
while validation returned success for cached **0.3.0**, correctly rejected as stale
(`20261027T184204Z-3b67b00c/result.json` and `auval.log`). No agent-installed
operation is inferred or executed from these logs.

The built bundle's root directory still had an **October 20** timestamp despite
new October 27 plist/binary contents. `shutil.copytree` preserves that timestamp.
This is a concrete omitted discovery-refresh step and a plausible contributor to
stale registration, not proof of the registrar's exact internal caching behavior.

## Repair

- Refresh only the signed staging bundle's directory timestamp before publication;
  do not modify the source bundle, signed file bytes, existing backups or neighbors.
- Explicit `validate-au` also refreshes only its positively owned bundle directory,
  so an already-installed copy can recover without another rebuild/install.
- Hold the installer's exclusive lock across verification and bounded retries.
  Recheck component/ledger inode/bytes before and after every subprocess/attempt;
  stop on external changes. Unknown/edited/symlinked installs are refused.
- Retry only `auval` success with the right identity but the wrong cached version:
  five attempts maximum with waits of 0.5, 1, 2 and 4 seconds. Keep every log and
  outcome. Nonzero exits, missing success/version, wrong identities, signing errors
  and exhausted stale versions still fail; no false installed/Logic acceptance.
- No shared cache deletion, registrar/DAW process kill, automatic Logic UI operation,
  unrelated plug-in change or source-recording access. A dylib already mapped into
  Logic cannot be safely hot-replaced by an external Make command; quit Logic first.

Validation uses temporary fake install roots, fake signers and mocked validation
processes only. Real macOS registry convergence still needs the user's next explicit
`make validate-au` or `make reload-au`; it is not claimed from those fixtures.

Executed: all **295 Python tests pass**, including **11 new refresh/retry
regressions** (`build/harmony-mix-validation/reload-python-001.log`). Tests cover
stale-to-current convergence, bounded exhaustion, immediate genuine-failure
refusal, source/neighbor/receipt preservation, edit/ownership/symlink rejection,
concurrent-installer locking and retained CLI failure history. The first targeted
test invocation exposed a test-helper name collision with `unittest.TestCase.run`;
renaming that helper fixed collection, without changing the implementation.
This follow-up changes Python tooling/docs only; the previous mixing DSP and its
four-profile results are unchanged. The already-preserved signed artifact is not
rewritten or re-signed, and this new tooling has not been run on the actual AU.

`build/harmony-mix-validation/refresh-signature-001/` additionally verifies a
**copied uninstalled signed bundle** with `codesign --verify --deep --strict`
before and after refreshing only its directory timestamp. Both pass; all file
hashes/modes and the original artifact's timestamp/bytes are unchanged. This is
signature-preservation evidence, not evidence that the real registry refreshed.
