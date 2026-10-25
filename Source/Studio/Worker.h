#pragma once
#include "Engine.h"
#include <thread>

namespace voxide::studio
{
// Derived from reviewed fb233d8 worker packet ownership. No test interposer or
// native API is called by process/available/retrieve. Destruction is off render.
class Worker
{
public:
    Worker(int,Factory);
    ~Worker();
    Info info() const noexcept { return description; }
    void process(const float*,int,double,double) noexcept;
    int available() noexcept;
    int retrieve(float*,int) noexcept;
    bool healthy() const noexcept { return !failed.load(std::memory_order_acquire); }
    bool waitIdleForTest() const;
private:
    struct Command { std::uint64_t serial=0;double ratio=1,hz=0;int count=0;std::array<float,128> audio {}; };
    struct Packet { std::uint64_t first=0;int count=0;std::array<float,1024> audio {}; };
    Queue<Command,512> input;
    Queue<Packet,512> output;
    Packet pending;
    int read=0;
    std::uint64_t submitted=0,received=0;
    std::atomic<std::uint64_t> completed {0};
    std::atomic<bool> ready {false},stop {false},failed {false};
    Info description;
    std::thread thread;
    void run(int,Factory) noexcept;
};
}
