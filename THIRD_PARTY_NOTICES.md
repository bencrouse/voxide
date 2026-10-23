# Third-party dependencies — local-only development

The user selected local-only use under JUCE's AGPLv3 option. No paid license,
public release, or proprietary redistribution permission is assumed. Private
development does not require publishing this repository merely to run the program
locally. Sharing/conveying copies changes the obligations and needs a separate
review of the actual license terms, including corresponding source and notices.
This document is an engineering inventory, not a substitute for those terms.

## JUCE 8.0.15

- Author: Raw Material Software Limited / JUCE contributors.
- Repository: https://github.com/juce-framework/JUCE
- Revision: `91ad83ae34a81e0833b1a2b0866f54846370ae53`
- Archive: `https://codeload.github.com/juce-framework/JUCE/tar.gz/91ad83ae34a81e0833b1a2b0866f54846370ae53`
- SHA-256: `04f8d5055382582c757be9da069ea98338005f98248facd9c2804435ac853e70`
- Selected option: **AGPLv3**, not the commercial JUCE license.
- Exact license: https://github.com/juce-framework/JUCE/blob/91ad83ae34a81e0833b1a2b0866f54846370ae53/LICENSE.md
- Full AGPL text: https://www.gnu.org/licenses/agpl-3.0.html

The pin matches Nitride's dependency version/hash, but Voxide fetches/verifies its
own archive. We consulted Nitride's structure; no Nitride implementation/assets
were copied and no license to redistribute Nitride is inferred.

### Bundled dependency audit

The complete upstream inventory and exact notices stay in the verified extracted
source at `build/<profile>/_deps/JUCE-<revision>/LICENSE.md` and its referenced
files. Preserve these when transferring dependency source. Before any distribution,
assemble required full notices for the precise linked configuration, not just this
summary. Relevant AU/UI/audio modules include:

| Dependency | Upstream terms/location relative to JUCE root |
| --- | --- |
| Apple AudioUnitSDK | Apache-2.0; `modules/juce_audio_plugin_client/AU/AudioUnitSDK/LICENSE.txt` |
| HarfBuzz | Old MIT and file-specific notices; `modules/juce_graphics/fonts/harfbuzz/COPYING` |
| SheenBidi | Apache-2.0; `modules/juce_graphics/unicode/sheenbidi/LICENSE` |
| libpng | libpng/zlib-style; `modules/juce_graphics/image_formats/pnglib/` |
| zlib | zlib license; `modules/juce_core/zip/zlib/README` |
| JPEG codec | Independent JPEG Group; `modules/juce_graphics/image_formats/jpglib/README` |
| CHOC / QuickJS | ISC / MIT; `modules/juce_javascript/choc/` (upstream inventory lists exact files) |

JUCE's inventory also lists Oboe, FLAC, Ogg/Vorbis, LV2/pslextensions, OpenGL
GLEW/Mesa/Khronos, AAX, VST3, Box2D, ASIO, and build/example dependencies.
Their presence in the archive is not evidence that all are linked or used here.
Only AU/Standalone are requested; browser/curl and optional FLAC/Ogg/MP3/LAME/Windows
media codec support are disabled. No VST/AAX SDK, SDK account, or commercial codec
license is required for this target. Apple system frameworks come from the user's
existing macOS SDK; they are not copied into the repository.

## No other adopted packages in PR 00

Python scripts use the standard library; CMake, Git, and Apple's tools are existing
local prerequisites. No pip/conda/Homebrew install is run. The PR 04 inventory below
supersedes the original bootstrap-only inventory; Rubber Band's GPL/public source
is not a proprietary commercial license.

## PR 04 — evaluator-only dependencies (not linked to the product)

All are fetched from official GitHub repositories at full immutable revisions and
verified by archive SHA-256. Complete upstream license files remain in each verified
source tree. `cmake/engine-dependencies.json` is the machine-readable inventory;
`scripts/engine_dependencies.py` also verifies every extracted file, including hidden
files, against the pinned archive on every configure. Edits are refused and preserved.
There is no upstream build-system download, package-manager install or paid license.

| Package | Pin | Terms and selected use |
| --- | --- | --- |
| Signalsmith Stretch 1.4.0 tag | `a670068d9aeb64913331d5cc29337b19a457a7df` | MIT, `LICENSE.txt`; copyright 2022 Geraint Luff / Signalsmith Audio Ltd.; separate native evaluator only |
| Signalsmith Linear 0.6.4 | `de55e6a50ffcf6f8f43f649692d94691c7025151` | MIT, `LICENSE.txt`; copyright 2025 Signalsmith Audio; Stretch FFT dependency, Apple Accelerate backend |
| Rubber Band 4.0.0 | `1d95888bec3ae0a17c0c4af791810d5a63f6bc35` | GPL-2.0-or-later, `COPYING`; Particular Programs Ltd.; separate local comparator, no commercial license assumed |

Archive hashes, in the same order:

```
948b8382bb13f316d13536cdfe06111789a538e8fee7f7a531ee2aec94de1747
cc39693d5c8bc96451b5503819bb82b2d88c1df450183c55595e5d9d4b517012
0d6fe8fcc54d8e0b7da1a67ebdb0129dd62f983ecbfb66650c65f977d46fe20f
```

Official source/license locations:
- `https://github.com/Signalsmith-Audio/signalsmith-stretch` / `LICENSE.txt` at the pin.
- `https://github.com/Signalsmith-Audio/linear` / `LICENSE.txt` at the pin.
- `https://github.com/breakfastquay/rubberband` / `COPYING`, `README.md`,
  `COMPILING.md` and `single/RubberBandSingle.cpp` at the pin.

The Stretch tag is named 1.4.0 while its header's static version array still reads
1.3.2. We preserve/report the exact source pin rather than changing upstream code or
pretending that string is an independent version verification.

Rubber Band uses its supported single-compilation-unit build: R3, `NO_THREADING`,
Apple vDSP FFT and built-in BQ resampler. No FFTW, IPP, Speex, libsamplerate, SLEEF,
libsndfile, Vamp, LADSPA/LV2 or extra SDK is selected. Unused bundled notices and demo
assets stay in the upstream archive; demo recordings are not imported into the corpus.
Apple Accelerate is an existing system framework, not vendored into Git. Preserve
the complete upstream inventories before any distribution, not just this summary.

These local evaluators do **not** authorize proprietary distribution or App Store
publication of Rubber Band-linked software. Before sharing source/binaries or linking
a selected engine into the product, revisit the full applicable licensing obligations.
