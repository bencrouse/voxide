#pragma once
#include "Session.h"
#include <juce_audio_utils/juce_audio_utils.h>

namespace voxide::evaluation
{
class ProcessorTestAccess;
class Processor final : public juce::AudioProcessor
{
public:
    explicit Processor(Session::Factory=engines::create);
    ~Processor() override;
    const juce::String getName() const override { return "voxide Studio Eval"; }
    void prepareToPlay(double,int) override;
    void releaseResources() override;
    void reset() override { resetGeneration.fetch_add(1,std::memory_order_release); }
    void requestRestart() noexcept { restartGeneration.fetch_add(1,std::memory_order_release); }
    bool isBusesLayoutSupported(const BusesLayout&) const override;
    void processBlock(juce::AudioBuffer<float>&,juce::MidiBuffer&) override;
    void processBlockBypassed(juce::AudioBuffer<float>&,juce::MidiBuffer&) override;
    using AudioProcessor::processBlock;
    using AudioProcessor::processBlockBypassed;
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return .6; }
    bool hasEditor() const override { return true; }
    juce::AudioProcessorEditor* createEditor() override;
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return "Evaluation only"; }
    void changeProgramName(int,const juce::String&) override {}
    void getStateInformation(juce::MemoryBlock&) override;
    void setStateInformation(const void*,int) override;
    Session::Snapshot status() const noexcept;
private:
    void render(juce::AudioBuffer<float>&,juce::MidiBuffer&,bool);
    float delayed(float) noexcept;
    Session::Factory factory;
    std::unique_ptr<Session> session;
    std::vector<float> leadDelay;
    std::size_t leadPosition=0;
    float wetGain=1;
    double rate=0;
    std::atomic<unsigned> restartGeneration {0};
    std::atomic<unsigned> resetGeneration {0};
    unsigned renderedGeneration=0,renderedReset=0;
    bool lastOffline=false,lastPlaying=false,lastPositionKnown=false,lastBypassed=false;
    std::int64_t lastPosition=0;
    int lastFrames=0;
    std::atomic<Session::Status> renderStatus {Session::Status::preparing};
    std::atomic<float> pitchHz {0};
    std::atomic<unsigned> activeVoices {0};
    juce::AudioParameterChoice *key=nullptr,*scale=nullptr;
    juce::AudioParameterBool* enabled=nullptr;
    juce::AudioParameterFloat* level=nullptr;
    friend class ProcessorTestAccess;
};
}
