#pragma once
#include <juce_audio_utils/juce_audio_utils.h>
#include "Diagnostics.h"

namespace voxide
{
class Processor final : public juce::AudioProcessor
{
public:
    Processor();
    const juce::String getName() const override { return "voxide"; }
    void prepareToPlay(double, int) override;
    void reset() override;
    void releaseResources() override {}
    bool isBusesLayoutSupported(const BusesLayout&) const override;
    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    void processBlockBypassed(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    using AudioProcessor::processBlock;
    using AudioProcessor::processBlockBypassed;
    juce::AudioParameterChoice& sourceParameter() noexcept { return *sourceChoice; }
    DiagnosticQueue<>& diagnosticQueue() noexcept { return diagnostics; }
    const juce::String& instanceId() const noexcept { return instance; }
    bool acceptsMidi() const override { return true; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0.0; }
    bool hasEditor() const override { return true; }
    juce::AudioProcessorEditor* createEditor() override;
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return "Pass-through shell"; }
    void changeProgramName(int, const juce::String&) override {}
    void getStateInformation(juce::MemoryBlock&) override;
    void setStateInformation(const void*, int) override;

private:
    void render(juce::AudioBuffer<float>&, juce::MidiBuffer&, bool bypassed);
    DiagnosticQueue<> diagnostics;
    const juce::String instance = juce::Uuid().toString();
    std::array<std::uint64_t, 32> held {};
    std::uint64_t diagnosticFrame = 0, sequence = 0, blockCounter = 0, truncatedMidiBlocks = 0;
    std::uint32_t diagnosticEpoch = 0;
    double diagnosticRate = 0.0;
    std::int64_t lastHostSample = -1;
    std::uint32_t lastHostFrames = 0;
    bool heldKnown = true, wasPlaying = false, lastHostSampleKnown = false;
    juce::AudioParameterChoice* sourceChoice = nullptr; // Owned by AudioProcessor.
};
}
