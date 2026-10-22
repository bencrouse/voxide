#include "PitchTracker.h"
#include "HarmonySelector.h"
#include "AllocationAudit.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <vector>

namespace
{
void check(bool pass, const char* text)
{
    if (!pass) { std::cerr << "Tracking: " << text << '\n'; std::exit(EXIT_FAILURE); }
}
voxide::PitchFrame pitch(double midi)
{
    voxide::PitchFrame p; p.midi = midi; p.hz = 440 * std::exp2((midi - 69) / 12); p.confidence = 1; p.voiced = true;
    return p;
}
void send(voxide::HarmonySelector& s, int command, int a, int b)
{
    const std::uint8_t bytes[] { static_cast<std::uint8_t>(command), static_cast<std::uint8_t>(a), static_cast<std::uint8_t>(b) };
    s.midi(bytes, 3);
}
int noteAt(const std::vector<int>& notes, int degree)
{
    const int count = static_cast<int>(notes.size());
    int octave = 0;
    while (degree < 0) { degree += count; --octave; }
    return 12 * (octave + degree / count) + notes[static_cast<std::size_t>(degree % count)];
}
void scaleTests()
{
    voxide::HarmonySelector selector;
    const auto catalog = voxide::scaleCatalog();
    check(catalog.size() == 42, "Catalog changed without schema/test update");
    // Exhaustive custom-set mapping: all 4095 nonempty 12-tone sets, every root,
    // every member, signed degree and octave wrap. Oracle uses a different lookup.
    for (unsigned set = 1; set <= 4095; ++set)
    {
        std::vector<int> notes;
        for (int pc = 0; pc < 12; ++pc) if ((set & (1u << pc)) != 0) notes.push_back(pc);
        for (int root = 0; root < 12; ++root)
        {
            voxide::HarmonyConfig cfg;
            cfg.scale = 41; cfg.customMask = static_cast<std::uint16_t>(set); cfg.root = root;
            cfg.degrees = { -3, 2, 0 }; cfg.octaves = { -1, 0, 1 };
            selector.configure(cfg);
            for (int i = 0; i < static_cast<int>(notes.size()); ++i)
            {
                selector.pitch({}); // independent anchor, no inherited hysteresis
                const double input = 60 + root + notes[static_cast<std::size_t>(i)] + 0.11;
                selector.pitch(pitch(input));
                for (std::size_t voice = 0; voice < 3; ++voice)
                {
                    const int shift = noteAt(notes, i + cfg.degrees[voice]) - notes[static_cast<std::size_t>(i)] + 12 * cfg.octaves[voice];
                    const auto& actual = selector.targets()[voice];
                    check(std::abs(actual.midi - input - shift) < 1e-9 && actual.active == (std::abs(shift) <= 24), "Custom degree/root/wrap/expression/range mismatch");
                }
            }
        }
    }
    for (std::size_t scale = 0; scale < catalog.size() - 1; ++scale)
    {
        check(catalog[scale].mask != 0 && (catalog[scale].mask & 1) != 0, "Invalid built-in scale");
        for (std::size_t other = scale + 1; other < catalog.size(); ++other)
            check(std::string(catalog[scale].id) != catalog[other].id, "Duplicate scale ID");
        voxide::HarmonyConfig cfg; cfg.scale = static_cast<int>(scale);
        selector.configure(cfg); selector.pitch({}); selector.pitch(pitch(60.2));
        check(std::abs(selector.targets()[2].midi - 72.2) < 1e-9, "Octave changed with scale cardinality");
        std::vector<int> notes;
        for (int pc = 0; pc < 12; ++pc) if ((catalog[scale].mask & (1 << pc)) != 0) notes.push_back(pc);
        check(selector.targets()[0].shift == noteAt(notes, 2), "Built-in third mismatch");
        for (int root = 0; root < 12; ++root)
            for (int semitone = -12; semitone <= 12; ++semitone)
            {
                cfg.root = root;
                selector.configure(cfg); selector.pitch({});
                const double input = 60 + root + semitone + 0.5;
                // Independent exhaustive absolute-note oracle, lower-note tie break.
                int nearestDegree = 0;
                double nearestDistance = 1000;
                for (int degree = -24; degree <= 24; ++degree)
                {
                    const double distance = std::abs(input - (60 + root + noteAt(notes, degree)));
                    if (distance < nearestDistance) { nearestDegree = degree; nearestDistance = distance; }
                }
                selector.pitch(pitch(input));
                check(selector.targets()[0].shift == noteAt(notes, nearestDegree + 2) - noteAt(notes, nearestDegree), "Accidental/root/tie mapping mismatch");
            }
    }
    voxide::HarmonyConfig cfg;
    selector.configure(cfg); selector.pitch({}); selector.pitch(pitch(64.49));
    const auto below = selector.targets()[0].shift;
    for (int i = 0; i < 50; ++i)
    {
        selector.pitch(pitch(i % 2 ? 64.60 : 64.40));
        check(selector.targets()[0].shift == below, "Boundary vibrato chatter");
    }
    selector.pitch(pitch(64.9));
    check(selector.targets()[0].shift != below, "Deliberate change suppressed");
    selector.pitch({}); selector.pitch(pitch(64.5));
    check(selector.targets()[0].shift == below, "Exact tie must go down");
    selector.pitch(pitch(64.6));
    cfg.octaves[1] = 1;
    selector.configure(cfg);
    check(selector.targets()[0].shift == below, "Other voice edit reset source anchor");
    cfg.degrees[2] = 1;
    selector.configure(cfg);
    check(selector.targets()[0].shift == below, "Degree edit reset source anchor");
    cfg.customMask ^= 1;
    selector.configure(cfg);
    check(selector.targets()[0].shift == below, "Inactive custom edit reset source anchor");
    cfg.root = 1;
    selector.configure(cfg);
    voxide::HarmonySelector fresh; fresh.configure(cfg); fresh.pitch(pitch(64.6));
    for (std::size_t i = 0; i < 3; ++i)
        check(selector.targets()[i].shift == fresh.targets()[i].shift, "Root change retained stale source anchor");
    cfg.scale = 41; cfg.customMask = 0;
    selector.configure(cfg);
    check(!selector.targets()[0].active, "Empty custom set not silent");
}
void midiTests()
{
    voxide::HarmonySelector s;
    voxide::HarmonyConfig cfg; cfg.midiMode = true; s.configure(cfg); s.pitch(pitch(60.25));
    send(s, 0x90, 60, 100); send(s, 0x90, 64, 100); send(s, 0x90, 67, 100);
    check(s.midiSlots() == std::array<int,3>{60,64,67}, "Stable initial slots");
    send(s, 0x90, 72, 100);
    check(s.midiSlots() == std::array<int,3>{72,64,67}, "Newest-three replacement");
    send(s, 0x80, 72, 0);
    check(s.midiSlots() == std::array<int,3>{60,64,67}, "Older held note restoration");
    send(s, 0x90, 60, 100); send(s, 0x80, 60, 0);
    check(s.midiSlots()[0] == 60, "Repeated note count lost");
    check(s.midiSummary().keyPresses == 3 && s.midiSummary().physicalKeys == 3 && s.midiSummary().soundingPitches == 3, "Repeated-note summary lost physical count");
    send(s, 0xb0, 64, 127); send(s, 0x80, 60, 0);
    check(s.midiSlots()[0] == 60, "Sustain release lost");
    check(s.midiSummary().keyPresses == 2 && s.midiSummary().physicalKeys == 2 && s.midiSummary().sustainedKeys == 1
        && s.midiSummary().soundingPitches == 3, "Sustain/physical summary conflated");
    send(s, 0xb0, 64, 0);
    check(s.midiSlots()[0] == -1, "Sustain pedal off stuck note");
    send(s, 0x91, 64, 100); send(s, 0x90, 64, 0);
    check(s.midiSlots()[1] == 64, "Other channel duplicate released");
    send(s, 0xb1, 120, 0);
    check(s.midiSlots()[1] == -1, "Channel panic failed");
    check(s.targets()[2].midi == 67 && std::abs(s.targets()[2].shift - 6.75) < 1e-9, "Absolute MIDI expression policy");
    send(s, 0x90, 69, 100); send(s, 0x80, 69, 0);
    check(s.midiSlots()[0] == -1, "Same-offset on/off ordering stuck note");
    send(s, 0x80, 69, 0); send(s, 0x90, 69, 100);
    check(s.midiSlots()[0] == 69, "Same-offset off/on ordering lost note");
    send(s, 0xb0, 64, 127); send(s, 0xb0, 123, 0);
    check(s.midiSlots()[0] == 69, "All-notes-off ignored sustain");
    send(s, 0xb0, 121, 0);
    check(s.midiSlots()[0] == -1 && s.midiSlots()[2] == -1, "Reset controllers failed to release sustained notes");
    send(s, 0x90, 67, 100);
    s.pitch(pitch(43)); check(s.targets()[0].active && s.targets()[0].shift == 24, "Inclusive +24 limit rejected");
    s.pitch(pitch(91)); check(s.targets()[0].active && s.targets()[0].shift == -24, "Inclusive -24 limit rejected");
    s.pitch(pitch(40)); check(!s.targets()[0].active, "Out-of-range target clamped");
    s.pitch({}); check(!s.targets()[2].active, "Unvoiced target active");
    s.panic(); send(s, 0x90, 60, 100); s.pitch(pitch(60));
    check(!s.midiKnown() && !s.targets()[0].active, "Unknown overflow state not fail-closed");
    const std::uint8_t reset = 0xff; s.midi(&reset, 1);
    check(s.midiKnown() && s.midiSlots()[0] == -1, "System reset failed");
    for (unsigned i = 0; i < 65536; ++i) send(s, 0x90, 60, 100);
    check(!s.midiKnown(), "Repeated-note counter overflow not detected");
}
std::vector<voxide::PitchFrame> track(const std::vector<float>& audio, double rate, voxide::TrackerVariant variant, const std::vector<int>& blocks)
{
    voxide::PitchTracker tracker; tracker.prepare(rate, variant);
    std::vector<voxide::PitchFrame> frames;
    std::size_t at = 0, block = 0;
    while (at < audio.size())
    {
        const auto until = std::min(audio.size(), at + static_cast<std::size_t>(blocks[block++ % blocks.size()]));
        for (; at < until; ++at)
            if (tracker.push(audio[at]))
            {
                const auto frame = tracker.frame();
                check(frame.available == at + 1 && frame.end == frame.available && frame.begin < frame.end, "Noncausal timestamp");
                frames.push_back(frame);
            }
    }
    return frames;
}
void trackerTests()
{
    for (double rate : {44100.0, 48000.0})
        for (auto variant : {voxide::TrackerVariant::yin, voxide::TrackerVariant::multiCandidate})
            for (double midi : {40.0, 48.0, 60.0, 72.0, 84.0})
            {
                std::vector<float> audio(static_cast<std::size_t>(rate * 0.16));
                const double hz = 440 * std::exp2((midi - 69) / 12);
                for (std::size_t i = 0; i < audio.size(); ++i) audio[i] = static_cast<float>(0.2 * std::sin(6.283185307179586 * hz * i / rate));
                const auto reference = track(audio, rate, variant, {1});
                check(!reference.empty() && reference.back().voiced && std::abs(reference.back().midi - midi) < 0.12, "Steady range tone incorrect");
                for (auto blocks : {std::vector<int>{32}, {64}, {128}, {257}, {512}, {1024}, {32,257,1,1024,64,128,512}})
                {
                    const auto result = track(audio, rate, variant, blocks);
                    check(result.size() == reference.size(), "Partition lost frames");
                    for (std::size_t i = 0; i < result.size(); ++i)
                        check(result[i].begin == reference[i].begin && result[i].available == reference[i].available
                            && result[i].hz == reference[i].hz && result[i].voiced == reference[i].voiced, "Partition changed decision");
                }
                // Alter only the unseen future: shared prefix must be identical.
                auto changed = audio;
                std::fill(changed.begin() + static_cast<std::ptrdiff_t>(audio.size() / 2), changed.end(), 0.0f);
                const auto future = track(changed, rate, variant, {257});
                for (std::size_t i = 0; i < reference.size() && reference[i].available <= audio.size() / 2; ++i)
                    check(reference[i].hz == future[i].hz && reference[i].voiced == future[i].voiced, "Future influenced prefix");
            }
    voxide::PitchTracker tracker; tracker.prepare(48000);
    for (int i = 0; i < 10000; ++i) tracker.push(0.2f);
    check(!tracker.frame().voiced, "DC voiced");
    tracker.reset(); check(tracker.frame().available == 0, "Reset retained history");
    tracker.push(std::numeric_limits<float>::quiet_NaN());
    for (int i = 1; i < 3000; ++i) tracker.push(0);
    check(!tracker.frame().voiced, "Nonfinite/silence voiced");
    tracker.prepare(96000); for (int i = 0; i < 3000; ++i) check(!tracker.push(0.2f), "Unsupported rate emitted estimates");
}
}
void runTrackingTests()
{
    if (voxide::audit::available) check(voxide::audit::selfTest(), "Allocation detector did not catch deliberate C/C++ allocations");
    scaleTests(); midiTests(); trackerTests();
    voxide::PitchTracker tracker; tracker.prepare(48000);
    voxide::HarmonySelector selector;
    voxide::audit::begin();
    for (int i = 0; i < 12000; ++i)
    {
        if (i % 240 == 0) send(selector, 0x90, 60 + i % 12, 100);
        if (tracker.push(static_cast<float>(0.2 * std::sin(i * 0.03)))) selector.pitch(tracker.frame());
    }
    const auto allocations = voxide::audit::end();
    check(allocations == 0, "Tracker/selector allocated");
    std::cout << "Tracking: 4095 custom sets/all roots, built-ins, MIDI, causality, partitions passed; "
              << (voxide::audit::available ? "C/C++ allocation audit passed" : "allocation audit disabled under sanitizer (Debug/Release audit required)") << '\n';
}
