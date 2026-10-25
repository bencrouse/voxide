#include "WorkerEngine.h"
#include "../Source/Tests/AllocationAudit.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <stdexcept>

namespace voxide::worker
{
namespace
{
using Clock=std::chrono::steady_clock;
void pause() { std::this_thread::sleep_for(std::chrono::microseconds(50)); }
}
Engine::Engine(engines::Config config,double initialRatio,double initialHz,Factory factory,Options options)
    : ratio(initialRatio),hz(initialHz),thread([this,config,initialRatio,initialHz,factory,options]
      { run(config,initialRatio,initialHz,factory,options); })
{
    // Off render: a worker is fully constructed before metadata is published.
    while (!ready.load(std::memory_order_acquire)) pause();
    if (!healthy()) { thread.join(); throw std::runtime_error("Worker native setup failed"); }
}
Engine::~Engine()
{
    shutdown.store(true,std::memory_order_release);
    if (thread.joinable()) thread.join();
}
void Engine::control(double r,double f)
{
    if (!std::isfinite(r) || r<.25 || r>4 || !std::isfinite(f) || f<0)
    { failed.store(true,std::memory_order_release); return; }
    ratio=r; hz=f;
}
void Engine::process(const float* samples,int count)
{
    if (!healthy()) return;
    if (finishRequested || !samples || count<1 || count>128)
    { failed.store(true,std::memory_order_release); return; }
    Command command; command.serial=submitted+1; command.ratio=ratio; command.hz=hz; command.count=count;
    std::copy_n(samples,count,command.input.data());
    if (!input.push(command)) { failed.store(true,std::memory_order_release); return; }
    ++submitted;
    highWater=std::max(highWater,submitted-completed.load(std::memory_order_acquire));
}
int Engine::available() const
{
    if (!healthy()) return 0;
    if (read==pending.count)
    {
        if (!output.pop(pending)) return 0;
        read=0;
        if (pending.first!=received || pending.count<1 || pending.count>1024)
        { failed.store(true,std::memory_order_release); return 0; }
        received+=static_cast<unsigned>(pending.count);
    }
    return pending.count-read;
}
int Engine::retrieve(float* destination,int maximum)
{
    if (!destination || maximum<1) { failed.store(true,std::memory_order_release); return 0; }
    const int count=std::min(available(),maximum);
    std::copy_n(pending.audio.data()+read,count,destination); read+=count;
    return count;
}
bool Engine::waitIdle() const
{
    const auto limit=Clock::now()+std::chrono::seconds(5);
    while (completed.load(std::memory_order_acquire)<submitted)
    {
        if (!healthy() || Clock::now()>limit) return false;
        pause();
    }
    return healthy();
}
void Engine::finish()
{
    if (!finishRequested)
    {
        finishRequested=true;
        Command final; final.final=true; final.serial=submitted+1;
        if (healthy() && input.push(final)) ++submitted;
        else { failed.store(true,std::memory_order_release); shutdown.store(true,std::memory_order_release); }
    }
    // Off render only; no native flush/join/wait is exposed on the callback path.
    while (!finished.load(std::memory_order_acquire)) pause();
}
void Engine::reset(double,double) { throw std::logic_error("Reconstruct worker graphs while stopped"); }
Engine::Metrics Engine::metrics() const
{
    if (!finished.load(std::memory_order_acquire)) throw std::logic_error("Worker metrics require finish");
    auto result=measurement; result.queueHighWater=highWater; result.failed=!healthy(); return result;
}
bool Engine::drain(engines::Engine& native)
{
    for (int calls=0;native.available()>0;++calls)
    {
        if (calls==64 || !healthy()) return false;
        Packet packet; packet.first=measurement.nativeFrames;
        const int requested=std::min(1024,native.available());
        packet.count=native.retrieve(packet.audio.data(),requested);
        if (packet.count<1 || packet.count>requested) return false;
        for (int i=0;i<packet.count;++i) if (!std::isfinite(packet.audio[i])) return false;
        if (!output.push(packet)) return false;
        measurement.nativeFrames+=static_cast<unsigned>(packet.count);
    }
    return true;
}
void Engine::run(engines::Config config,double initialRatio,double initialHz,Factory factory,Options options) noexcept
{
    try
    {
        measurement.auditDetected=!audit::available || audit::selfTest();
        if (!measurement.auditDetected) throw std::runtime_error("Worker allocation detector failed");
        audit::begin(); auto native=factory(config,initialRatio,initialHz);
        if (!native) throw std::runtime_error("Worker factory returned no engine");
        description=native->info(); measurement.setupAllocations=audit::end();
        if (description.quantum!=128) throw std::runtime_error("Worker quantum must be 128");
        ready.store(true,std::memory_order_release);
        while (!shutdown.load(std::memory_order_acquire) && healthy())
        {
            Command command;
            if (!input.pop(command)) { pause(); continue; }
            if (!command.final && options.stallCommand==measurement.commands+1)
                std::this_thread::sleep_for(std::chrono::milliseconds(options.stallMilliseconds));
            audit::begin();
            if (command.final) native->finish();
            else { native->control(command.ratio,command.hz); native->process(command.input.data(),command.count); }
            const bool valid=drain(*native);
            const auto allocations=audit::end();
            if (command.final) measurement.finishAllocations+=allocations;
            else { measurement.bodyAllocations+=allocations; ++measurement.commands; }
            if (!valid) { failed.store(true,std::memory_order_release); break; }
            completed.store(command.serial,std::memory_order_release);
            if (command.final) break;
        }
        audit::begin(); native.reset(); measurement.destroyAllocations=audit::end();
    }
    catch (...) { audit::end(); failed.store(true,std::memory_order_release); }
    finished.store(true,std::memory_order_release);
    ready.store(true,std::memory_order_release);
}
}
