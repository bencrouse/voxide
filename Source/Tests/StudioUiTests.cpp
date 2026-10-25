#include "PluginProcessor.h"
#include "StudioTestSupport.h"
#include "ProcessorTestAccess.h"
#include "AllocationAudit.h"
#include <iostream>
void runStudioUiTests();

namespace
{
void require(bool value,const char* text) { if (!value) throw std::runtime_error(text); }
juce::Component* find(juce::Component& parent,const juce::String& id)
{
    if (parent.getComponentID()==id) return &parent;
    for (auto* child:parent.getChildren()) if (auto* result=find(*child,id)) return result;
    return nullptr;
}
void bounds(juce::Component& parent)
{
    for (auto* child:parent.getChildren())
    {
        if (child->isVisible()) require(parent.getLocalBounds().contains(child->getBounds()),"Editor child clipped outside parent");
        bounds(*child);
    }
}
std::vector<float> renderWithEditor(bool withEditor)
{
    voxide::Processor p(studioTest::factory);
    juce::MemoryBlock saved;p.getStateInformation(saved);
    // Recall into a fresh processor must produce the same DSP with/without UI.
    p.setStateInformation(saved.getData(),static_cast<int>(saved.getSize()));p.prepareToPlay(48000,128);
    std::unique_ptr<juce::AudioProcessorEditor> editor(withEditor?p.createEditor():nullptr);
    std::vector<float> samples;juce::AudioBuffer<float> audio(2,128);juce::MidiBuffer midi;
    for (int at=0;at<24064;at+=128)
    {
        require(p.waitIdleForTest(),"UI/headless reference worker failed");
        if (at==8192)
        {
            if (editor)
            {
                dynamic_cast<juce::ComboBox*>(find(*editor,"scaleRoot"))->setSelectedItemIndex(5,juce::sendNotificationSync);
                dynamic_cast<juce::Slider*>(find(*editor,"voiceDegree1"))->setValue(0,juce::sendNotificationSync);
            }
            else { p.getParameters()[2]->setValueNotifyingHost(5.f/11);p.getParameters()[17]->setValueNotifyingHost(.5f); }
        }
        if (at==16384) p.setStateInformation(saved.getData(),static_cast<int>(saved.getSize()));
        for (int i=0;i<128;++i) audio.setSample(0,i,static_cast<float>(.02*std::sin(6.283185307179586*220*(at+i)/48000)));
        p.processBlock(audio,midi);
        require(p.studioStatus().status==voxide::studio::Status::ready,"UI/headless reference accepted muted fault");
        for (int i=0;i<128;++i) samples.push_back(audio.getSample(0,i));
    }
    return samples;
}
}
void runStudioUiTests()
{
    juce::ScopedJuceInitialiser_GUI gui;
    const auto images=juce::File(VOXIDE_TEST_OUTPUT_DIR).getSiblingFile("ui").getChildFile("capture-"+juce::Uuid().toString());
    require(images.createDirectory().wasOk(),"Cannot create unique UI snapshot directory");
    require(renderWithEditor(false)==renderWithEditor(true),"UI gestures/headless automation/recall changed production audio");
    {
        voxide::Processor unavailable(nullptr);unavailable.prepareToPlay(48000,128);
        std::unique_ptr<juce::AudioProcessorEditor> editor(unavailable.createEditor());
        const auto* recovery=dynamic_cast<juce::TextButton*>(find(*editor,"restartHarmonies"));
        require(unavailable.studioStatus().status==voxide::studio::Status::initializationFailed
            && recovery && !recovery->isEnabled() && recovery->getButtonText()=="Re-prepare required","Unrecoverable initialization offered an ineffective restart");
    }
    voxide::Processor p(studioTest::factory);p.prepareToPlay(48000,128);
    juce::MemoryBlock initial;p.getStateInformation(initial);
    std::atomic<bool> stop {false},failed {false},recovered {false};
    std::atomic<unsigned> callbacks {0},handoffs {0},settleAfter {std::numeric_limits<unsigned>::max()};
    std::thread render([&]
    {
        studioTest::renderThread=true;
        juce::AudioBuffer<float> audio(2,128);juce::MidiBuffer midi;
        const void* previous=voxide::ProcessorTestAccess::graph(p);
        while (!stop.load())
        {
            if (!p.waitIdleForTest()) failed.store(true);
            for (int i=0;i<128;++i) audio.setSample(0,i,.02f*std::sin(static_cast<float>(callbacks.load()*128+static_cast<unsigned>(i))*.0288f));
            voxide::audit::begin();p.processBlock(audio,midi);
            if (voxide::audit::end()!=0) failed.store(true);
            for (int i=0;i<128;++i) if (!std::isfinite(audio.getSample(0,i))) failed.store(true);
            const auto* graph=voxide::ProcessorTestAccess::graph(p);
            if (graph && previous && graph!=previous) ++handoffs;
            if (graph) previous=graph;
            const auto status=p.studioStatus();
            if (callbacks.load()>=settleAfter.load() && status.status==voxide::studio::Status::ready && status.active==7)
                for (int i=0;i<128;++i)
                {
                    const auto source=callbacks.load()*128+static_cast<unsigned>(i)-4800;
                    const float dry=.02f*std::sin(static_cast<float>(source)*.0288f);
                    if (std::abs(audio.getSample(0,i)-dry)>1e-5f) recovered.store(true);
                }
            ++callbacks;std::this_thread::sleep_for(std::chrono::microseconds(100));
        }
    });
    try
    {
        while (callbacks.load()<10) std::this_thread::sleep_for(std::chrono::microseconds(100));
        for (int pass=0;pass<20;++pass)
        {
            std::unique_ptr<juce::AudioProcessorEditor> editor(p.createEditor());
            require(!editor->getWantsKeyboardFocus(),"Editor steals host keyboard focus");
            for (auto size:{juce::Point<int>(720,600),juce::Point<int>(780,620),juce::Point<int>(1000,760)})
            {
                editor->setSize(size.x,size.y);bounds(*editor);
                juce::Image image(juce::Image::ARGB,size.x,size.y,true);juce::Graphics graphics(image);editor->paintEntireComponent(graphics,true);
                if (pass==0)
                {
                    auto file=images.getChildFile(juce::String(size.x)+"x"+juce::String(size.y)+".png");
                    juce::FileOutputStream output(file);require(output.openedOk() && juce::PNGImageFormat().writeImageToStream(image,output),"Cannot write UI snapshot");
                }
            }
            auto* key=dynamic_cast<juce::ComboBox*>(find(*editor,"scaleRoot"));
            auto* degree=dynamic_cast<juce::Slider*>(find(*editor,"voiceDegree1"));
            auto* enabled=dynamic_cast<juce::ToggleButton*>(find(*editor,"voiceEnabled1"));
            require(key && degree && enabled,"Native product controls missing");
            require(key->getWantsKeyboardFocus() && degree->getWantsKeyboardFocus() && enabled->getWantsKeyboardFocus(),"Controls not keyboard accessible");
            key->setSelectedItemIndex(pass%12,juce::sendNotificationSync);
            require(std::abs(p.getParameters()[2]->getValue()-static_cast<float>(pass%12)/11)<1e-6f,"UI key gesture not delivered");
            degree->setValue(3,juce::sendNotificationSync);require(std::abs(p.getParameters()[17]->getValue()-14.f/22)<1e-6f,"UI degree edit ignored");
            // Host automation may retain e.g. normalized .25 as semantic false.
            // Exercise an actual transition, not a no-op false->false request.
            enabled->setToggleState(!enabled->getToggleState(),juce::sendNotificationSync);
            enabled->setToggleState(false,juce::sendNotificationSync);
            require(juce::exactlyEqual(p.getParameters()[23]->getValue(),0.f),"UI voice enable gesture ignored");
            auto* voiceLevel=dynamic_cast<juce::Slider*>(find(*editor,"voiceLevel1"));require(voiceLevel,"UI level missing");
            voiceLevel->setValue(-6,juce::sendNotificationSync);
            require(std::abs(p.getParameters()[24]->getValue()-.9f)<1e-6f,"UI voice level gesture ignored");
            p.setStateInformation(initial.getData(),static_cast<int>(initial.getSize()));
            require(key->getSelectedItemIndex()==0 && std::abs(degree->getValue()-2)<1e-9,"Recall did not update controls");
            for (int index=0;index<p.getParameters().size();++index)
                if (index>=23) p.getParameters()[index]->setValueNotifyingHost(static_cast<float>(pass%5)/4);
            // Reopening must not write a stale attachment snapshot over automation.
            juce::MemoryBlock before,after;p.getStateInformation(before);editor.reset();p.getStateInformation(after);
            require(before==after,"Editor teardown overwrote automated state");
            const auto target=callbacks.load()+3;
            while (callbacks.load()<target) std::this_thread::sleep_for(std::chrono::microseconds(100));
        }
        settleAfter.store(callbacks.load()+128);
        const auto limit=std::chrono::steady_clock::now()+std::chrono::seconds(10);
        while (!recovered.load() && std::chrono::steady_clock::now()<limit) std::this_thread::sleep_for(std::chrono::milliseconds(1));
        require(recovered.load() && handoffs.load()>0,"Concurrency test never recovered audible healthy workers/graph handoffs");
    }
    catch (...) { stop.store(true);render.join();throw; }
    stop.store(true);render.join();
    require(callbacks.load()>=70 && !failed.load(),"Concurrent editor/recall/render contract failed");
    p.releaseResources();require(studioTest::living.load()==0,"UI lifecycle leaked workers");
    std::cout<<"Native editor snapshots: "<<images.getFullPathName()<<'\n';
    std::cout<<"Native editor snapshots, gestures, recall and concurrent rendering passed; no window/device/host opened\n";
}
