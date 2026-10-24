#pragma once
#include "EngineAdapter.h"
#include "HarmonySelector.h"
#include <array>
#include <atomic>
#include <cstdint>
#include <memory>

namespace voxide::interaction
{
template<class T, std::size_t N> class Queue
{
public:
    bool push(const T& value) noexcept
    {
        const auto w = write.load(std::memory_order_relaxed), next = (w + 1) % N;
        if (next == read.load(std::memory_order_acquire)) return false;
        values[w] = value; write.store(next,std::memory_order_release); return true;
    }
    bool peek(T& value) const noexcept
    {
        const auto r = read.load(std::memory_order_relaxed);
        if (r == write.load(std::memory_order_acquire)) return false;
        value = values[r]; return true;
    }
    bool pop(T& value) noexcept
    {
        if (!peek(value)) return false;
        read.store((read.load(std::memory_order_relaxed)+1)%N,std::memory_order_release); return true;
    }
    void clearStopped() noexcept { read.store(0); write.store(0); }
private:
    std::array<T,N> values {};
    std::atomic<std::size_t> read {0}, write {0};
};
enum class Mode { oraclePrescribed, livePrescribed, scale, midi };
enum class Treatment { native, shared };
enum class Profile { live, mix };
struct Settings
{
    engines::Config engine;
    Mode mode = Mode::oraclePrescribed;
    Treatment treatment = Treatment::native;
    Profile profile = Profile::mix;
    HarmonyConfig harmony;
    // Explicit research controls; defaults retain the historical PR05 ablation.
    int shiftLimit = 24;
    bool inactiveUncertain = false;
    bool operator==(const Settings& other) const noexcept;
};
// All event times are epoch-local source samples. Oracle frames are available at
// `available`, never silently backdated. A sole producer posts in available order.
struct Event
{
    enum class Kind { pitch, targets, midi, harmony } kind = Kind::pitch;
    std::uint64_t source = 0, available = 0;
    PitchFrame pitch;
    std::array<double,3> targetMidi {57,64,69};
    unsigned mask = 7;
    std::array<std::uint8_t,3> bytes {};
    HarmonyConfig harmony;
};
struct Telemetry
{
    enum class Kind { control, output, request } kind = Kind::control;
    std::uint64_t epoch = 0, wall = 0, requested = 0, available = 0, frameBegin = 0, frameEnd = 0, frameAvailable = 0;
    std::int64_t source = 0, firstOutput = 0;
    int voice = 0, count = 0;
    int requestKind = 0;
    double hz = 0, confidence = 0, targetMidi = 0, requestedShift = 0, appliedShift = 0, weight = 0;
    bool voiced = false, active = false;
};
struct Output
{
    float leadDirect = 0, leadAligned = 0, sumDirect = 0, sumAligned = 0;
    std::array<float,3> native {}, voices {};
};
struct Stats
{
    std::array<std::uint64_t,3> nativeFrames {}, underflows {}, lateSamples {};
    std::array<std::uint64_t,3> inputHashes {14695981039346656037ull,14695981039346656037ull,14695981039346656037ull};
    std::array<std::uint64_t,3> controlHashes {14695981039346656037ull,14695981039346656037ull,14695981039346656037ull};
    std::uint64_t telemetryDropped = 0, badEvents = 0, lateControls = 0, invalidInput = 0, missingMetadata = 0;
    std::uint64_t rejectedTargets = 0, fifoOverflow = 0;
    float unrenderedFinishPeak = 0;
};
// Research-only, fixed-output live scheduling. No plug-in/UI linkage. Render owns
// all DSP. post()/readTelemetry() are sole-producer/sole-consumer handoff surfaces.
// Lifecycle/settings replacement requires ALL render/post/telemetry owners to be
// externally stopped/joined. settings()/stats() are owner/joined reads, not UI APIs.
class Processor
{
public:
    using Factory = std::unique_ptr<engines::Engine> (*)(engines::Config,double,double);
    Processor(Settings, Factory);
    ~Processor();
    bool configureStopped(Settings);
    bool resetStopped();
    // Finalization is terminal for the native graph; reset/reconfigure before restart.
    void start();
    void stop();
    Output push(float);
    bool post(const Event&) noexcept;
    bool readTelemetry(Telemetry&) noexcept;
    int latencySamples() const noexcept;
    int analysisDelaySamples() const noexcept;
    bool running() const noexcept;
    const Settings& settings() const noexcept;
    const Stats& stats() const noexcept; // render owner or after it is joined
private:
    struct State;
    Factory factory;
    std::unique_ptr<State> state;
};
}
