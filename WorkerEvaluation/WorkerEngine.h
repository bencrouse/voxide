#pragma once
#include "../InteractionEvaluation/InteractionProcessor.h"
#include <thread>

namespace voxide::worker
{
// Research-only proxy. One callback owner; all native ownership lives on worker.
// Construction, finish, waitIdle and destruction require a stopped/joined callback.
class Engine final : public engines::Engine
{
public:
    using Factory=interaction::Processor::Factory;
    struct Options { unsigned stallCommand=0, stallMilliseconds=0; };
    struct Metrics
    {
        std::size_t setupAllocations=0, bodyAllocations=0, finishAllocations=0, destroyAllocations=0;
        std::uint64_t commands=0, nativeFrames=0, queueHighWater=0;
        bool auditDetected=false, failed=false;
    };
    Engine(engines::Config, double, double, Factory, Options);
    ~Engine() override;
    engines::Info info() const noexcept override { return description; }
    void control(double,double) override;
    void process(const float*,int) override;
    int available() const override;
    int retrieve(float*,int) override;
    void finish() override;
    void reset(double,double) override; // Intentionally unsupported: reconstruct stopped.
    bool waitIdle() const; // Offline coordinator only, never called by callback.
    bool healthy() const noexcept { return !failed.load(std::memory_order_acquire); }
    Metrics metrics() const; // Only after finish.
private:
    struct Command
    {
        std::uint64_t serial=0;
        double ratio=1,hz=200;
        int count=0;
        bool final=false;
        std::array<float,128> input {};
    };
    struct Packet { std::uint64_t first=0; int count=0; std::array<float,1024> audio {}; };
    static_assert(std::atomic<std::size_t>::is_always_lock_free && std::atomic<bool>::is_always_lock_free);
    static_assert(std::atomic<std::uint64_t>::is_always_lock_free);
    interaction::Queue<Command,512> input;
    mutable interaction::Queue<Packet,512> output;
    mutable Packet pending;
    mutable int read=0;
    mutable std::uint64_t received=0;
    mutable std::atomic<bool> failed {false};
    std::atomic<bool> ready {false}, shutdown {false}, finished {false};
    std::atomic<std::uint64_t> completed {0};
    std::uint64_t submitted=0, highWater=0;
    double ratio=1,hz=200;
    engines::Info description;
    Metrics measurement;
    std::thread thread;
    bool finishRequested=false;
    void run(engines::Config,double,double,Factory,Options) noexcept;
    bool drain(engines::Engine&);
};
}
