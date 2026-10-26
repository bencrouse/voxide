#pragma once
#include <array>
#include <atomic>
#include <cstdint>

namespace voxide
{
struct SessionSample
{
    std::uint64_t capture=0,sequence=0,tick=0,elapsed=0;
    int frames=0,rate=0,status=0,active=0,enabled=0,root=0,scale=0;
    unsigned epoch=0,nonfinite=0;
    bool offline=false,bypassed=false,transportKnown=false,playing=false;
    float peak=0;
};
// One render producer and one serialized off-render consumer. Indices never reset.
// This queue contains metadata only, never PCM, MIDI, pitch traces or source hashes.
class SessionTelemetry
{
public:
    static constexpr std::uint64_t capacity=8192;
    static_assert(std::atomic<std::uint64_t>::is_always_lock_free);
    static_assert(std::atomic<bool>::is_always_lock_free);
    bool start() noexcept
    {
        if (armed.load() || writing.load() || read.load()!=written.load()) return false;
        armed.store(++generation);return true;
    }
    void stop() noexcept { armed.store(0); }
    bool quiescent() const noexcept { return !writing.load(); }
    bool recording() const noexcept { return armed.load()!=0; }
    bool empty() const noexcept { return read.load(std::memory_order_relaxed)==written.load(std::memory_order_acquire); }
    std::uint64_t capture() const noexcept { return generation; } // Consumer only.
    std::uint64_t dropped() const noexcept { return lost.load(std::memory_order_relaxed); }
    std::uint64_t begin() noexcept
    {
        const auto token=armed.load();if (!token) return 0;
        writing.store(true);
        // Sequentially consistent handshake: stop cannot finalize an old-token
        // writer; a writer arriving after finalization cannot publish old data.
        if (armed.load()!=token) { writing.store(false);return 0; }
        if (renderCapture!=token) { renderCapture=token;sequence=0; }
        return token;
    }
    void finish(SessionSample sample) noexcept
    {
        sample.sequence=++sequence;
        const auto at=written.load(std::memory_order_relaxed);
        if (at-read.load(std::memory_order_acquire)==capacity) lost.fetch_add(1,std::memory_order_relaxed);
        else { samples[at%capacity]=sample;written.store(at+1,std::memory_order_release); }
        writing.store(false);
    }
    bool pop(SessionSample& sample) noexcept
    {
        const auto at=read.load(std::memory_order_relaxed);
        if (at==written.load(std::memory_order_acquire)) return false;
        sample=samples[at%capacity];read.store(at+1,std::memory_order_release);return true;
    }
private:
    std::array<SessionSample,capacity> samples {};
    std::atomic<std::uint64_t> armed {0},read {0},written {0},lost {0};
    std::atomic<bool> writing {false};
    std::uint64_t generation=0,renderCapture=0,sequence=0;
};
}
