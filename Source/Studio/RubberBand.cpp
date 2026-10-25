#include "Engine.h"
#include <rubberband/RubberBandStretcher.h>
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace voxide::studio
{
class RubberBandNative final : public Native
{
    using RB=RubberBand::RubberBandStretcher;
public:
    RubberBandNative(int rate,double ratio) : stretch(static_cast<std::size_t>(rate),1,
        RB::OptionProcessRealTime|RB::OptionEngineFiner|RB::OptionThreadingNever
        |RB::OptionFormantPreserved|RB::OptionPitchHighConsistency|RB::OptionWindowShort,1.0,ratio)
    {
        if (stretch.getEngineVersion()!=3) throw std::runtime_error("Rubber Band R3 unavailable");
        stretch.setMaxProcessSize(128);stretch.setDebugLevel(0);
    }
    Info info() const noexcept override
    { return {static_cast<int>(stretch.getPreferredStartPad()),static_cast<int>(stretch.getStartDelay())}; }
    void control(double ratio,double) override
    { if (ratio!=stretch.getPitchScale()) stretch.setPitchScale(ratio); }
    void process(const float* samples,int n) override
    { const float* in[]{samples};stretch.process(in,static_cast<std::size_t>(n),false); }
    int available() const override { return std::max(0,stretch.available()); }
    int retrieve(float* samples,int n) override
    { float* out[]{samples};return static_cast<int>(stretch.retrieve(out,static_cast<std::size_t>(n))); }
private:
    RB stretch;
};
std::unique_ptr<Native> createNative(int rate,double ratio,double hz)
{
    if ((rate!=44100 && rate!=48000) || !std::isfinite(ratio) || ratio<.5 || ratio>2
        || !std::isfinite(hz) || hz<0 || hz>rate/2) throw std::invalid_argument("Invalid studio engine setup");
    return std::make_unique<RubberBandNative>(rate,ratio);
}
}
