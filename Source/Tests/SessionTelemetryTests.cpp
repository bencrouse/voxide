#include "PluginProcessor.h"
#include "StudioTestSupport.h"
#include "AllocationAudit.h"
#include <filesystem>
#include <iostream>
void runSessionTelemetryTests();
namespace
{
void require(bool ok,const char* text) { if (!ok) throw std::runtime_error(text); }
void queueContracts()
{
    voxide::SessionTelemetry queue;voxide::SessionSample sample;
    require(queue.begin()==0 && queue.start(),"Telemetry was not opt-in");
    sample.capture=queue.begin();queue.stop();
    require(!queue.quiescent() && !queue.start(),"Capture finalized/restarted over in-flight writer");
    sample.frames=128;queue.finish(sample);
    require(!queue.start() && queue.pop(sample) && sample.sequence==1 && sample.capture==1,"Final callback was lost/reused");
    require(queue.start(),"Drained capture could not restart");
    for (std::uint64_t i=0;i<voxide::SessionTelemetry::capacity+5;++i)
    { sample.capture=queue.begin();queue.finish(sample); }
    queue.stop();std::uint64_t count=0;
    while (queue.pop(sample)) { ++count;require(sample.capture==2 && sample.sequence==count,"Capture sequence changed"); }
    require(count==voxide::SessionTelemetry::capacity && queue.dropped()==5,"Overflow was hidden");
}
void queueConcurrency()
{
    voxide::SessionTelemetry queue;std::atomic<bool> stop {false},allocated {false};
    std::thread producer([&]
    {
        while (!stop.load())
        {
            voxide::audit::begin();const auto token=queue.begin();
            if (token) { voxide::SessionSample sample;sample.capture=token;queue.finish(sample); }
            if (voxide::audit::end()!=0) allocated.store(true);
            std::this_thread::yield();
        }
    });
    try
    {
        for (int pass=0;pass<30;++pass)
        {
            const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(5);
            while (!queue.start()) { require(std::chrono::steady_clock::now()<deadline,"Capture restart handshake stalled");std::this_thread::yield(); }
            const auto token=queue.capture();std::uint64_t last=0,count=0;
            auto drain=[&]
            {
                voxide::SessionSample sample;
                while (queue.pop(sample)) { require(sample.capture==token && sample.sequence>last,"Concurrent stop/start mixed captures");last=sample.sequence;++count; }
            };
            while (count<64) { drain();require(std::chrono::steady_clock::now()<deadline,"Concurrent producer stalled");std::this_thread::yield(); }
            queue.stop();while (!queue.quiescent()) { require(std::chrono::steady_clock::now()<deadline,"In-flight writer did not finish");std::this_thread::yield(); }
            drain();require(queue.empty(),"Final callback was not accounted for");
        }
    }
    catch (...) { stop.store(true);producer.join();throw; }
    stop.store(true);producer.join();require(!voxide::audit::available || !allocated.load(),"Concurrent metadata allocated");
}
void logContracts()
{
    juce::ScopedJuceInitialiser_GUI gui;
    const auto directory=juce::File(VOXIDE_TEST_OUTPUT_DIR).getSiblingFile("sessions").getChildFile(juce::Uuid().toString());
    voxide::SessionTelemetry queue;voxide::SessionLog log(queue);
    require(log.start(directory,"synthetic-race-fixture"),"Cannot start synthetic log");
    voxide::SessionSample sample;sample.capture=queue.begin();sample.tick=1;sample.elapsed=1;sample.frames=128;sample.rate=48000;sample.status=1;
    log.stop();require(log.active() && log.stopping(),"Stop truncated an in-flight callback");queue.finish(sample);log.drain();
    require(!log.active() && log.error().isEmpty(),"Final in-flight callback was not drained");
    const auto contents=juce::File(log.path()).loadFileAsString();
    require(contents.contains("\"callbacks\": 1") && contents.contains("\"kind\": \"end\"") && !contents.contains("source_hash"),"Incomplete or PCM-derived log");
    const auto symlink=directory.getSiblingFile(directory.getFileName()+"-link");
    std::filesystem::create_directory_symlink(directory.getFullPathName().toStdString(),symlink.getFullPathName().toStdString());
    require(!log.start(symlink,"unsafe") && log.error().contains("symlink"),"Symlink log destination accepted");
    {
        voxide::Processor p(studioTest::factory);p.prepareToPlay(48000,128);
        require(!p.sessionLog().active(),"Preparation started recording without consent");
        require(p.sessionLog().start(directory,"synthetic-product-fixture"),"Product log start failed");
        juce::AudioBuffer<float> audio(2,128);juce::MidiBuffer midi;std::vector<float> captured;
        for (int block=0;block<50;++block)
        {
            if (block==10) { std::unique_ptr<juce::AudioProcessorEditor> editor(p.createEditor());editor.reset(); }
            require(p.waitIdleForTest(),"Telemetry fake worker failed");
            for (int i=0;i<128;++i) audio.setSample(0,i,.02f*std::sin(static_cast<float>(block*128+i)*.0288f));
            const auto waits=voxide::studio::Worker::waitCallsOnThreadForTest();voxide::audit::begin();p.processBlock(audio,midi);
            const auto allocations=voxide::audit::end();
            if (voxide::audit::available) require(allocations==0,"Session metadata allocated in render");
            for (int i=0;i<128;++i) captured.push_back(audio.getSample(0,i));
            require(voxide::studio::Worker::waitCallsOnThreadForTest()==waits,"Session metadata waited in render");
            require(p.sessionLog().active(),"Editor close stopped session capture");p.sessionLog().drain();
        }
        p.sessionLog().stop();p.sessionLog().drain();
        require(!p.sessionLog().active() && p.sessionLog().error().isEmpty(),"Product session did not finalize");
        const auto text=juce::File(p.sessionLog().path()).loadFileAsString();
        require(text.contains("\"callbacks\": 50") && text.contains("processor render body only") && text.contains("\"pcm_recorded\": false"),"Session scope/completeness missing");
        voxide::Processor reference(studioTest::factory);reference.prepareToPlay(48000,128);
        for (int block=0;block<50;++block)
        {
            require(reference.waitIdleForTest(),"Unlogged reference worker failed");
            for (int i=0;i<128;++i) audio.setSample(0,i,.02f*std::sin(static_cast<float>(block*128+i)*.0288f));
            reference.processBlock(audio,midi);
            for (int i=0;i<128;++i) require(juce::exactlyEqual(audio.getSample(0,i),captured[static_cast<std::size_t>(block*128+i)]),"Logging changed audio");
        }
    }
    juce::String aborted;
    { voxide::SessionTelemetry t;voxide::SessionLog unfinished(t);require(unfinished.start(directory,"aborted-fixture"),"Abort fixture failed");aborted=unfinished.path(); }
    const auto text=juce::File(aborted).loadFileAsString();require(text.contains("\"kind\": \"aborted\"") && !text.contains("\"kind\": \"end\""),"Destructor fabricated successful stop");
}
void outputOnlyMetadata()
{
    voxide::Processor p(studioTest::factory);auto layout=p.getBusesLayout();
    layout.inputBuses.set(0,juce::AudioChannelSet::stereo());layout.inputBuses.set(1,juce::AudioChannelSet::stereo());
    require(p.setBusesLayout(layout),"Telemetry stereo/sidechain layout rejected");p.prepareToPlay(44100,128);
    require(p.sessionTelemetry().start(),"Output-only telemetry could not arm");
    juce::AudioBuffer<float> audio(4,128);audio.clear();juce::MidiBuffer midi;
    for (int i=0;i<128;++i) { audio.setSample(2,i,2);audio.setSample(3,i,2); }
    voxide::audit::begin();p.processBlock(audio,midi);const auto allocations=voxide::audit::end();
    if (voxide::audit::available) require(allocations==0,"Output metadata allocated");
    p.sessionTelemetry().stop();voxide::SessionSample sample;
    require(p.sessionTelemetry().pop(sample) && juce::exactlyEqual(sample.peak,0.f) && sample.nonfinite==0,
        "Unselected sidechain input was mislabeled as output headroom");
}
}
void runSessionTelemetryTests()
{
    queueContracts();queueConcurrency();logContracts();outputOnlyMetadata();std::cout<<"Session metadata opt-in, stop handshake, overflow, editor lifetime and render auditing pass; synthetic only\n";
}
