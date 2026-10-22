# PR 02 analytic fixtures

These are original generated test signals, not recordings of people and not output
from Voxide or a candidate shifter. They carry no participant consent or listener
claims. `catalog.json` records generator revision, seed and SHA-256 for every WAV,
reference grid and sample-indexed control JSON. All WAVs are mono PCM24.

Fourteen cases at each of 44.1/48 kHz cover E2/C6 input endpoints, a mid-register
sine, ±24-semitone output extremes (20.60/4,186.01 Hz), missing fundamental, step,
glide, vibrato, broadband synthetic vowel resonators, noise burst, silence, level
change and bleed. Broadband resonators have no F0 and are not real-singer formant
ground truth. Phase laws supply the other signals' analytic F0. Glide/vibrato are
excluded from stable-frame accuracy and bleed is uncertain, not silently correct.
Static ratios cover −24/−12/−7/−3/0/+3/+7/+12/+24 semitones, not achieved shifts.

Generator **v2** is the explicit PR 02 review correction: controls and annotations
bind to exact PCM/timebase digests (v2 schemas), burst onset is at the first active
sample (3675/4000 at 44.1/48 kHz), and silence has no onset. **All 28 WAV files are
byte-identical to v1**; only reference/control/catalog metadata changed. The previous
uncommitted analytic baseline is preserved privately at
`evaluation/pr-02/fixture-history/pr02-v1/`; its hashes also remain in the earlier
qualification reports. No candidate output was used to regenerate expectations.

The PCM digest includes sample rate, layout, bit depth, frame count and PCM words,
ignoring unrelated RIFF metadata. Control JSON is not an SMF file; exact timestamps
and same-sample ordering are intentional. A file hash additionally binds exact WAV
bytes in the catalog.

Ordinary checks read these assets and regenerate only in temporary directories to
compare with frozen hashes. To propose another baseline revision, explicitly
generate a **new** directory and review the exact audio/reference changes:

```sh
python3 scripts/evaluation.py fixtures --directory evaluation/pr-02/proposed-fixtures-003
```

Generation refuses existing directories. There is no `--force` or baseline-update
option in checks. v2 was frozen on native arm64/macOS with existing Python 3.13;
bitwise libm portability beyond the qualified environment is not claimed. Never
silently refresh hashes to accommodate another platform or a candidate failure.
