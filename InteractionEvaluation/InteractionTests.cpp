#include "InteractionProcessor.h"
#include "AllocationAudit.h"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <thread>
#include <vector>

using namespace voxide;
using namespace voxide::interaction;
namespace
{
void check(bool value,const char* message) { if (!value) { std::cerr<<message<<'\n'; std::exit(1); } }
class Transport final : public engines::Engine
{
public:
    engines::Info info() const noexcept override { return {0,0,0,0,128,0,0}; }
    void control(double r,double) override { check(r>=.25 && r<=4,"Out-of-range ratio sent to engine"); }
    void process(const float* x,int n) override { check(pending==0 && n<=128,"Transport capacity"); std::copy_n(x,n,data.begin()); pending=n; read=0; }
    int available() const override { return pending; }
    int retrieve(float* x,int n) override { check(n>0 && n<=pending,"Caller retrieved beyond native availability"); std::copy_n(data.data()+read,n,x); read+=n; pending-=n; return n; }
    void finish() override {}
    void reset(double,double) override { pending=read=0; }
private:
    std::array<float,128> data {};
    int pending=0,read=0;
};
std::unique_ptr<engines::Engine> transport(engines::Config,double,double) { return std::make_unique<Transport>(); }
Event pitch(std::uint64_t at,double hz,bool voiced=true)
{
    Event e; e.source=e.available=at; e.pitch.hz=hz; e.pitch.confidence=voiced?1:0; e.pitch.voiced=voiced; e.pitch.begin=e.pitch.end=at; return e;
}
void contracts()
{
    if (audit::available) check(audit::selfTest(),"Allocation auditor failed deliberate controls");
    for (int rate:{44100,48000}) for (auto treatment:{Treatment::native,Treatment::shared})
    {
        Settings s; s.engine.rate=rate; s.treatment=treatment;
        Processor p(s,transport); check(p.latencySamples()==rate/10,"Reported latency mismatch");
        check(p.post(pitch(0,220)),"Oracle initial frame rejected");
        Event target; target.kind=Event::Kind::targets; target.targetMidi={45,64,69}; check(p.post(target),"Targets rejected");
        p.start(); check(!p.configureStopped(s) && !p.resetStopped(),"Live reconfiguration/reset permitted");
        std::vector<float> input(static_cast<std::size_t>(rate/2));
        for (std::size_t i=0;i<input.size();++i) input[i]=static_cast<float>(.1*std::sin(6.283185307179586*220*i/rate));
        input[0]=-0.0f;
        std::array<double,3> previous {};
        std::size_t allocations=0;
        audit::begin();
        for (std::size_t i=0;i<input.size();++i)
        {
            const auto out=p.push(input[i]);
            check(std::bit_cast<std::uint32_t>(out.leadDirect)==std::bit_cast<std::uint32_t>(input[i]),"Direct lead PCM changed");
            const auto source=static_cast<std::int64_t>(i)-p.latencySamples();
            check(out.leadAligned==(source>=0?input[static_cast<std::size_t>(source)]:0),"Aligned lead delay/null mismatch");
            check(std::abs(out.sumAligned-out.leadAligned-(out.voices[0]+out.voices[1]+out.voices[2])/3)<1e-7,"Sum/headroom gain invariant failed");
            if (source>rate/20)
                for (float voice:out.voices) check(std::abs(voice-out.leadAligned)<1e-7,"Transport voice/source alignment mismatch");
            Telemetry t;
            while (p.readTelemetry(t)) if (t.kind==Telemetry::Kind::control)
            {
                const auto v=static_cast<std::size_t>(t.voice);
                check(std::abs(t.appliedShift-previous[v])<=2400.0*128/rate+1e-8,"Ratio ramp is unbounded");
                previous[v]=t.appliedShift;
                check(t.frameAvailable<=t.wall+1,"Future F0 used before availability");
                const std::array<double,3> expected {-12,7,12};
                if (t.source>rate/20) check(std::abs(t.appliedShift-expected[v])<1e-8,"Independent prescribed voice target assignment failed");
            }
        }
        allocations=audit::end();
        if (audit::available) check(allocations==0,"Interaction adapter/selector allocated in render");
        check(p.stats().underflows==std::array<std::uint64_t,3>{} && p.stats().lateControls==0 && p.stats().missingMetadata==0,"Sufficient-reserve transport failed");
        p.stop(); check(p.resetStopped(),"Stopped reset rejected"); p.start();
        for (int i=0;i<rate/3;++i) check(p.push(0).sumAligned==0,"Reset leaked prior audio");
        p.stop();
    }
}
void controlsAndPolicy()
{
    Settings s; s.treatment=Treatment::shared;
    Processor p(s,transport); p.start();
    // Explicit unvoiced dry budget: one third of the source in the COMPLETE wet
    // sum, not three full-gain unshifted consonant copies.
    for (int i=0;i<12000;++i)
    {
        const auto out=p.push(.1f);
        if (i>7000) check(std::abs(out.sumAligned-(.1f+.1f/3))<1e-7,"Shared consonant budget reinforced three copies");
        Telemetry t; while (p.readTelemetry(t)) {}
    }
    p.stop();
    s.profile=Profile::live; s.mode=Mode::livePrescribed;
    check(p.configureStopped(s),"Stopped profile replacement rejected"); p.start();
    for (int i=0;i<12000;++i) { p.push(0); Telemetry t; while(p.readTelemetry(t)) {} }
    check(p.stats().underflows[0]>0 && p.stats().missingMetadata>0,"Insufficient live reserve was hidden"); p.stop();
    s.profile=Profile::mix; s.mode=Mode::oraclePrescribed;
    check(p.configureStopped(s),"Stopped mode replacement rejected");
    auto late=pitch(0,220); late.available=9000; check(p.post(late),"Late oracle rejected before render"); p.start();
    for (int i=0;i<15000;++i) { p.push(0); Telemetry t; while(p.readTelemetry(t)) {} }
    check(p.stats().lateControls>0,"Late oracle was backdated into an on-time pass"); p.stop();
}
void concurrency()
{
    Queue<std::uint64_t,17> queue;
    std::thread producer([&] { for (std::uint64_t i=0;i<100000;++i) while (!queue.push(i)) std::this_thread::yield(); });
    for (std::uint64_t i=0;i<100000;++i) { std::uint64_t value=0; while (!queue.pop(value)) std::this_thread::yield(); check(value==i,"SPSC ordering/loss"); }
    producer.join();
    Settings s; s.mode=Mode::midi;
    Processor p(s,transport); p.start();
    std::atomic<bool> done {false};
    std::thread automation([&]
    {
        for (unsigned i=0;i<1000;++i)
        {
            Event e; e.kind=Event::Kind::midi; e.available=e.source=i*5;
            e.bytes={static_cast<std::uint8_t>(i%2?0x80:0x90),60,100};
            p.post(e); // Overflow is deliberately a fail-closed input, not blocking render.
        }
    });
    std::thread consumer([&] { Telemetry t; while (!done.load(std::memory_order_acquire)) { while (p.readTelemetry(t)) {} std::this_thread::yield(); } while (p.readTelemetry(t)) {} });
    for (int i=0;i<30000;++i) p.push(0);
    automation.join(); p.stop(); done.store(true,std::memory_order_release); consumer.join();
    check(p.resetStopped(),"Joined state handoff failed");
}
void malformedControls()
{
    Settings s; Processor p(s,transport); p.start();
    auto future=pitch(0,220); future.pitch.end=1000;
    check(p.post(future),"Malformed control could not reach validation");
    voxide::audit::begin();
    for (int i=0;i<12000;++i) { const auto out=p.push(.1f); check(std::isfinite(out.sumAligned),"Malformed control produced nonfinite audio"); Telemetry t; while(p.readTelemetry(t)) {} }
    const auto allocations=voxide::audit::end();
    check(p.stats().badEvents>0,"Future oracle frame was accepted");
    if (voxide::audit::available) check(allocations==0,"Malformed control handling allocated on render");
    p.stop(); check(p.resetStopped(),"Malformed epoch reset failed");
    Event invalid; invalid.kind=Event::Kind::harmony; invalid.harmony.root=99;
    check(p.post(invalid),"Malformed harmony could not reach validation"); p.start();
    voxide::audit::begin();
    for (int i=0;i<1000;++i) p.push(0);
    const auto invalidAllocations=voxide::audit::end();
    check(p.stats().badEvents>0,"Malformed harmony accepted");
    if (voxide::audit::available) check(invalidAllocations==0,"Malformed harmony allocated/raised on render");
    p.stop();
}
void completeModes()
{
    for (auto mode : {Mode::livePrescribed,Mode::scale,Mode::midi})
    {
        Settings s; s.mode=mode; Processor p(s,transport);
        Event targets; targets.kind=Event::Kind::targets; targets.targetMidi={52,64,69}; check(p.post(targets),"Prescribed handoff failed");
        for (std::uint8_t note : {52,64,69}) { Event e; e.kind=Event::Kind::midi; e.bytes={0x90,note,100}; check(p.post(e),"MIDI handoff failed"); }
        if (mode==Mode::scale)
        {
            Event e; e.kind=Event::Kind::harmony; e.source=e.available=9600;
            e.harmony.degrees={0,0,0}; e.harmony.octaves={-1,0,1}; check(p.post(e),"Harmony automation handoff failed");
        }
        p.start(); std::array<unsigned,3> observed {};
        for (int i=0;i<24000;++i)
        {
            p.push(static_cast<float>(.1*std::sin(6.283185307179586*220*i/48000)));
            Telemetry t;
            while (p.readTelemetry(t)) if (t.kind==Telemetry::Kind::control && t.source>7200 && t.voiced)
            {
                const auto v=static_cast<std::size_t>(t.voice);
                if (mode==Mode::scale && t.source>=9600 && t.source<11000) continue; // bounded ramp, not a stale-target pass
                const std::array<double,3> expected=mode==Mode::scale
                    ? (t.source>=11000?std::array<double,3>{-12,0,12}:std::array<double,3>{3,7,12})
                    :std::array<double,3>{-5,7,12};
                check(t.active && std::abs(t.appliedShift-expected[v])<.05,"Complete tracker/selector/voice assignment mismatch");
                ++observed[v];
            }
        }
        for (auto n:observed) check(n>20,"Complete mode never produced three voiced controls");
        p.stop();
    }
}
}
int main() { contracts(); controlsAndPolicy(); concurrency(); malformedControls(); completeModes(); std::cout<<"Three-voice transport, lead null, ramps, policy, lifecycle and SPSC contracts passed\n"; }
