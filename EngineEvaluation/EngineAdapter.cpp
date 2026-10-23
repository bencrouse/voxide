#include "EngineAdapter.h"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#ifdef VOXIDE_ENGINE_signalsmith
#include <signalsmith-stretch/signalsmith-stretch.h>
#else
#include <rubberband/RubberBandStretcher.h>
#endif

namespace voxide::engines
{
#ifdef VOXIDE_ENGINE_signalsmith
class Native final : public Engine
{
public:
    Native(Config c, double ratio, double hz) : config(c), stretch(0x564f5849)
    {
        stretch.configure(1, config.window, config.hop, false);
        control(ratio, hz);
    }
    Info info() const noexcept override
    {
        return { stretch.inputLatency(), stretch.outputLatency(), 0, 0, config.hop, stretch.inputLatency(), 1 };
    }
    void control(double ratio, double hz) override
    {
        stretch.setTransposeFactor(static_cast<float>(ratio));
        stretch.setFormantFactor(1.0f, true); // Explicit pitch compensation; never default-shift formants.
        stretch.setFormantBase(static_cast<float>((hz > 0 ? hz : 200.0) / config.rate));
    }
    void process(const float* input, int count) override
    {
        if (pending != 0 || count < 0 || count > static_cast<int>(output.size())) throw "Signalsmith output not drained/oversized input";
        const float* inputs[] { input }; float* outputs[] { output.data() };
        stretch.process(inputs, count, outputs, count);
        pending = count; read = 0;
    }
    int available() const override { return pending; }
    int retrieve(float* destination, int maximum) override
    {
        const int count = std::min(pending, maximum);
        std::copy_n(output.data() + read, count, destination); pending -= count; read += count;
        return count;
    }
    void finish() override
    {
        if (pending != 0) throw "Signalsmith finish before drain";
        float* outputs[] { output.data() };
        pending = stretch.outputLatency(); read = 0;
        if (pending > static_cast<int>(output.size())) throw "Signalsmith flush capacity exceeded";
        stretch.flush(outputs, pending);
    }
    void reset(double ratio, double hz) override { stretch.reset(); pending = read = 0; control(ratio, hz); }
private:
    Config config;
    signalsmith::stretch::SignalsmithStretch<float> stretch;
    std::array<float, 4096> output {};
    int pending = 0, read = 0;
};
const char* engineName() noexcept { return "signalsmith"; }
#else
class Native final : public Engine
{
    using RB = RubberBand::RubberBandStretcher;
public:
    Native(Config c, double ratio, double) : config(c), stretch(static_cast<std::size_t>(c.rate), 1,
        RB::OptionProcessRealTime | RB::OptionEngineFiner | RB::OptionThreadingNever
        | RB::OptionFormantPreserved | RB::OptionPitchHighConsistency
        | (c.window == 1 ? RB::OptionWindowShort : RB::OptionWindowStandard), 1.0, ratio)
    {
        if (stretch.getEngineVersion() != 3) throw std::runtime_error("Requested Rubber Band R3 not active");
        stretch.setMaxProcessSize(128);
        stretch.setDebugLevel(0);
        refresh();
    }
    Info info() const noexcept override { return description; }
    void control(double ratio, double) override
    {
        if (ratio != stretch.getPitchScale()) stretch.setPitchScale(ratio);
        refresh(); // Query dynamic metadata, but never re-pad/trim a running stream.
    }
    void process(const float* input, int count) override
    {
        const float* inputs[] { input }; stretch.process(inputs, static_cast<std::size_t>(count), false);
    }
    int available() const override { return std::max(0, stretch.available()); }
    int retrieve(float* output, int maximum) override
    {
        float* outputs[] { output }; return static_cast<int>(stretch.retrieve(outputs, static_cast<std::size_t>(maximum)));
    }
    void finish() override
    {
        const float zero = 0; const float* inputs[] { &zero }; stretch.process(inputs, 0, true);
    }
    void reset(double ratio, double) override
    {
        // reset() retains the CURRENT ratios and configures its cleared state for
        // them. Install the intended initial ratio before resetting, not after.
        stretch.setTimeRatio(1.0); stretch.setPitchScale(ratio); stretch.reset(); refresh();
    }
private:
    void refresh()
    {
        description = { 0, 0, static_cast<int>(stretch.getPreferredStartPad()), static_cast<int>(stretch.getStartDelay()), 128, 0, stretch.getEngineVersion() };
    }
    Config config;
    Info description;
    RB stretch;
};
const char* engineName() noexcept { return "rubberband-r3"; }
#endif
std::unique_ptr<Engine> create(Config config, double ratio, double hz)
{
    if ((config.rate != 44100 && config.rate != 48000) || !std::isfinite(ratio) || ratio < .25 || ratio > 4
        || !std::isfinite(hz) || hz < 0 || hz > config.rate / 2) throw std::runtime_error("Invalid engine initialization");
#ifdef VOXIDE_ENGINE_signalsmith
    if ((config.window != 512 && config.window != 1024 && config.window != 2048) || config.hop != config.window / 4)
        throw std::runtime_error("Unsupported Signalsmith configuration");
#else
    if ((config.window != 1 && config.window != 2) || config.hop != 128) throw std::runtime_error("Use Rubber Band short=1/standard=2, quantum=128");
#endif
    return std::make_unique<Native>(config, ratio, hz);
}
}
