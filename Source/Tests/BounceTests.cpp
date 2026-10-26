#include "PluginProcessor.h"
#include "StudioTestSupport.h"
#include "AllocationAudit.h"
#include <bit>
#include <iostream>
void runBounceTests(bool native);

namespace
{
void require(bool value,const char* text) { if (!value) throw std::runtime_error(text); }
void set(voxide::Processor& p,const char* id,float value)
{
    for (auto* base:p.getParameters()) if (auto* parameter=dynamic_cast<juce::RangedAudioParameter*>(base);parameter && parameter->paramID==id)
    { parameter->setValueNotifyingHost(parameter->convertTo0to1(value));return; }
    throw std::runtime_error("Bounce parameter missing");
}
float signal(int at,int rate)
{
    if (at>=rate || (at>=rate/3 && at<rate/3+rate/20)) return 0;
    // Deliberately nonzero first sample and separate second phrase; synthetic only.
    return at==0?.01f:static_cast<float>(.02*std::sin(6.283185307179586*(at<rate/2?220:330)*at/rate));
}
struct Capture { std::vector<float> audio;bool wet=false;unsigned active=0; };
Capture capture(int rate,bool offline,bool native,const std::vector<int>& partitions,bool dry=false)
{
    voxide::Processor p(native?voxide::studio::createNative:studioTest::factory);
    if (dry) for (const auto* id:{"voiceEnabled1","voiceEnabled2","voiceEnabled3"}) set(p,id,0);
    p.setNonRealtime(offline);p.prepareToPlay(rate,1024);
    require(p.getLatencySamples()==rate/10,"Bounce latency changed");
    Capture result;const int total=rate+rate*6/10;
    const std::array<int,4> events {6144,12288,18432,24576};std::size_t next=0,partition=0;
    const auto epoch=std::chrono::steady_clock::now();
    for (int at=0;at<total;)
    {
        if (next<events.size() && at==events[next])
        {
            if (next==0) { set(p,"scaleRoot",5);set(p,"scaleSet",1); }
            if (next==1) set(p,"voiceDegree1",-2);
            if (next==2 && !dry) set(p,"voiceLevel2",-6);
            if (next==3) { juce::MemoryBlock saved;p.getStateInformation(saved);p.setStateInformation(saved.getData(),static_cast<int>(saved.getSize())); }
            ++next;
        }
        if (!offline)
        {
            if (native) std::this_thread::sleep_until(epoch+std::chrono::nanoseconds(static_cast<std::uint64_t>(at)*1000000000ull/static_cast<unsigned>(rate)));
            else require(p.waitIdleForTest(),"Realtime fake worker failed");
        }
        int n=std::min(partitions[partition++%partitions.size()],total-at);
        if (next<events.size()) n=std::min(n,events[next]-at);
        require(n>0,"Invalid bounce partition");juce::AudioBuffer<float> audio(2,n);juce::MidiBuffer midi;
        for (int i=0;i<n;++i) audio.setSample(0,i,signal(at+i,rate));
        const auto waits=voxide::studio::Worker::waitCallsOnThreadForTest();voxide::audit::begin();p.processBlock(audio,midi);
        const auto allocations=voxide::audit::end();
        if (!offline)
        {
            require(voxide::studio::Worker::waitCallsOnThreadForTest()==waits,"Realtime callback waited for workers");
            if (voxide::audit::available) require(allocations==0,"Realtime bounce callback allocated");
        }
        require(p.studioStatus().status==voxide::studio::Status::ready,"Dry/failed bounce was accepted as harmonized");
        result.active|=p.studioStatus().active;
        for (int i=0;i<n;++i)
        {
            const float value=audio.getSample(0,i);
            require(std::isfinite(value) && std::bit_cast<std::uint32_t>(value)==std::bit_cast<std::uint32_t>(audio.getSample(1,i)),"Invalid bounce/stereo output");
            const float lead=at+i<rate/10?0.f:signal(at+i-rate/10,rate);
            if (dry) require(std::bit_cast<std::uint32_t>(value)==std::bit_cast<std::uint32_t>(lead),"First-sample/tail/aligned-original mismatch");
            if (at>rate/2 && at<rate && std::abs(value-lead)>1e-4f) result.wet=true;
            result.audio.push_back(value);
        }
        at+=n;
    }
    require(result.audio.size()==static_cast<std::size_t>(total),"Bounce shortened duration/tail");
    for (int at=total-rate/10;at<total;++at) require(std::abs(result.audio[static_cast<std::size_t>(at)])<1e-6f,"Bounce tail did not clear");
    require(dry || (result.wet && result.active==7),"Harmony bounce passed with silent/inactive voices");
    return result;
}
void offlineResets()
{
    voxide::Processor p(studioTest::factory);p.setNonRealtime(true);
    for (const auto* id:{"voiceEnabled1","voiceEnabled2","voiceEnabled3"}) set(p,id,0);
    p.prepareToPlay(48000,128);juce::AudioBuffer<float> audio(2,128);juce::MidiBuffer midi;
    for (int block=0;block<80;++block)
    {
        if (block<12) p.requestRestart();
        for (int i=0;i<128;++i) audio.setSample(0,i,signal(block*128+i,48000));
        p.processBlock(audio,midi);require(p.studioStatus().status==voxide::studio::Status::ready,"Fast offline resets exhausted spare without synchronization");
        for (int i=0;i<128;++i)
        {
            const int at=block*128+i-4800;const float expected=at<0?0.f:signal(at,48000);
            require(juce::exactlyEqual(audio.getSample(0,i),expected),"Offline harmony reset dropped original");
        }
    }
}
void offlineFailure()
{
    voxide::Processor p(studioTest::factory);p.setNonRealtime(true);p.prepareToPlay(48000,128);
    studioTest::nonfinite.store(true);juce::AudioBuffer<float> audio(2,128);juce::MidiBuffer midi;
    for (int at=0;at<8192;at+=128)
    {
        for (int i=0;i<128;++i) audio.setSample(0,i,signal(at+i,48000));p.processBlock(audio,midi);
        for (int i=0;i<128;++i)
        {
            const float expected=at+i<4800?0.f:signal(at+i-4800,48000);
            require(juce::exactlyEqual(audio.getSample(0,i),expected),"Failed offline render leaked invalid wet or changed original");
        }
    }
    require(p.studioStatus().status==voxide::studio::Status::failed && p.studioStatus().active==0,"Offline fault was accepted as successful bounce");
    p.releaseResources();studioTest::nonfinite.store(false);
}
}
void runBounceTests(bool native)
{
    for (int rate:{44100,48000})
    {
        const auto realtime=capture(rate,false,native,{128});
        const auto offline=capture(rate,true,native,{512});
        require(realtime.audio==offline.audio,"Realtime/offline audio or source automation differs");
        const auto repeated=capture(rate,true,native,{257,32,1024,1,128});
        require(offline.audio==repeated.audio,"Offline partition/repeat/recall changed audio");
        capture(rate,true,native,{1024,1,257},true);
    }
    if (!native) { offlineResets();offlineFailure(); }
    std::cout<<(native?"Native":"Fake")<<" bounce: exact playback/offline/partition/recall agreement, first sample and 0.6 s tails; not Logic/PDC or vocal-quality qualification\n";
}
