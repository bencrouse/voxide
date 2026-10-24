// Research copy of PR04's thin interface: exactly one additional 256/32 preset
// and a compile-time backend comparison. No upstream source modifications.
#include "EngineAdapter.h"
#include <signalsmith-stretch/signalsmith-stretch.h>
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace voxide::engines
{
class Native final : public Engine
{
public:
    Native(Config c,double ratio,double hz) : config(c), stretch(0x564f5849)
    {
        stretch.configure(1,c.window,c.hop,false); control(ratio,hz);
    }
    Info info() const noexcept override { return {stretch.inputLatency(),stretch.outputLatency(),0,0,config.hop,stretch.inputLatency(),1}; }
    void control(double ratio,double hz) override
    {
        stretch.setTransposeFactor(static_cast<float>(ratio)); stretch.setFormantFactor(1,true);
        stretch.setFormantBase(static_cast<float>((hz>0?hz:200)/config.rate));
    }
    void process(const float* input,int n) override
    {
        if(pending || n<0 || n>4096) throw std::runtime_error("Invalid fixed native process");
        const float* in[]{input}; float* out[]{output.data()}; stretch.process(in,n,out,n); pending=n; read=0;
    }
    int available() const override { return pending; }
    int retrieve(float* out,int n) override
    {
        if(n<0 || n>pending) throw std::runtime_error("Retrieval exceeds availability");
        std::copy_n(output.data()+read,n,out); read+=n; pending-=n; return n;
    }
    void finish() override
    {
        if(pending) throw std::runtime_error("Undrained finish");
        float* out[]{output.data()}; pending=stretch.outputLatency(); read=0; stretch.flush(out,pending);
    }
    void reset(double ratio,double hz) override { stretch.reset(); pending=read=0; control(ratio,hz); }
private:
    Config config;
    signalsmith::stretch::SignalsmithStretch<float> stretch;
    std::array<float,4096> output{};
    int pending=0,read=0;
};
const char* engineName() noexcept { return "signalsmith"; }
std::unique_ptr<Engine> create(Config c,double ratio,double hz)
{
    const bool preset=(c.window==256 && c.hop==32) || ((c.window==512 || c.window==1024 || c.window==2048) && c.hop==c.window/4);
    if(!preset || (c.rate!=44100 && c.rate!=48000) || !std::isfinite(ratio) || ratio<.25 || ratio>4 || !std::isfinite(hz) || hz<0 || hz>c.rate/2)
        throw std::invalid_argument("Unsupported bounded research preset");
    return std::make_unique<Native>(c,ratio,hz);
}
}
