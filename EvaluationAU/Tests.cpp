#include "Processor.h"
#include "../Source/Tests/AllocationAudit.h"
#include <bit>
#include <chrono>
#include <cmath>
#include <cstring>
#include <iostream>
#include <stdexcept>

namespace voxide::evaluation
{
class SessionTestAccess
{
public:
    static const void* active(const Session& s) { return s.active; }
    static bool idle(Session& s)
    {
        return s.waitIdleForTest();
    }
};
class ProcessorTestAccess
{
public:
    static bool idle(Processor& p) { return !p.session || SessionTestAccess::idle(*p.session); }
    static const void* active(const Processor& p) { return p.session?SessionTestAccess::active(*p.session):nullptr; }
};
}

namespace
{
using namespace voxide;
using evaluation::Processor;
std::thread::id owner;
std::atomic<int> wrongOwner {0},living {0};
std::atomic<bool> badOutput {false};
void require(bool value,const char* text) { if (!value) throw std::runtime_error(text); }
bool sameFloat(float a,float b) { return std::bit_cast<std::uint32_t>(a)==std::bit_cast<std::uint32_t>(b); }
void nativeOwner() { if (std::this_thread::get_id()==owner) ++wrongOwner; }
class Fake final : public engines::Engine
{
public:
    Fake() { nativeOwner(); ++living; }
    ~Fake() override { nativeOwner(); --living; }
    engines::Info info() const noexcept override { nativeOwner(); return {0,0,0,0,128,0,3}; }
    void control(double r,double) override { nativeOwner(); ratio=r; }
    void process(const float* source,int count) override
    {
        nativeOwner(); require(pending==0,"Fake input not drained");
        for (int i=0;i<count;++i) audio[static_cast<std::size_t>(i)]=badOutput.load()?std::numeric_limits<float>::quiet_NaN():static_cast<float>(source[i]*ratio);
        read=0; pending=count;
    }
    int available() const override { nativeOwner(); return pending; }
    int retrieve(float* out,int n) override
    { nativeOwner(); require(n>0 && n<=pending,"Fake over-read"); std::copy_n(audio.data()+read,n,out); read+=n; pending-=n; return n; }
    void finish() override { nativeOwner(); }
    void reset(double,double) override { throw std::logic_error("No native reset"); }
private:
    std::array<float,128> audio {};
    int pending=0,read=0;
    double ratio=1;
};
std::unique_ptr<engines::Engine> fake(engines::Config,double,double) { return std::make_unique<Fake>(); }
void parameter(Processor& p,int index,float normalized) { p.getParameters()[index]->setValueNotifyingHost(normalized); }
void callback(Processor& p,juce::AudioBuffer<float>& buffer,bool bypass=false)
{
    juce::MidiBuffer midi;
    audit::begin();
    if (bypass) p.processBlockBypassed(buffer,midi); else p.processBlock(buffer,midi);
    const auto count=audit::end();
    if (audit::available) require(count==0,"Evaluation callback allocated");
}
void leadAndState()
{
    for (int rate:{44100,48000})
    {
        Processor p(fake); parameter(p,2,0); p.prepareToPlay(rate,512);
        require(p.getLatencySamples()==rate/10,"Wrong latency declaration");
        require(p.getParameters().size()==4 && !p.acceptsMidi(),"Wrong prototype control contract");
        std::vector<float> source(static_cast<std::size_t>(rate/2));
        for (std::size_t i=0;i<source.size();++i) source[i]=static_cast<float>(.02*std::sin(6.283185307179586*220*static_cast<double>(i)/rate));
        int position=0;
        for (int partition:{1,32,128,257,512})
        {
            juce::AudioBuffer<float> buffer(2,partition);
            for (int pass=0;pass<12;++pass)
            {
                require(evaluation::ProcessorTestAccess::idle(p),"Fake coordinator failed");
                for (int i=0;i<partition;++i) { buffer.setSample(0,i,source[static_cast<std::size_t>(position+i)%source.size()]); buffer.setSample(1,i,.7f); }
                callback(p,buffer,pass%2==0);
                for (int i=0;i<partition;++i)
                {
                    const int input=position+i-rate/10;
                    const float expected=input<0?0.f:source[static_cast<std::size_t>(input)%source.size()];
                    require(sameFloat(buffer.getSample(0,i),expected) && sameFloat(buffer.getSample(1,i),expected),"Lead/bypass alignment or stereo alias failure");
                }
                position+=partition;
            }
        }
        parameter(p,0,5.f/11); parameter(p,1,.5f); parameter(p,3,.3f);
        juce::MemoryBlock state,after; p.getStateInformation(state);
        Processor restored(fake); restored.setStateInformation(state.getData(),static_cast<int>(state.getSize())); restored.getStateInformation(after);
        require(state==after,"Evaluation state roundtrip failed");
        auto broken=state; static_cast<unsigned char*>(broken.getData())[broken.getSize()-1]=0xff;
        restored.setStateInformation(broken.getData(),static_cast<int>(broken.getSize())); restored.getStateInformation(after);
        require(state==after,"Malformed state partially applied");
        restored.setStateInformation(state.getData(),static_cast<int>(state.getSize())-1); restored.getStateInformation(after);
        require(state==after,"Truncated state changed parameters");
        p.releaseResources();
    }
}
void modesAndReset()
{
    Processor p(fake); p.prepareToPlay(48000,128);
    auto layout=p.getBusesLayout(); layout.inputBuses.set(0,juce::AudioChannelSet::stereo());
    require(p.setBusesLayout(layout),"Stereo main rejected");
    layout.outputBuses.set(0,juce::AudioChannelSet::mono()); require(!p.isBusesLayoutSupported(layout),"Mono output incorrectly accepted");
    juce::AudioBuffer<float> buffer(2,128); buffer.clear();
    for (int i=0;i<24;++i)
    {
        audit::begin();p.reset();require(audit::end()==0,"Reset requested synchronous destruction");
        callback(p,buffer);
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    p.setNonRealtime(true);callback(p,buffer);
    require(p.status().status==evaluation::Session::Status::offlineUnsupported,"Offline mode was mislabeled supported");
    p.setNonRealtime(false);callback(p,buffer);
    for (int i=0;i<50 && p.status().status!=evaluation::Session::Status::ready;++i)
    { std::this_thread::sleep_for(std::chrono::milliseconds(2));callback(p,buffer); }
    require(p.status().status==evaluation::Session::Status::ready,"Fresh spare was not replenished");
    p.releaseResources();p.prepareToPlay(96000,128);callback(p,buffer);
    require(p.status().status==evaluation::Session::Status::unsupportedRate && p.getLatencySamples()==9600,"Unsupported rate not explicit");
    p.releaseResources();
}
void transportContinuity()
{
    struct Head final : juce::AudioPlayHead
    {
        bool known=true;
        std::int64_t frame=0;
        juce::Optional<PositionInfo> getPosition() const override
        {
            if (!known) return {};
            PositionInfo info;info.setTimeInSamples(frame);info.setIsPlaying(true);return info;
        }
    } head;
    Processor p(fake);p.prepareToPlay(48000,128);p.setPlayHead(&head);
    juce::AudioBuffer<float> buffer(2,128);buffer.clear();callback(p,buffer);
    const auto* initial=evaluation::ProcessorTestAccess::active(p);
    head.known=false;callback(p,buffer);
    head.known=true;head.frame=256;callback(p,buffer);
    require(evaluation::ProcessorTestAccess::active(p)==initial,"Unknown host position caused a false discontinuity");
    head.frame=0;callback(p,buffer);
    require(evaluation::ProcessorTestAccess::active(p)!=initial,"Actual seek did not swap to a pristine graph");
    p.releaseResources();
}
void nativeSmoke()
{
    using Clock=std::chrono::steady_clock;
    for (int rate:{44100,48000})
    {
        Processor p; p.prepareToPlay(rate,128);
        juce::AudioBuffer<float> buffer(2,128); bool heard=false;
        const auto start=Clock::now();
        for (int begin=0;begin<rate*2;begin+=128)
        {
            std::this_thread::sleep_until(start+std::chrono::nanoseconds(static_cast<std::uint64_t>(begin)*1000000000ull/static_cast<unsigned>(rate)));
            for (int i=0;i<128;++i) buffer.setSample(0,i,static_cast<float>(.02*std::sin(6.283185307179586*220*(begin+i)/rate)));
            callback(p,buffer);
            for (int i=0;i<128;++i)
            {
                const int at=begin+i-rate/10;
                const float dry=at<0?0.f:static_cast<float>(.02*std::sin(6.283185307179586*220*at/rate));
                require(std::isfinite(buffer.getSample(0,i)) && sameFloat(buffer.getSample(0,i),buffer.getSample(1,i)),"Invalid native output");
                if (at>rate/2 && std::abs(buffer.getSample(0,i)-dry)>1e-4f) heard=true;
            }
        }
        require(heard && p.status().status==evaluation::Session::Status::ready && p.status().active==7,"Native prototype did not produce all three harmonies");
        p.releaseResources();
    }
}
void faultCloses()
{
    Processor p(fake);p.prepareToPlay(48000,128);badOutput.store(true);
    juce::AudioBuffer<float> buffer(2,128);
    for (int block=0;block<80;++block)
    {
        for (int i=0;i<128;++i) buffer.setSample(0,i,.01f);
        callback(p,buffer);std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    require(p.status().status==evaluation::Session::Status::failed && p.status().active==0,"Native fault was hidden");
    for (int i=0;i<128;++i) require(sameFloat(buffer.getSample(0,i),.01f),"Fault changed the lead or leaked wet output");
    p.releaseResources();badOutput.store(false);
}
void advertisedPacketSurvivesWorkerFailure()
{
    auto engine=std::make_unique<worker::Engine>(engines::Config{48000,1,128},1,220,fake,worker::Engine::Options{});
    std::array<float,128> input {},output {};input.fill(.01f);
    engine->process(input.data(),128);require(engine->waitIdle(),"Initial worker packet not ready");
    require(engine->available()==128,"Missing advertised packet");
    badOutput.store(true);engine->process(input.data(),128);
    require(!engine->waitIdle(),"Injected worker failure missing");engine->finish();
    audit::begin();const int count=engine->available();const int received=engine->retrieve(output.data(),count);
    const auto allocations=audit::end();
    require(count==128 && received==128 && !engine->healthy(),"Worker failure invalidated an advertised packet");
    if (audit::available) require(allocations==0,"Failure retrieval allocated on callback");
    engine.reset();badOutput.store(false);
}
}
int main(int argc,char** argv)
{
    try
    {
        owner=std::this_thread::get_id();
        if (audit::available) require(audit::selfTest(),"Allocation detector unavailable");
        if (argc==2 && std::string(argv[1])=="--native") nativeSmoke();
        else { require(argc==1,"Unknown test mode"); leadAndState(); modesAndReset(); transportContinuity(); faultCloses(); advertisedPacketSurvivesWorkerFailure(); require(wrongOwner==0 && living==0,"Native ownership escaped worker"); }
        std::cout<<"Evaluation processor checks passed; no device, playback, installation or Logic operation\n";
        return 0;
    }
    catch (const std::exception& e) { audit::end();std::cerr<<e.what()<<'\n';return 1; }
}
