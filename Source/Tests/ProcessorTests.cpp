#include "PluginProcessor.h"
#include "DiagnosticsTests.h"
#include "StudioTestSupport.h"
#include "AllocationAudit.h"
#include <bit>
#include <iostream>
#include <stdexcept>
#include <cstring>
void runTrackingProcessorTests();
void runStudioUiTests();
void runStateRecoveryTests();
void runBounceTests(bool);

namespace
{
using voxide::Processor;
void require(bool value,const char* message) { if (!value) throw std::runtime_error(message); }
bool same(float a,float b) { return std::bit_cast<std::uint32_t>(a)==std::bit_cast<std::uint32_t>(b); }
void set(Processor& p,const juce::String& id,float value)
{
    for (auto* base:p.getParameters()) if (auto* parameter=dynamic_cast<juce::RangedAudioParameter*>(base);parameter && parameter->paramID==id)
    { parameter->setValueNotifyingHost(parameter->convertTo0to1(value));return; }
    throw std::runtime_error("Missing parameter");
}
float signal(int at,int rate) { return static_cast<float>(.02*std::sin(6.283185307179586*220*at/rate)); }
void callback(Processor& p,juce::AudioBuffer<float>& audio,bool bypass=false)
{
    juce::MidiBuffer midi;voxide::audit::begin();
    if (bypass) p.processBlockBypassed(audio,midi);else p.processBlock(audio,midi);
    const auto n=voxide::audit::end();if (voxide::audit::available) require(n==0,"Product callback allocated");
    require(midi.isEmpty(),"Product emitted MIDI");
}
void dryRouting()
{
    for (int rate:{44100,48000}) for (bool side:{false,true})
    {
        Processor p(studioTest::factory);auto layout=p.getBusesLayout();layout.inputBuses.set(1,juce::AudioChannelSet::mono());
        require(p.setBusesLayout(layout),"Sidechain layout rejected");set(p,"sourceBus",side?1.f:0.f);
        for (int v=1;v<=3;++v) set(p,"voiceEnabled"+juce::String(v),0);
        p.prepareToPlay(rate,512);require(p.getLatencySamples()==rate/10,"Product latency wrong");
        int at=0;
        for (int frames:{1,32,64,128,257,512,1024})
        {
            juce::AudioBuffer<float> audio(2,frames);
            for (int pass=0;pass<16;++pass)
            {
                require(p.waitIdleForTest(),"Fake worker not idle");
                auto input=p.getBusBuffer(audio,true,side?1:0);audio.clear();
                for (int i=0;i<frames;++i) input.setSample(0,i,signal(at+i,rate));
                if (pass==4) p.requestRestart();
                if (pass==6) { juce::MemoryBlock state;p.getStateInformation(state);p.setStateInformation(state.getData(),static_cast<int>(state.getSize())); }
                const bool bypass=pass%2==0;if (bypass) p.reset();
                callback(p,audio,bypass);
                for (int i=0;i<frames;++i)
                {
                    const float expected=at+i<rate/10?0.f:signal(at+i-rate/10,rate);
                    require(same(audio.getSample(0,i),expected) && same(audio.getSample(1,i),expected),"Aligned original/source/bypass changed");
                }
                at+=frames;
            }
        }
        p.setNonRealtime(true);juce::AudioBuffer<float> b(2,128);b.clear();callback(p,b);
        require(p.studioStatus().status==voxide::studio::Status::ready,"Offline coordinator failed");
        p.setNonRealtime(false);set(p,"harmonyMode",1);callback(p,b);
        require(p.studioStatus().status==voxide::studio::Status::midiUnsupported,"Legacy MIDI mode falsely supported");
    }
}
void stateMigration()
{
    Processor p(studioTest::factory);require(p.getParameters().size()==30,"Parameter layout changed");
    constexpr char v3[]="voxide-tracking-v3";
    juce::MemoryBlock old(sizeof(v3)+23*sizeof(float),true);std::memcpy(old.getData(),v3,sizeof(v3));
    auto* bytes=static_cast<unsigned char*>(old.getData())+sizeof(v3);
    for (int i=0;i<23;++i)
    {
        const auto bits=std::bit_cast<std::uint32_t>(p.getParameters()[i]->getDefaultValue());
        for (unsigned j=0;j<4;++j) *bytes++=static_cast<unsigned char>(bits>>(8*j));
    }
    p.setStateInformation(old.getData(),static_cast<int>(old.getSize()));
    for (int i:{23,25,27}) require(same(p.getParameters()[i]->getValue(),0.f),"Legacy dry session enabled harmonies");
    juce::MemoryBlock installed,after;p.getStateInformation(installed);
    set(p,"scaleRoot",9);set(p,"scaleSet",1);set(p,"voiceEnabled1",1);
    juce::MemoryBlock malformed;p.getStateInformation(malformed);
    static_cast<unsigned char*>(malformed.getData())[malformed.getSize()-1]=0xff;
    p.setStateInformation(installed.getData(),static_cast<int>(installed.getSize()));
    p.setStateInformation(malformed.getData(),static_cast<int>(malformed.getSize()));p.getStateInformation(after);
    require(after==installed,"Malformed state partially applied");
    constexpr char eval[]="voxide-studio-eval-v1";p.setStateInformation(eval,sizeof(eval));p.getStateInformation(after);
    require(after==installed,"Evaluation state silently reinterpreted");
    constexpr char v1[]="voxide-shell-v1";
    auto distinct=[&]
    {
        set(p,"sourceBus",1);set(p,"scaleRoot",9);set(p,"scaleSet",1);
        set(p,"voiceEnabled1",1);set(p,"voiceLevel1",-6);set(p,"originalLevel",-12);
    };
    distinct(); // A no-op v1 implementation must not satisfy the defaults check.
    p.setStateInformation(v1,sizeof(v1));
    require(same(p.getParameters()[0]->getValue(),0.f),"v1 default routing changed");
    for (int i=0;i<30;++i)
    {
        const float expected=(i==23 || i==25 || i==27)?0.f:p.getParameters()[i]->getDefaultValue();
        require(same(p.getParameters()[i]->getValue(),expected),"v1 migration changed defaults or enabled harmonies");
    }
    distinct();juce::MemoryBlock nondefault;p.getStateInformation(nondefault);
    p.setStateInformation(v1,sizeof(v1)-1);p.getStateInformation(after);require(after==nondefault,"Truncated v1 state changed settings");
}
void layoutContracts()
{
    for (int mainChannels:{1,2}) for (int sideChannels:{0,1,2}) for (bool selectedSide:{false,true})
    {
        Processor p(studioTest::factory);auto layout=p.getBusesLayout();
        layout.inputBuses.set(0,juce::AudioChannelSet::canonicalChannelSet(mainChannels));
        layout.inputBuses.set(1,juce::AudioChannelSet::canonicalChannelSet(sideChannels));
        require(p.setBusesLayout(layout),"Legacy mono/stereo bus layout lost");
        auto invalid=layout;invalid.outputBuses.set(0,juce::AudioChannelSet::mono());require(!p.isBusesLayoutSupported(invalid),"Mono output accepted");
        invalid=layout;invalid.inputBuses.set(1,juce::AudioChannelSet::create5point1());require(!p.isBusesLayoutSupported(invalid),"Surround sidechain accepted");
        set(p,"sourceBus",selectedSide?1.f:0.f);for (int v=1;v<=3;++v) set(p,"voiceEnabled"+juce::String(v),0);
        p.prepareToPlay(48000,257);juce::AudioBuffer<float> audio(std::max(2,p.getTotalNumInputChannels()),257);
        auto inputSignal=[&](int frame) { return selectedSide?(sideChannels?.5f*signal(frame,48000):0.f):signal(frame,48000); };
        for (int at=0;at<7000;at+=257)
        {
            require(p.waitIdleForTest(),"Routing variant worker failed");audio.clear();
            auto main=p.getBusBuffer(audio,true,0),side=p.getBusBuffer(audio,true,1);
            for (int i=0;i<257;++i)
            {
                main.setSample(0,i,signal(at+i,48000));if (mainChannels==2) main.setSample(1,i,.7f);
                if (sideChannels) side.setSample(0,i,.5f*signal(at+i,48000));if (sideChannels==2) side.setSample(1,i,-.7f);
            }
            callback(p,audio);require(p.studioStatus().status==voxide::studio::Status::ready,"Routing variant silently accepted fault");
            for (int i=0;i<257;++i)
            {
                const auto expected=at+i<4800?0.f:inputSignal(at+i-4800);
                require(same(audio.getSample(0,i),expected) && same(audio.getSample(1,i),expected),"Stereo routing/downmix/silent-sidechain contract changed");
            }
        }
    }
}
void voicesAndFaults()
{
    studioTest::markers.store(true);
    for (int silent:{-1,0,1,2})
    {
        studioTest::ordinal.store(0);studioTest::silent.store(silent);
        Processor p(studioTest::factory);p.prepareToPlay(48000,128);juce::AudioBuffer<float> audio(2,128);
        for (int at=0;at<48000;at+=128)
        {
            require(p.waitIdleForTest(),"Marker worker failed");
            for (int i=0;i<128;++i) audio.setSample(0,i,signal(at+i,48000));callback(p,audio);
            if (at>40000) for (int i=0;i<128;++i)
            {
                double wet=0;for (int v=0;v<3;++v) if (v!=silent) wet+=studioTest::marker[static_cast<std::size_t>(v)]/3.;
                require(std::abs(audio.getSample(0,i)-signal(at+i-4800,48000)-wet)<1e-7,"Individual product voice missing");
            }
        }
        require(p.studioStatus().status==voxide::studio::Status::ready && p.studioStatus().active==7,"Voice controls inactive");
        set(p,"voiceEnabled2",0);set(p,"voiceLevel1",-6);set(p,"originalLevel",-60);
        for (int block=0;block<12;++block)
        { require(p.waitIdleForTest(),"Mixer worker failed");for (int i=0;i<128;++i) audio.setSample(0,i,signal(48000+block*128+i,48000));callback(p,audio); }
        const double expected=((silent==0?0:studioTest::marker[0])*std::pow(10.,-6./20)+(silent==2?0:studioTest::marker[2]))/3.;
        for (int i=0;i<128;++i) require(std::abs(audio.getSample(0,i)-expected)<1e-7,"Voice/original mixer controls ignored");
    }
    studioTest::markers.store(false);studioTest::silent.store(-1);
    Processor p(studioTest::factory);p.prepareToPlay(48000,128);studioTest::nonfinite.store(true);
    juce::AudioBuffer<float> b(2,128);
    for (int block=0;block<64;++block)
    {
        for (int i=0;i<128;++i) b.setSample(0,i,.01f);callback(p,b);std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    require(p.studioStatus().status==voxide::studio::Status::failed && p.studioStatus().active==0,"Native fault not latched");
    for (int i=0;i<128;++i) require(same(b.getSample(0,i),.01f),"Fault changed original");
    p.releaseResources();studioTest::nonfinite.store(false);
}
void rangeAndFiniteContracts()
{
    {
        Processor unsupported(studioTest::factory);unsupported.prepareToPlay(96000,128);
        juce::AudioBuffer<float> audio(2,128);audio.clear();callback(unsupported,audio);
        require(unsupported.getLatencySamples()==9600 && unsupported.studioStatus().status==voxide::studio::Status::unsupportedRate,"Unsupported rate falsely qualified");
    }
    voxide::studio::Session session(48000,studioTest::factory);voxide::HarmonyConfig config;
    config.degrees={0,0,0};config.octaves={-1,0,1};
    for (int at=0;at<24064;at+=128)
    {
        require(session.waitIdleForTest(),"Boundary worker failed");
        if (at==16384) config.octaves[2]=2;
        session.begin(config,voxide::TrackerVariant::multiCandidate,false,false);
        for (int i=0;i<128;++i)
        {
            const auto voices=session.push(signal(at+i,48000));
            if (at>10000 && at<16000) for (std::size_t v=0;v<3;++v)
                require(std::abs(voices[v]-signal(at+i-4800,48000)*std::exp2(static_cast<float>(config.octaves[v])))<1e-7f,"Inclusive +/-12 voice or source alignment incorrect");
            if (at>22000) require(juce::exactlyEqual(voices[2],0.f),"Out-of-range voice was clamped into audible output");
        }
    }
    require(session.snapshot().status==voxide::studio::Status::ready && session.snapshot().active==3,"Boundary/out-of-range policy not explicit");
    for (int mode=0;mode<3;++mode)
    {
        Processor p(studioTest::factory);if (mode==1) for (int v=1;v<=3;++v) set(p,"voiceEnabled"+juce::String(v),0);
        p.prepareToPlay(48000,128);studioTest::large.store(std::numeric_limits<float>::max()*.9f);
        juce::AudioBuffer<float> audio(2,128);bool fault=false;
        const double amplitude=mode==2?static_cast<double>(std::numeric_limits<float>::max())*.75:.02;
        for (int at=0;at<24064;at+=128)
        {
            if (!fault) require(p.waitIdleForTest(),"Finite native worker failed");
            for (int i=0;i<128;++i) audio.setSample(0,i,static_cast<float>(amplitude*std::sin(6.283185307179586*220*(at+i)/48000)));
            callback(p,audio);
            const bool failed=p.studioStatus().status==voxide::studio::Status::failed;require(!fault || failed,"Overflow fault unlatched");
            for (int i=0;i<128;++i)
            {
                require(std::isfinite(audio.getSample(0,i)),"Nonfinite product mix escaped");
                if (fault || mode==1)
                {
                    const int source=at+i-4800;
                    const float dry=source<0?0.f:static_cast<float>(amplitude*std::sin(6.283185307179586*220*source/48000));
                    require(same(audio.getSample(0,i),dry),"Finite fallback/zero wet changed lead");
                }
            }
            fault=failed;
        }
        require(mode==2?fault:!fault,"Finite accumulation/final overflow status wrong");p.releaseResources();studioTest::large.store(0);
    }
}
}
int main(int argc,char** argv)
{
    try
    {
        studioTest::renderThread=true;
        if (argc==2 && juce::String(argv[1])=="--ui") { runStudioUiTests();return 0; }
        if (argc==2 && juce::String(argv[1])=="--bounce-native") { runBounceTests(true);return 0; }
        require(argc==1,"Unknown product test mode");
        if (voxide::audit::available) require(voxide::audit::selfTest(),"Allocation detector failed");
        runDiagnosticsTests();runTrackingProcessorTests();dryRouting();layoutContracts();stateMigration();voicesAndFaults();rangeAndFiniteContracts();runStateRecoveryTests();runBounceTests(false);
        require(studioTest::wrongOwner.load()==0 && studioTest::living.load()==0,"Native ownership/lifetime escaped worker");
        std::cout<<"PR07 product contracts passed; no install, private audio, device or Logic\n";return 0;
    }
    catch (const std::exception& e) { voxide::audit::end();std::cerr<<e.what()<<'\n';return 1; }
}
