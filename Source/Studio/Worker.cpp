#include "Worker.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <stdexcept>

namespace voxide::studio
{
namespace { void pause() { std::this_thread::sleep_for(std::chrono::microseconds(50)); } }
Worker::Worker(int rate,Factory factory) : thread([this,rate,factory]{run(rate,factory);})
{
    while (!ready.load(std::memory_order_acquire)) pause();
    if (!healthy()) { thread.join();throw std::runtime_error("Studio worker setup failed"); }
}
Worker::~Worker() { stop.store(true,std::memory_order_release);if (thread.joinable()) thread.join(); }
void Worker::process(const float* samples,int n,double ratio,double hz) noexcept
{
    if (!healthy()) return;
    if (!samples || n<1 || n>128 || !std::isfinite(ratio) || ratio<.5 || ratio>2 || !std::isfinite(hz) || hz<0)
    { failed.store(true,std::memory_order_release);return; }
    Command c;c.serial=submitted+1;c.count=n;c.ratio=ratio;c.hz=hz;
    std::copy_n(samples,n,c.audio.data());
    if (!input.push(c)) { failed.store(true,std::memory_order_release);return; }
    ++submitted;
}
int Worker::available() noexcept
{
    // An advertised finite packet survives a concurrent worker failure.
    if (read==pending.count)
    {
        if (!output.pop(pending)) return 0;
        read=0;
        if (pending.first!=received || pending.count<1 || pending.count>1024)
        { failed.store(true,std::memory_order_release);return 0; }
        received+=static_cast<unsigned>(pending.count);
    }
    return pending.count-read;
}
int Worker::retrieve(float* destination,int maximum) noexcept
{
    if (!destination || maximum<1) { failed.store(true,std::memory_order_release);return 0; }
    const int n=std::min(available(),maximum);
    std::copy_n(pending.audio.data()+read,n,destination);read+=n;return n;
}
bool Worker::waitIdleForTest() const
{
    const auto limit=std::chrono::steady_clock::now()+std::chrono::seconds(5);
    while (completed.load(std::memory_order_acquire)<submitted)
    { if (!healthy() || std::chrono::steady_clock::now()>limit) return false;pause(); }
    return healthy();
}
void Worker::run(int rate,Factory factory) noexcept
{
    try
    {
        auto native=factory(rate,1,200);
        if (!native) throw std::runtime_error("No studio native engine");
        description=native->info();
        if (description.pad<0 || description.pad>32768 || description.trim<0 || description.trim>32768)
            throw std::runtime_error("Studio engine metadata out of bounds");
        ready.store(true,std::memory_order_release);
        std::uint64_t produced=0;
        while (!stop.load(std::memory_order_acquire) && healthy())
        {
            Command c;if (!input.pop(c)) { pause();continue; }
            native->control(c.ratio,c.hz);native->process(c.audio.data(),c.count);
            for (int calls=0;native->available()>0;++calls)
            {
                if (calls==64 || !healthy()) throw std::runtime_error("Studio native output budget exceeded");
                Packet p;p.first=produced;const int requested=std::min(1024,native->available());
                p.count=native->retrieve(p.audio.data(),requested);
                if (p.count<1 || p.count>requested) throw std::runtime_error("Invalid studio retrieval");
                for (int i=0;i<p.count;++i) if (!std::isfinite(p.audio[static_cast<std::size_t>(i)]))
                    throw std::runtime_error("Nonfinite studio output");
                if (!output.push(p)) throw std::runtime_error("Studio output queue overflow");
                produced+=static_cast<unsigned>(p.count);
            }
            completed.store(c.serial,std::memory_order_release);
        }
    }
    catch (...) { failed.store(true,std::memory_order_release); }
    ready.store(true,std::memory_order_release);
}
}
