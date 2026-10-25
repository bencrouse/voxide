#pragma once
#include <array>
#include <atomic>
#include <memory>
#include <cstdint>

namespace voxide::studio
{
static_assert(std::atomic<std::size_t>::is_always_lock_free && std::atomic<bool>::is_always_lock_free
    && std::atomic<float>::is_always_lock_free && std::atomic<std::uint64_t>::is_always_lock_free);
// The sole product backend is pinned Rubber Band R3 short, native consonants,
// formants preserved. Native ownership, including metadata, stays off render.
struct Info { int pad=0,trim=0; };
class Native
{
public:
    virtual ~Native()=default;
    virtual Info info() const noexcept=0;
    virtual void control(double,double)=0;
    virtual void process(const float*,int)=0;
    virtual int available() const=0;
    virtual int retrieve(float*,int)=0;
};
using Factory=std::unique_ptr<Native>(*)(int,double,double);
std::unique_ptr<Native> createNative(int,double,double);

// Single producer, single consumer. Never reset indices while either runs.
template<class T,std::size_t N> class Queue
{
public:
    bool push(const T& value) noexcept
    {
        const auto w=write.load(std::memory_order_relaxed),next=(w+1)%N;
        if (next==read.load(std::memory_order_acquire)) return false;
        values[w]=value;write.store(next,std::memory_order_release);return true;
    }
    bool peek(T& value) const noexcept
    {
        const auto r=read.load(std::memory_order_relaxed);
        if (r==write.load(std::memory_order_acquire)) return false;
        value=values[r];return true;
    }
    bool pop(T& value) noexcept
    {
        if (!peek(value)) return false;
        read.store((read.load(std::memory_order_relaxed)+1)%N,std::memory_order_release);return true;
    }
private:
    std::array<T,N> values {};
    std::atomic<std::size_t> read {0},write {0};
};
}
