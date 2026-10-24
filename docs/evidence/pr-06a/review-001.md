# PR06A evaluation review — 2026-10-24

**Verdict: five tooling defects must be repaired before trusting additional
verification evidence. No fixes or Stage A native executions have occurred.**

The user requested a fresh read-only agent in the bottom-right Herdr pane. That
reviewer examined the working/untracked PR06A implementation against PR05 and
reproduced the findings with synthetic temporary fixtures. The main agent then
independently inspected the referenced code and reproduced all five failure
mechanisms with synthetic fixtures/mocked I/O. Neither review accessed private
audio payloads, reran native DSP, built/installed anything, played audio or operated
Logic/devices. Temporary synthetic reproduction files were not retained as corpus
evidence. No implementation files were edited.

This is an independent **code-review session**, not independent vocal listening,
a formal pitch reference or a final product qualification.

## 1. P1 — copied listening receipts bypass consumption

`scripts/studio_listening.py:163–165` creates `render-claim.json` beside the supplied
receipt. An unchanged receipt copied to another private directory passes
`approval_context()` but has no claim beside it, allowing another render attempt.
The approved proposal/trial is unchanged; the original claim is ignored.

The reviewer intercepted the copied receipt at the mocked source reader. The
main agent independently intercepted before source access at provenance setup,
after confirming a fresh copied-directory claim was created and the original
consumed claim was untouched. No audio was read by either reproduction.

Required repair: canonical consumption keyed to the authorized proposal/trial,
independent of receipt location. Preserve/honor existing consumed claims rather
than silently treating migration as new permission. Regress copied receipts in
other directories and archived authorization copies, not only same-path retries.
The playback-only exporter already uses a canonical report/amendment claim; that
does not repair the listening renderer.

## 2. P2 — metadata proposal output can escape through a symlink

`scripts/studio_pilot.py:110–112` constructs the output path directly without
checking its ancestors for symlinks. A synthetic `evaluation/pr-06a` symlink to
`docs/public-output` caused `propose()` to write its source/rights/hash metadata
outside ignored storage. Both agents reproduced this with fake registered metadata
and an empty fake source file; no private recording was involved.

Required repair: validate private destination containment and all path ancestors
before directory creation/writes, including the metadata-only preparation route.
Add output-parent symlink regressions; input containment alone is insufficient.

## 3. P2 — partial telemetry can pass listening-export validation

`scripts/studio_listening.py:116–131`, also called by the retained-output exporter,
checks that all voice IDs appear and some controls are active, but does not prove
complete per-quantum/tail coverage. Non-control request/output rows are filtered
out before validation. A native `telemetry_dropped == 0` does not establish that
every serialized CSV row was retained.

Both agents confirmed that the existing positive fixture, containing only one
control row per voice and no output evidence, passes `safety_checks()`. The reviewer
also confirmed request-only invalid records are ignored. This does not establish
that actual retained telemetry is incomplete; it demonstrates a validator gap.

Required repair: derive and check expected control/output coverage, order, source
and delivery clocks against native settings/quantum/capture metadata. Add deleted
middle-row, missing-tail, missing-output and invalid-request regressions. Do not
invent missing rows or relax a failed evidence requirement to preserve a pass.

## 4. P2 — engineering duration trusts self-declared capture length

`scripts/studio_engineering.py:41–45,150–154` checks files/processed count against
`native["frames"]` without independently requiring the frozen five-second primary
and 0.6-second zero tail. Both agents reproduced acceptance of a consistently
shortened 10,000-frame 48 kHz capture instead of the required 268,800 frames.

Required repair: validate independently derived rate/primary/tail/total lengths
from the frozen protocol and invocation before analysis. Add self-consistent short
capture, wrong primary/tail split and truncated-file negative cases. The retained
engineering JSON metadata reports the expected lengths; it was not shown to be
shortened by this review.

## 5. P2 — engineering captures do not check either fixed sum

`scripts/studio_engineering.py:46–57,72–76` checks leads and nonzero voices but not
direct/aligned blend equations. Both agents confirmed acceptance of zero complete
sum channels with otherwise valid leads and nonzero voices. Identically wrong
outputs can also pass repeat comparisons; equality is not correctness.

Required repair: check both sums against their corresponding lead plus the three
voice channels at gain 1/3, using the retained numerical tolerance. Add zeroed
sum, wrong lead route and changed-gain cases. Do not change mix gains or normalize
outputs to conceal the failure.

## Evidence limits and next checkpoint

- All **28 existing studio Python tests** passed for the reviewer; they lack the
  regressions above. Passing tests therefore do not close these findings.
- The reviewer verified all four synthetic report hashes bound by the verification
  proposal; historical pitch counts and the proposed 36/88 Stage A bounds agree.
- These defects concern authorization/privacy and rejection of bad evidence.
  They do **not** establish corrupted retained audio, a bad engine, an audible
  artifact, or a reason to reverse the provisional Signalsmith engineering lead.
- Original reports, raw outputs, approvals and failure statuses remain immutable.
  Any later revalidation result must be additive, not a retrospective pass rewrite.
- The user approved synthetic-only verification execution before this review;
  execution remains **paused pending repairs/regressions and review of the fixes**.
  New private replay, host operation and product integration remain unapproved.
- No correction allowance is consumed by identifying validator bugs; no DSP tuning
  or musical rerender is authorized by this review. Formal human/host/support gates
  remain separate. No final engine decision, commit, merge or push occurred.
