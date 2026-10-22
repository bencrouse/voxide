#include "PitchTracker.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace voxide
{
namespace
{
constexpr double lowHz = 82.4068892282175, highHz = 1046.5022612023945;
}
void PitchTracker::prepare(double sampleRate, TrackerVariant selected) noexcept
{
    supported = sampleRate == 44100.0 || sampleRate == 48000.0;
    rate = supported ? sampleRate / 2.0 : 24000.0;
    variant = selected;
    minLag = static_cast<int>(std::floor(rate / highHz));
    maxLag = static_cast<int>(std::ceil(rate / lowHz)) + 1;
    support = comparison + maxLag;
    hop = static_cast<int>(std::round(rate * 0.005));
    reset();
}
void PitchTracker::reset() noexcept
{
    ring.fill(0); invalid.fill(false);
    current = {};
    samples = 0; write = filled = decimation = sinceHop = goodFrames = 0;
    sum = previousMidi = 0; badSample = previousVoiced = false;
}
bool PitchTracker::push(float sample) noexcept
{
    ++samples;
    if (!supported) return false;
    // Two-sample box prefilter; not a brick-wall anti-alias filter.
    if (std::isfinite(sample)) sum += sample;
    else badSample = true;
    if (++decimation != 2) return false;
    ring[static_cast<std::size_t>(write)] = sum / 2.0;
    invalid[static_cast<std::size_t>(write)] = badSample;
    write = (write + 1) % support;
    filled = std::min(support, filled + 1);
    sum = 0; decimation = 0; badSample = false;
    if (++sinceHop < hop) return false;
    sinceHop = 0;
    if (filled < support) return false;
    analyse();
    return true;
}
void PitchTracker::analyse() noexcept
{
    current = {};
    current.end = current.available = samples;
    current.begin = samples - static_cast<std::uint64_t>(support * 2);
    double mean = 0, energy = 0;
    bool clean = true;
    for (int i = 0; i < support; ++i)
    {
        const auto index = static_cast<std::size_t>((write + i) % support);
        window[static_cast<std::size_t>(i)] = ring[index];
        mean += ring[index];
        clean = clean && !invalid[index];
    }
    mean /= support;
    for (int i = 0; i < support; ++i)
    {
        const double x = window[static_cast<std::size_t>(i)] - mean;
        energy += x * x;
    }
    current.rms = std::sqrt(energy / support);
    if (!clean || current.rms < std::pow(10.0, -55.0 / 20.0))
    {
        goodFrames = 0; previousVoiced = false;
        return;
    }
    double cumulative = 0;
    difference[0] = 1;
    for (int lag = 1; lag <= maxLag; ++lag)
    {
        double value = 0;
        for (int i = 0; i < comparison; ++i)
        {
            // Anchor every candidate at the newest comparison segment rather
            // than unnecessarily analysing the oldest part of the history.
            const int newest = support - comparison + i;
            const double delta = window[static_cast<std::size_t>(newest - lag)] - window[static_cast<std::size_t>(newest)];
            value += delta * delta;
        }
        cumulative += value;
        difference[static_cast<std::size_t>(lag)] = cumulative > 0 ? value * lag / cumulative : 1;
    }
    int chosen = -1;
    double best = std::numeric_limits<double>::infinity();
    // A bounded local-candidate search, not noncausal path optimisation.
    for (int lag = minLag; lag < maxLag; ++lag)
    {
        const auto n = static_cast<std::size_t>(lag);
        if (difference[n] > difference[n - 1] || difference[n] >= difference[n + 1]) continue;
        if (variant == TrackerVariant::yin)
        {
            if (difference[n] < 0.15) { chosen = lag; break; }
        }
        else
        {
            const double midi = 69 + 12 * std::log2(rate / lag / 440.0);
            // Prefer the shortest credible period, with a weak continuity prior.
            const double continuity = previousVoiced ? std::min(12.0, std::abs(midi - previousMidi)) * 0.002 : 0;
            const double score = difference[n] + 0.025 * std::log2(static_cast<double>(lag) / minLag) + continuity;
            if (score < best) { best = score; chosen = lag; }
        }
    }
    if (chosen < 0)
    {
        goodFrames = 0; previousVoiced = false;
        return;
    }
    const auto n = static_cast<std::size_t>(chosen);
    const double a = difference[n - 1], b = difference[n], c = difference[n + 1];
    const double denominator = a - 2 * b + c;
    const double correction = denominator > 0 ? std::clamp(0.5 * (a - c) / denominator, -0.5, 0.5) : 0;
    const double hz = rate / (chosen + correction);
    current.confidence = std::clamp(1 - b, 0.0, 1.0);
    // Small edge tolerance permits interpolation error at E2/C6, not wider input support.
    if (current.confidence < 0.85 || hz < lowHz * 0.997 || hz > highHz * 1.003)
    {
        goodFrames = 0; previousVoiced = false;
        return;
    }
    current.hz = hz;
    current.midi = 69 + 12 * std::log2(hz / 440.0);
    goodFrames = std::min(2, goodFrames + 1);
    current.voiced = goodFrames >= 2;
    previousMidi = current.midi;
    previousVoiced = true;
}
}
