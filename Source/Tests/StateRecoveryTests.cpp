#include "PluginProcessor.h"
#include "ProcessorTestAccess.h"
#include "StudioTestSupport.h"
#include "AllocationAudit.h"
#include <condition_variable>
#include <functional>
#include <future>
#include <bit>
void runStateRecoveryTests();

namespace
{
using voxide::Processor;
using Access=voxide::ProcessorTestAccess;
void require(bool value,const char* text) { if (!value) throw std::runtime_error(text); }
bool same(float a,float b) { return juce::exactlyEqual(a,b); }
void set(Processor& p,int index,float value) { p.getParameters()[index]->setValueNotifyingHost(value); }
juce::MemoryBlock save(Processor& p) { juce::MemoryBlock result;p.getStateInformation(result);return result; }
void restore(Processor& p,const juce::MemoryBlock& state) { p.setStateInformation(state.getData(),static_cast<int>(state.getSize())); }
struct Listener final : juce::AudioProcessorParameter::Listener
{
    std::function<void()> callback;
    void parameterValueChanged(int,float) override { if (callback) callback(); }
    void parameterGestureChanged(int,bool) override {}
};
struct Attachment
{
    juce::AudioProcessorParameter& parameter;
    Listener listener;
    Attachment(Processor& p,int index,std::function<void()> callback) : parameter(*p.getParameters()[index])
    { listener.callback=std::move(callback);parameter.addListener(&listener); }
    ~Attachment() { parameter.removeListener(&listener); }
};
void render(Processor& p,juce::AudioBuffer<float>& audio)
{
    juce::MidiBuffer midi;voxide::audit::begin();p.processBlock(audio,midi);
    const auto count=voxide::audit::end();if (voxide::audit::available) require(count==0,"Recovery render allocated");
}
void preparationRecall()
{
    Processor p(studioTest::factory);const auto old=save(p);
    set(p,0,1);set(p,2,7.f/11);set(p,3,1.f/41);set(p,29,.8f);const auto desired=save(p);restore(p,old);
    std::mutex mutex;std::condition_variable condition;bool paused=false,released=false;std::atomic<bool> once {false};
    Attachment listener(p,0,[&]
    {
        if (once.exchange(true)) return;
        std::unique_lock lock(mutex);paused=true;condition.notify_all();condition.wait(lock,[&]{return released;});
    });
    auto recall=std::async(std::launch::async,[&]{restore(p,desired);});
    { std::unique_lock lock(mutex);condition.wait(lock,[&]{return paused;}); }
    std::promise<void> preparing;auto entered=preparing.get_future();
    auto prepared=std::async(std::launch::async,[&]{preparing.set_value();p.prepareToPlay(48000,128);});entered.wait();
    const bool serialized=prepared.wait_for(std::chrono::milliseconds(100))==std::future_status::timeout;
    { const std::lock_guard lock(mutex);released=true; }condition.notify_all();recall.get();prepared.get();
    require(serialized,"Preparation bypassed an in-flight recall");
    juce::AudioBuffer<float> audio(2,128);audio.clear();render(p,audio);
    const auto selection=Access::selection(p);
    require(same(selection[0],1) && same(selection[1],7) && same(selection[2],1)
        && std::abs(selection[3]-std::pow(10.f,-12.f/20))<1e-6f && !(Access::generation(p)&1u),"Preparation seeded partial state/gains");
}
void recursiveRecall()
{
    Processor p(studioTest::factory);const auto initial=save(p);
    set(p,0,1);set(p,2,4.f/11);set(p,3,1.f/41);set(p,29,.9f);const auto first=save(p);
    set(p,0,0);set(p,2,7.f/11);set(p,3,2.f/41);set(p,29,.8f);const auto nested=save(p);
    set(p,0,1);set(p,2,9.f/11);set(p,3,3.f/41);const auto cycle=save(p);
    restore(p,initial);p.prepareToPlay(48000,128);
    std::atomic<bool> firstNotified {false},secondNotified {false};int completeRenders=0;
    Attachment observer(p,2,[&]
    {
        juce::AudioBuffer<float> audio(2,128);audio.clear();render(p,audio);const auto selected=Access::selection(p);
        const bool a=same(selected[0],1) && same(selected[1],4) && same(selected[2],1) && std::abs(selected[3]-std::pow(10.f,-6.f/20))<1e-6f;
        const bool b=same(selected[0],0) && same(selected[1],7) && same(selected[2],2) && std::abs(selected[3]-std::pow(10.f,-12.f/20))<1e-6f;
        require((a || b) && !(Access::generation(p)&1u),"Reentrant callback rendered a hybrid/odd-generation state");++completeRenders;
    });
    Attachment caller(p,0,[&]
    {
        if (!firstNotified.exchange(true))
        {
            require(save(p)==first,"Reentrant save serialized a partial outer state");restore(p,nested);
            require(save(p)==first,"Nested restore mutated an in-flight notification batch");
        }
        else if (!secondNotified.exchange(true))
        {
            require(save(p)==nested,"Deferred notification did not observe the committed state");restore(p,cycle);
        }
    });
    restore(p,first);
    require(save(p)==nested && completeRenders==2 && secondNotified.load(),"Deferred recall result/reentrancy bound undefined");
}
std::atomic<bool> failNext {false};
std::atomic<unsigned> failures {0};
std::atomic<unsigned> attempts {0};
std::unique_ptr<voxide::studio::Native> failOnce(int rate,double ratio,double hz)
{
    ++attempts;
    if (failNext.exchange(false)) { ++failures;throw std::runtime_error("Injected native setup failure"); }
    return studioTest::factory(rate,ratio,hz);
}
void recovery(bool spare)
{
    failNext.store(!spare);failures.store(0);attempts.store(0);
    Processor p(failOnce);for (int index:{23,25,27}) set(p,index,0);p.prepareToPlay(48000,128);
    if (!spare) require(p.studioStatus().status==voxide::studio::Status::failed,"Initial native setup failure not retained for recovery");
    auto stoppedAttempts=attempts.load();
    juce::AudioBuffer<float> audio(2,128);int at=0;
    auto block=[&]
    {
        require(p.waitIdleForTest(),"Recovery fake worker failed");
        for (int i=0;i<128;++i) audio.setSample(0,i,static_cast<float>(.02*std::sin(6.283185307179586*220*(at+i)/48000)));
        render(p,audio);
        for (int i=0;i<128;++i)
        {
            const int source=at+i-4800;
            const auto expected=source<0?0.f:static_cast<float>(.02*std::sin(6.283185307179586*220*source/48000));
            require(std::bit_cast<std::uint32_t>(audio.getSample(0,i))==std::bit_cast<std::uint32_t>(expected),"Recovery changed queued original");
        }
        at+=128;std::this_thread::sleep_for(std::chrono::milliseconds(1));
    };
    for (int n=0;n<45;++n) block();
    if (spare)
    {
        failNext.store(true);p.requestRestart();
        const auto limit=std::chrono::steady_clock::now()+std::chrono::seconds(5);
        do { block(); } while (!Access::rebuildFailed(p) && std::chrono::steady_clock::now()<limit);
        require(Access::rebuildFailed(p) && failures.load()==1,"Spare failure injection did not occur");
        stoppedAttempts=attempts.load();
    }
    restore(p,save(p)); // Ordinary recall cannot retry a failed initial/spare build.
    for (int n=0;n<5;++n) block();
    require(attempts.load()==stoppedAttempts && failures.load()==1 && Access::rebuildFailed(p) && p.studioStatus().status==voxide::studio::Status::failed,
        "Failed build recovered without an explicit request");
    p.requestRestart();
    const auto limit=std::chrono::steady_clock::now()+std::chrono::seconds(5);
    do { block(); } while (p.studioStatus().status!=voxide::studio::Status::ready && std::chrono::steady_clock::now()<limit);
    require(p.studioStatus().status==voxide::studio::Status::ready,"Explicit recovery never rebuilt workers");
    for (int index:{23,25,27}) set(p,index,1);
    bool heard=false;
    for (int n=0;n<100;++n)
    {
        require(p.waitIdleForTest(),"Recovered workers stopped");
        for (int i=0;i<128;++i) audio.setSample(0,i,static_cast<float>(.02*std::sin(6.283185307179586*220*(at+i)/48000)));
        render(p,audio);
        if (n>60) for (int i=0;i<128;++i)
        {
            const float dry=static_cast<float>(.02*std::sin(6.283185307179586*220*(at+i-4800)/48000));
            if (std::abs(audio.getSample(0,i)-dry)>1e-5f) heard=true;
        }
        at+=128;
    }
    require(heard && p.studioStatus().status==voxide::studio::Status::ready && p.studioStatus().active==7,"Recovery passed with silent/failed harmonies");
}
}
void runStateRecoveryTests() { preparationRecall();recursiveRecall();recovery(false);recovery(true); }
