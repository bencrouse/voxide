#include "Studio/Session.h"
#include "StudioTestSupport.h"
#include "../../EvaluationAU/Session.h"
#include <chrono>
#include <iostream>

namespace voxide::evaluation
{
class SessionTestAccess
{
public:
    static bool idle(Session& s) { return s.waitIdleForTest(); }
};
}
namespace
{
void require(bool value,const char* text) { if (!value) throw std::runtime_error(text); }
class ReferenceFake final : public voxide::engines::Engine
{
public:
    voxide::engines::Info info() const noexcept override { return {0,0,0,0,128,0,3}; }
    void control(double r,double) override { ratio=r; }
    void process(const float* source,int n) override
    {
        require(pending==0,"Reference fake not drained");
        for (int i=0;i<n;++i) audio[static_cast<std::size_t>(i)]=static_cast<float>(source[i]*ratio);
        pending=n;read=0;
    }
    int available() const override { return pending; }
    int retrieve(float* out,int maximum) override
    { const int n=std::min(maximum,pending);std::copy_n(audio.data()+read,n,out);read+=n;pending-=n;return n; }
    void finish() override {}
    void reset(double,double) override { throw std::logic_error("No reference native reset"); }
private:
    double ratio=1;
    int pending=0,read=0;
    std::array<float,128> audio {};
};
std::unique_ptr<voxide::engines::Engine> referenceFake(voxide::engines::Config,double,double)
{ return std::make_unique<ReferenceFake>(); }
void compare(bool native)
{
    for (int rate:{44100,48000})
    {
        voxide::studio::Session product(rate,native?voxide::studio::createNative:studioTest::factory);
        voxide::evaluation::Session reference(rate,native?voxide::engines::create:referenceFake);
        const auto start=std::chrono::steady_clock::now();bool heard=false;
        for (int at=0;at<rate;++at)
        {
            if (at%128==0)
            {
                if (native) std::this_thread::sleep_until(start+std::chrono::nanoseconds(static_cast<std::uint64_t>(at)*1000000000ull/static_cast<unsigned>(rate)));
                else require(product.waitIdleForTest() && voxide::evaluation::SessionTestAccess::idle(reference),"Reference workers did not finish");
                voxide::HarmonyConfig config;config.root=at<rate/2?0:5;config.scale=at<rate/2?0:1;
                product.begin(config,voxide::TrackerVariant::multiCandidate,false,false);reference.begin(config.root,config.scale,false);
            }
            const float input=static_cast<float>(.02*std::sin(6.283185307179586*220*at/rate));
            const auto voices=product.push(input);double sum=0;for (float v:voices) sum+=v/3.;
            const float expected=reference.push(input,false,1);
            require(std::isfinite(sum) && std::abs(sum-expected)<1e-7,"Product diverged from preserved evaluation mix");
            if (at>rate/2 && std::abs(sum)>1e-4) heard=true;
            require(product.snapshot().status==voxide::studio::Status::ready
                && reference.snapshot().status==voxide::evaluation::Session::Status::ready,"Reference delivery fault (not a passing dry comparison)");
        }
        require(heard && product.snapshot().active==7,"Reference comparison lacked aggregate output/control activation");
    }
}
}
int main(int argc,char** argv)
{
    try
    {
        const bool native=argc==2 && std::string(argv[1])=="--native";
        require(native || argc==1,"Unknown reference test mode");compare(native);
        std::cout<<(native?"Native":"Fake")<<" production/reference agreement at both rates passed; aggregate only, not musical qualification\n";return 0;
    }
    catch (const std::exception& e) { std::cerr<<e.what()<<'\n';return 1; }
}
