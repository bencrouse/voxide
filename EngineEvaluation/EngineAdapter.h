#pragma once
#include <array>
#include <cstddef>
#include <memory>

namespace voxide::engines
{
struct Config { int rate = 48000, window = 512, hop = 128; };
struct Info
{
    int inputLatency = 0, outputLatency = 0, startPad = 0, startTrim = 0;
    int quantum = 128, controlLag = 0, nativeVersion = 0;
    int nominalOffset() const noexcept { return inputLatency + outputLatency; }
};
class Engine
{
public:
    virtual ~Engine() = default;
    virtual Info info() const noexcept = 0;
    virtual void control(double ratio, double sourceHz) = 0;
    virtual void process(const float*, int count) = 0;
    virtual int available() const = 0;
    virtual int retrieve(float*, int maximum) = 0;
    virtual void finish() = 0;
    virtual void reset(double ratio, double sourceHz) = 0;
};
std::unique_ptr<Engine> create(Config, double initialRatio, double sourceHz);
const char* engineName() noexcept;

// Fixed storage and explicit failure, never an allocating queue or silent repair.
template<std::size_t Capacity> class Fifo
{
public:
    bool push(float value) noexcept
    {
        if (count == Capacity) return false;
        data[write] = value; write = (write + 1) % Capacity; ++count; return true;
    }
    bool pop(float& value) noexcept
    {
        if (count == 0) return false;
        value = data[read]; read = (read + 1) % Capacity; --count; return true;
    }
    void reset() noexcept { read = write = count = 0; }
    std::size_t size() const noexcept { return count; }
private:
    std::array<float, Capacity> data {};
    std::size_t read = 0, write = 0, count = 0;
};
}
