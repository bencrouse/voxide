#include "WorkerEngine.h"
#include "../Source/Tests/AllocationAudit.h"
#include <algorithm>
#include <atomic>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace
{
using namespace voxide;
std::thread::id owner;
std::atomic<int> wrongThread {0}, living {0};
bool invalidOutput=false;
void require(bool value,const char* text) { if (!value) throw std::runtime_error(text); }
void nativeOwner() { if (std::this_thread::get_id()==owner) ++wrongThread; }
class Fake final : public engines::Engine
{
public:
    Fake() { nativeOwner(); ++living; }
    ~Fake() override { nativeOwner(); --living; }
    engines::Info info() const noexcept override { nativeOwner(); return {0,0,0,0,128,0,3}; }
    void control(double r,double) override { nativeOwner(); ratio=r; }
    void process(const float* source,int count) override
    {
        nativeOwner(); require(pending==0,"Fake not drained");
        void* (*volatile allocate)(std::size_t)=std::malloc;
        void* p=allocate(19); std::free(p); // Deliberate worker allocation positive control.
        for (int i=0;i<count;++i) data[i]=invalidOutput?std::numeric_limits<float>::quiet_NaN():static_cast<float>(source[i]*ratio);
        pending=count; read=0;
    }
    int available() const override { nativeOwner(); return pending; }
    int retrieve(float* out,int maximum) override
    {
        nativeOwner(); require(maximum>0 && maximum<=pending,"Fake over-read");
        std::copy_n(data.data()+read,maximum,out); read+=maximum; pending-=maximum; return maximum;
    }
    void finish() override { nativeOwner(); }
    void reset(double,double) override { throw std::logic_error("No native reset in worker prototype"); }
private:
    std::array<float,128> data {};
    double ratio=1;
    int pending=0,read=0;
};
std::unique_ptr<engines::Engine> factory(engines::Config,double,double) { return std::make_unique<Fake>(); }
void transfer()
{
    auto engine=std::make_unique<worker::Engine>(engines::Config{48000,1,128},1,220,factory,worker::Engine::Options{});
    std::array<float,128> input {}, output {};
    for (int run=0;run<1024;++run)
    {
        input.fill(static_cast<float>(run*.00001));
        audit::begin(); engine->control(2,220); engine->process(input.data(),128);
        require(audit::end()==0,"Proxy callback allocated");
        require(engine->waitIdle(),"Fake worker missed offline barrier"); // Outside callback.
        audit::begin();
        require(engine->available()==128 && engine->retrieve(output.data(),53)==53
                && engine->retrieve(output.data()+53,75)==75 && engine->available()==0,"Packet split/order mismatch");
        require(audit::end()==0,"Proxy retrieval allocated");
        for (float value:output) require(value==input[0]*2,"Worker changed sample/control identity");
    }
    engine->finish(); const auto metrics=engine->metrics();
    require(!metrics.failed && metrics.commands==1024 && metrics.nativeFrames==128*1024,"Worker metrics mismatch");
    if (audit::available) require(metrics.bodyAllocations>=1024,"Worker allocations were hidden");
    bool rejected=false;
    try { engine->reset(1,220); } catch (const std::logic_error&) { rejected=true; }
    require(rejected,"Native reset must not be used as a priming fix");
    audit::begin(); engine->process(input.data(),128);
    require(audit::end()==0 && !engine->healthy() && engine->available()==0,"Finalized proxy restarted");
}
void overflow()
{
    auto engine=std::make_unique<worker::Engine>(engines::Config{48000,1,128},1,220,factory,worker::Engine::Options{1,200});
    std::array<float,128> zero {};
    audit::begin();
    for (int i=0;i<600;++i) engine->process(zero.data(),128);
    require(audit::end()==0,"Queue overflow allocated on callback");
    require(!engine->healthy(),"Queue overflow did not latch the audio-mute flag");
    engine->finish(); require(engine->metrics().failed,"Queue failure was erased");
}
void nonfinite()
{
    invalidOutput=true;
    auto engine=std::make_unique<worker::Engine>(engines::Config{48000,1,128},1,220,factory,worker::Engine::Options{});
    std::array<float,128> zero {}; engine->process(zero.data(),128);
    require(!engine->waitIdle(),"Nonfinite native output passed");
    engine->finish(); require(!engine->healthy() && engine->available()==0,"Invalid native output escaped");
    engine.reset(); invalidOutput=false;
}
void advertisedPacketFailure()
{
    auto engine=std::make_unique<worker::Engine>(engines::Config{48000,1,128},1,220,factory,worker::Engine::Options{});
    std::array<float,128> input {},output {};input.fill(.01f);
    engine->process(input.data(),128);require(engine->waitIdle(),"First packet not ready");
    require(engine->available()==128,"First packet not advertised");
    invalidOutput=true;engine->process(input.data(),128);
    require(!engine->waitIdle(),"Native failure not exposed");engine->finish();
    audit::begin();const int count=engine->available();const int received=engine->retrieve(output.data(),count);
    require(audit::end()==0 && count==128 && received==128 && !engine->healthy(),"Failure invalidated an advertised packet");
    engine.reset();invalidOutput=false;
}
}
int main()
{
    try
    {
        owner=std::this_thread::get_id();
        if (audit::available) require(audit::selfTest(),"Allocation controls failed");
        transfer(); overflow(); nonfinite(); advertisedPacketFailure();
        require(wrongThread==0 && living==0,"Native ownership/lifetime escaped worker");
        std::cout<<"Worker ownership, SPSC order/splits, callback allocation, worker allocation detection, overflow, nonfinite and stopped lifecycle controls passed\n";
        return 0;
    }
    catch (const std::exception& e) { audit::end(); std::cerr<<e.what()<<'\n'; return 1; }
}
