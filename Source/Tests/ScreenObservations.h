#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>

namespace voxide::screen
{
// Post-render synthetic observations only; never part of the timed AU call.
// Absolute sample positions preserve coverage when a callback crosses a second.
struct Observations
{
    unsigned nonfinite=0;
    float peak=0;
    std::array<unsigned,5> wet {},audible {};
    void observe(int frame,int rate,float left,float right,float lead)
    {
        if (rate<=0 || frame<0 || frame/rate>=5) throw std::runtime_error("Invalid screen observation position");
        if (!std::isfinite(left) || !std::isfinite(right)) { ++nonfinite;return; }
        peak=std::max({peak,std::abs(left),std::abs(right)});
        const auto second=static_cast<std::size_t>(frame/rate);
        // Silence/lost channels are not harmonies merely because they differ
        // from the expected lead. This is aggregate activity, not pitch proof.
        if (std::abs(left)>1e-4f && std::abs(right)>1e-4f)
        {
            ++audible[second];
            if (std::abs(left-lead)>1e-4f && std::abs(right-lead)>1e-4f) ++wet[second];
        }
    }
};
inline void observationGuards()
{
    auto require=[](bool value) { if (!value) throw std::runtime_error("Screen observation negative control failed"); };
    for (int rate:{44100,48000})
    {
        Observations silent,dry,oneChannel,wet;
        silent.observe(rate,rate,0,0,.02f);dry.observe(rate,rate,.02f,.02f,.02f);
        oneChannel.observe(rate,rate,.03f,0,.02f);wet.observe(rate,rate,.03f,.03f,.02f);
        require(silent.wet[1]==0 && silent.audible[1]==0 && dry.wet[1]==0 && dry.audible[1]==1);
        require(oneChannel.wet[1]==0 && wet.wet[1]==1 && wet.audible[1]==1);
        Observations boundary;
        // The 44.1 kHz variable callback [88045,88302) contains 155 samples
        // before the second boundary and 102 after it. Generalize both rates.
        for (int at=2*rate-155;at<2*rate+102;++at)
            boundary.observe(at,rate,at<2*rate?.02f:.03f,at<2*rate?.02f:.03f,.02f);
        require(boundary.wet[1]==0 && boundary.wet[2]==102 && boundary.audible[1]==155 && boundary.audible[2]==102);
    }
}
}
