#pragma once
#include <array>
#include <atomic>
#include <cstdint>
#include <type_traits>

namespace voxide
{
struct DiagnosticEvent
{
    enum class Kind : std::uint8_t { audio, midi };
    Kind kind = Kind::audio;
    std::uint8_t source = 0, bypassed = 0, transportKnown = 0, playing = 0;
    std::uint8_t hostSampleKnown = 0;
    std::uint8_t midiSize = 0, midi[3] {}, heldKnown = 1;
    std::uint16_t heldKeys = 0;
    std::uint32_t epoch = 0, frames = 0, originalMidiSize = 0;
    std::int32_t offset = 0;
    std::uint32_t nonFinite = 0;
    std::uint64_t tick = 0, frame = 0, sequence = 0, block = 0, midiTruncatedBlocks = 0;
    std::int64_t hostSample = -1;
    double sampleRate = 0.0;
    float mainPeak = 0.0f, sidePeak = 0.0f, leftPeak = 0.0f, rightPeak = 0.0f;
    std::uint64_t sourceHash = 0, leftHash = 0, rightHash = 0;
    double pitchHz = 0, pitchConfidence = 0, targetMidi[3] {};
    std::uint64_t pitchBegin = 0, pitchEnd = 0, pitchAvailable = 0;
    std::uint8_t pitchVoiced = 0, targetActive[3] {}, musicalMidiKnown = 1, musicalOverflow = 0;
    std::uint32_t trackingEpoch = 0;
    std::uint32_t musicalKeyPresses = 0;
    std::uint16_t musicalPhysicalKeys = 0, musicalSustainedKeys = 0, musicalSoundingPitches = 0;
};
static_assert(std::is_trivially_copyable_v<DiagnosticEvent>);

// One render producer, one editor/message-thread consumer. Never reset indices
// while either is active. Overflow discards new records and reports its count.
template<std::uint64_t Capacity = 2048>
class DiagnosticQueue
{
public:
    static_assert(Capacity > 0);
    static_assert(std::atomic<std::uint64_t>::is_always_lock_free);

    bool push(const DiagnosticEvent& event) noexcept
    {
        const auto write = written.load(std::memory_order_relaxed);
        if (write - read.load(std::memory_order_acquire) >= Capacity)
        {
            lost.fetch_add(1, std::memory_order_relaxed);
            return false;
        }
        entries[write % Capacity] = event;
        written.store(write + 1, std::memory_order_release);
        return true;
    }

    bool pop(DiagnosticEvent& event) noexcept
    {
        const auto next = read.load(std::memory_order_relaxed);
        if (next == written.load(std::memory_order_acquire)) return false;
        event = entries[next % Capacity];
        read.store(next + 1, std::memory_order_release);
        return true;
    }

    std::uint64_t dropped() const noexcept { return lost.load(std::memory_order_relaxed); }
    std::uint64_t pending() const noexcept
    {
        const auto next = read.load(std::memory_order_relaxed);
        return written.load(std::memory_order_acquire) - next;
    }

private:
    std::array<DiagnosticEvent, Capacity> entries {};
    alignas(64) std::atomic<std::uint64_t> written { 0 };
    alignas(64) std::atomic<std::uint64_t> read { 0 };
    std::atomic<std::uint64_t> lost { 0 };
};
}
