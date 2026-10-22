#include "HarmonySelector.h"
#include <algorithm>
#include <cmath>
#include <initializer_list>
#include <limits>

namespace voxide
{
namespace
{
constexpr std::uint16_t mask(std::initializer_list<int> notes)
{
    std::uint16_t value = 0;
    for (int note : notes) value |= static_cast<std::uint16_t>(1u << note);
    return value;
}
constexpr Scale scales[] {
    { "major", "Major / Ionian", mask({0,2,4,5,7,9,11}) },
    { "natural-minor", "Natural minor / Aeolian", mask({0,2,3,5,7,8,10}) },
    { "dorian", "Dorian", mask({0,2,3,5,7,9,10}) },
    { "phrygian", "Phrygian", mask({0,1,3,5,7,8,10}) },
    { "lydian", "Lydian", mask({0,2,4,6,7,9,11}) },
    { "mixolydian", "Mixolydian", mask({0,2,4,5,7,9,10}) },
    { "locrian", "Locrian", mask({0,1,3,5,6,8,10}) },
    { "harmonic-minor", "Harmonic minor", mask({0,2,3,5,7,8,11}) },
    { "melodic-minor", "Melodic minor (ascending set)", mask({0,2,3,5,7,9,11}) },
    { "dorian-b2", "Dorian flat 2", mask({0,1,3,5,7,9,10}) },
    { "lydian-augmented", "Lydian augmented", mask({0,2,4,6,8,9,11}) },
    { "lydian-dominant", "Lydian dominant", mask({0,2,4,6,7,9,10}) },
    { "mixolydian-b6", "Mixolydian flat 6", mask({0,2,4,5,7,8,10}) },
    { "locrian-natural2", "Locrian natural 2", mask({0,2,3,5,6,8,10}) },
    { "altered", "Altered / Super Locrian", mask({0,1,3,4,6,8,10}) },
    { "harmonic-major", "Harmonic major", mask({0,2,4,5,7,8,11}) },
    { "double-harmonic", "Double harmonic major", mask({0,1,4,5,7,8,11}) },
    { "hungarian-minor", "Hungarian minor", mask({0,2,3,6,7,8,11}) },
    { "hungarian-major", "Hungarian major", mask({0,3,4,6,7,9,10}) },
    { "neapolitan-minor", "Neapolitan minor", mask({0,1,3,5,7,8,11}) },
    { "neapolitan-major", "Neapolitan major", mask({0,1,3,5,7,9,11}) },
    { "phrygian-dominant", "Phrygian dominant", mask({0,1,4,5,7,8,10}) },
    { "ukrainian-dorian", "Ukrainian Dorian", mask({0,2,3,6,7,9,10}) },
    { "persian", "Persian (12-TET set)", mask({0,1,4,5,6,8,11}) },
    { "enigmatic", "Enigmatic", mask({0,1,4,6,8,10,11}) },
    { "major-pentatonic", "Major pentatonic", mask({0,2,4,7,9}) },
    { "minor-pentatonic", "Minor pentatonic", mask({0,3,5,7,10}) },
    { "major-blues", "Major blues", mask({0,2,3,4,7,9}) },
    { "minor-blues", "Minor blues", mask({0,3,5,6,7,10}) },
    { "hirajoshi", "Hirajoshi (12-TET set)", mask({0,2,3,7,8}) },
    { "insen", "Insen (12-TET set)", mask({0,1,5,7,10}) },
    { "iwato", "Iwato (12-TET set)", mask({0,1,5,6,10}) },
    { "kumoi", "Kumoi (12-TET set)", mask({0,2,3,7,9}) },
    { "pelog", "Pelog (12-TET approximation)", mask({0,1,3,7,8}) },
    { "whole-tone", "Whole tone", mask({0,2,4,6,8,10}) },
    { "diminished-wh", "Diminished whole / half", mask({0,2,3,5,6,8,9,11}) },
    { "diminished-hw", "Diminished half / whole", mask({0,1,3,4,6,7,9,10}) },
    { "augmented", "Augmented", mask({0,3,4,7,8,11}) },
    { "bebop-dominant", "Bebop dominant", mask({0,2,4,5,7,9,10,11}) },
    { "bebop-major", "Bebop major", mask({0,2,4,5,7,8,9,11}) },
    { "chromatic", "Chromatic", 0x0fff },
    { "custom", "Custom pitch classes", 0 }
};
int floorDivide(int a, int b) noexcept { return a >= 0 ? a / b : (a - b + 1) / b; }
std::uint16_t scaleMask(const HarmonyConfig& config) noexcept
{
    const auto index = static_cast<std::size_t>(std::clamp(config.scale, 0, static_cast<int>(std::size(scales)) - 1));
    return index == std::size(scales) - 1 ? config.customMask & 0x0fff : scales[index].mask;
}
}
std::span<const Scale> scaleCatalog() noexcept { return scales; }
void HarmonySelector::reset() noexcept
{
    keys = {}; sustain = {}; age = {}; serial = 0;
    slots = { -1, -1, -1 }; output = {}; source = {};
    known = true; anchored = false;
}
void HarmonySelector::panic() noexcept { reset(); known = false; }
void HarmonySelector::configure(const HarmonyConfig& value) noexcept
{
    if (config == value) return;
    if (config.midiMode != value.midiMode || config.root != value.root || scaleMask(config) != scaleMask(value))
        anchored = false;
    config = value;
    select();
}
bool HarmonySelector::sounding(int note) const noexcept
{
    for (const auto& channel : keys)
        if (channel[static_cast<std::size_t>(note)].count != 0 || channel[static_cast<std::size_t>(note)].sustained) return true;
    return false;
}
MidiStateSummary HarmonySelector::midiSummary() const noexcept
{
    MidiStateSummary summary;
    std::array<bool, 128> pitches {};
    for (const auto& channel : keys)
        for (std::size_t note = 0; note < channel.size(); ++note)
        {
            const auto& key = channel[note];
            summary.keyPresses += key.count;
            if (key.count != 0) ++summary.physicalKeys;
            if (key.sustained) ++summary.sustainedKeys;
            if (key.count != 0 || key.sustained) pitches[note] = true;
        }
    for (bool sounding : pitches) if (sounding) ++summary.soundingPitches;
    return summary;
}
void HarmonySelector::allocate() noexcept
{
    std::array<int, 3> newest { -1, -1, -1 };
    for (int note = 0; note < 128; ++note)
        if (sounding(note))
            for (int i = 0; i < 3; ++i)
                if (newest[static_cast<std::size_t>(i)] < 0 || age[static_cast<std::size_t>(note)] > age[static_cast<std::size_t>(newest[static_cast<std::size_t>(i)])])
                {
                    for (int j = 2; j > i; --j) newest[static_cast<std::size_t>(j)] = newest[static_cast<std::size_t>(j - 1)];
                    newest[static_cast<std::size_t>(i)] = note;
                    break;
                }
    for (auto& slot : slots)
        if (std::find(newest.begin(), newest.end(), slot) == newest.end()) slot = -1;
    for (int note : newest)
        if (note >= 0 && std::find(slots.begin(), slots.end(), note) == slots.end())
            for (auto& slot : slots) if (slot < 0) { slot = note; break; }
    select();
}
void HarmonySelector::midi(const std::uint8_t* bytes, int size) noexcept
{
    if (bytes == nullptr || size < 1) return;
    if (bytes[0] == 0xff) { reset(); return; }
    if (size < 3 || bytes[0] < 0x80 || bytes[0] >= 0xf0 || bytes[1] > 127 || bytes[2] > 127) return;
    const auto channel = static_cast<std::size_t>(bytes[0] & 15);
    const auto note = static_cast<std::size_t>(bytes[1]);
    const int command = bytes[0] & 0xf0;
    if (command == 0xb0 && bytes[1] == 120)
    {
        keys[channel] = {}; sustain[channel] = false;
        // A channel panic cannot certify the other channels after a global overflow.
    }
    else if (!known) return;
    else if (command == 0x90 && bytes[2] != 0)
    {
        auto& key = keys[channel][note];
        if (key.count == std::numeric_limits<std::uint16_t>::max() || serial == std::numeric_limits<std::uint64_t>::max()) { panic(); return; }
        ++key.count; key.sustained = false; age[note] = ++serial;
    }
    else if (command == 0x80 || (command == 0x90 && bytes[2] == 0))
    {
        auto& key = keys[channel][note];
        if (key.count != 0 && --key.count == 0) key.sustained = sustain[channel];
    }
    else if (command == 0xb0 && bytes[1] == 64)
    {
        sustain[channel] = bytes[2] >= 64;
        if (!sustain[channel]) for (auto& key : keys[channel]) key.sustained = false;
    }
    else if (command == 0xb0 && bytes[1] == 123)
    {
        for (auto& key : keys[channel]) { if (key.count != 0) key.sustained = sustain[channel]; key.count = 0; }
    }
    else if (command == 0xb0 && bytes[1] == 121)
    {
        sustain[channel] = false;
        for (auto& key : keys[channel]) key.sustained = false;
    }
    else return;
    allocate();
}
void HarmonySelector::pitch(const PitchFrame& value) noexcept
{
    source = value;
    if (!source.voiced) anchored = false;
    select();
}
void HarmonySelector::select() noexcept
{
    output = {};
    if (!source.voiced || !std::isfinite(source.midi)) return;
    if (config.midiMode)
    {
        if (!known) return;
        for (std::size_t i = 0; i < 3; ++i)
            if (slots[i] >= 0)
            {
                const double shift = slots[i] - source.midi;
                output[i] = { static_cast<double>(slots[i]), shift, std::abs(shift) <= 24.0 };
            }
        return;
    }
    const auto set = scaleMask(config);
    std::array<int, 12> notes {};
    int count = 0;
    for (int pc = 0; pc < 12; ++pc) if ((set & (1 << pc)) != 0) notes[static_cast<std::size_t>(count++)] = pc;
    if (count == 0) return;
    // Nearest source scale anchor. Exact ties go downward. Retain the anchor
    // until a competitor is at least 0.30 semitone closer (±15c boundary band).
    int nearest = 0;
    double distance = 1.0e9;
    for (int octave = -3; octave <= 13; ++octave)
        for (int degree = 0; degree < count; ++degree)
        {
            const int note = std::clamp(config.root, 0, 11) + 12 * octave + notes[static_cast<std::size_t>(degree)];
            const double delta = std::abs(source.midi - note);
            if (delta < distance) { distance = delta; nearest = octave * count + degree; }
        }
    auto noteAt = [&](int degree)
    {
        const int octave = floorDivide(degree, count);
        return std::clamp(config.root, 0, 11) + 12 * octave + notes[static_cast<std::size_t>(degree - octave * count)];
    };
    if (!anchored || std::abs(source.midi - noteAt(anchor)) > distance + 0.30) anchor = nearest;
    anchored = true;
    for (std::size_t i = 0; i < 3; ++i)
    {
        const int origin = noteAt(anchor);
        const int destination = noteAt(anchor + std::clamp(config.degrees[i], -11, 11)) + 12 * std::clamp(config.octaves[i], -2, 2);
        const double shift = destination - origin;
        // Preserve all source deviation, including accidentals, scoops and vibrato.
        output[i] = { source.midi + shift, shift, std::abs(shift) <= 24.0 };
    }
}
}
