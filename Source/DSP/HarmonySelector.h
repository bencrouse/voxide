#pragma once
#include "PitchTracker.h"
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace voxide
{
struct Scale { const char* id; const char* name; std::uint16_t mask; };
std::span<const Scale> scaleCatalog() noexcept;
struct HarmonyConfig
{
    bool midiMode = false;
    int root = 0, scale = 0;
    std::uint16_t customMask = 0x0ab5;
    // Zero-based degree displacement, plus independent octaves: 2,4,0+1 octave.
    std::array<int, 3> degrees { 2, 4, 0 }, octaves { 0, 0, 1 };
    bool operator==(const HarmonyConfig&) const = default;
};
struct HarmonyTarget { double midi = 0, shift = 0; bool active = false; };
struct MidiStateSummary
{
    std::uint32_t keyPresses = 0; // Includes repeated presses of a channel/pitch.
    std::uint16_t physicalKeys = 0, sustainedKeys = 0, soundingPitches = 0;
};
class HarmonySelector
{
public:
    void reset() noexcept;
    void configure(const HarmonyConfig&) noexcept;
    void pitch(const PitchFrame&) noexcept;
    void midi(const std::uint8_t* bytes, int size) noexcept;
    void panic() noexcept;
    const std::array<HarmonyTarget, 3>& targets() const noexcept { return output; }
    const std::array<int, 3>& midiSlots() const noexcept { return slots; }
    bool midiKnown() const noexcept { return known; }
    MidiStateSummary midiSummary() const noexcept;
private:
    void allocate() noexcept;
    void select() noexcept;
    bool sounding(int note) const noexcept;
    struct Key { std::uint16_t count = 0; bool sustained = false; };
    std::array<std::array<Key, 128>, 16> keys {};
    std::array<bool, 16> sustain {};
    std::array<std::uint64_t, 128> age {};
    std::array<int, 3> slots { -1, -1, -1 };
    std::array<HarmonyTarget, 3> output {};
    HarmonyConfig config;
    PitchFrame source;
    std::uint64_t serial = 0;
    int anchor = 0;
    bool anchored = false, known = true;
};
}
