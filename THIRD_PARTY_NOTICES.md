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
local prerequisites. No pip/conda/Homebrew install is run. Signalsmith, its FFT
dependency, and Rubber Band are not yet fetched/linked. Later PRs must pin and audit
them; Rubber Band's GPL/public source is not a proprietary commercial license.
