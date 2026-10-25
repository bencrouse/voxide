#pragma once
#include "Studio/Engine.h"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <thread>

namespace studioTest
{
inline thread_local bool renderThread=false;
inline std::atomic<int> wrongOwner {0},living {0},ordinal {0};
inline std::atomic<int> silent {-1};
inline std::atomic<bool> markers {false},nonfinite {false};
inline std::atomic<float> large {0};
inline constexpr std::array<float,3> marker {.012f,.024f,.048f};
inline void owner() { if (renderThread) ++wrongOwner; }
class Native final : public voxide::studio::Native
{
public:
    Native() : voice(ordinal.fetch_add(1)%3) { owner();++living; }
    ~Native() override { owner();--living; }
    voxide::studio::Info info() const noexcept override { owner();return {}; }
    void control(double r,double) override { owner();ratio=r; }
    void process(const float* input,int n) override
    {
        owner();if (pending) throw std::runtime_error("Fake not drained");
        for (int i=0;i<n;++i)
        {
            float value=static_cast<float>(input[i]*ratio);
            if (markers.load()) value=silent.load()==voice?0.f:marker[static_cast<std::size_t>(voice)];
            if (const float big=large.load();big>0) value=big;
            output[static_cast<std::size_t>(i)]=nonfinite.load()?std::numeric_limits<float>::quiet_NaN():value;
        }
        pending=n;read=0;
    }
    int available() const override { owner();return pending; }
    int retrieve(float* destination,int maximum) override
    { owner();const int n=std::min(maximum,pending);std::copy_n(output.data()+read,n,destination);read+=n;pending-=n;return n; }
private:
    std::array<float,128> output {};
    int voice=0,pending=0,read=0;
    double ratio=1;
};
inline std::unique_ptr<voxide::studio::Native> factory(int,double,double) { return std::make_unique<Native>(); }
}
