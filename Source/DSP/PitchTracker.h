#pragma once
#include <array>
#include <cstdint>

namespace voxide
{
enum class TrackerVariant { yin, multiCandidate };
struct PitchFrame
{
    // Epoch-local source interval [begin, end); decision exists only at available.
    std::uint64_t begin = 0, end = 0, available = 0;
    double hz = 0, midi = 0, confidence = 0, rms = 0;
    bool voiced = false;
};

// Streaming, fixed-storage YIN difference functions. No future samples, heap or locks.
class PitchTracker
{
public:
    void prepare(double sampleRate, TrackerVariant = TrackerVariant::multiCandidate) noexcept;
    void reset() noexcept;
    bool push(float sample) noexcept;
    const PitchFrame& frame() const noexcept { return current; }
    int supportSamples() const noexcept { return support * 2; }
    int hopSamples() const noexcept { return hop * 2; }
private:
    void analyse() noexcept;
    static constexpr int comparison = 512, capacity = 1024;
    std::array<double, capacity> ring {}, window {}, difference {};
    std::array<bool, capacity> invalid {};
    PitchFrame current;
    TrackerVariant variant = TrackerVariant::multiCandidate;
    double rate = 24000, sum = 0, previousMidi = 0;
    std::uint64_t samples = 0;
    int write = 0, filled = 0, decimation = 0, sinceHop = 0, hop = 120;
    int minLag = 22, maxLag = 293, support = 805, goodFrames = 0;
    bool badSample = false, previousVoiced = false, supported = true;
};
}
