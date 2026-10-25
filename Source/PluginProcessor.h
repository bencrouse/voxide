#pragma once
#include <juce_audio_utils/juce_audio_utils.h>
#include "Diagnostics.h"
#include "DSP/PitchTracker.h"
#include "DSP/HarmonySelector.h"
#include "Studio/Session.h"
#include <mutex>
#include <optional>

namespace voxide
{
class Processor final : public juce::AudioProcessor
{
public:
    explicit Processor(studio::Factory=studio::createNative);
    ~Processor() override;
    const juce::String getName() const override { return "voxide"; }
    void prepareToPlay(double, int) override;
    void reset() override;
    void releaseResources() override;
    void requestRestart() noexcept { restartGeneration.fetch_add(1,std::memory_order_release); }
    studio::Snapshot studioStatus() const noexcept;
    float inputPeak() const noexcept { return meterPeak.load(std::memory_order_relaxed); }
    std::int64_t renderTick() const noexcept { return lastRenderTick.load(std::memory_order_relaxed); }
    bool waitIdleForTest() const { return !session || session->waitIdleForTest(); }
    bool isBusesLayoutSupported(const BusesLayout&) const override;
    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    void processBlockBypassed(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    using AudioProcessor::processBlock;
    using AudioProcessor::processBlockBypassed;
    juce::AudioParameterChoice& sourceParameter() noexcept { return *sourceChoice; }
    DiagnosticQueue<>& diagnosticQueue() noexcept { return diagnostics; }
    const juce::String& instanceId() const noexcept { return instance; }
    // Inspect only on the audio thread, or while rendering is stopped.
    const PitchFrame& pitchFrame() const noexcept { return tracker.frame(); }
    const HarmonySelector& harmonyState() const noexcept { return selector; }
    bool acceptsMidi() const override { return true; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0.6; }
    bool hasEditor() const override { return true; }
    juce::AudioProcessorEditor* createEditor() override;
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return "Studio harmonies"; }
    void changeProgramName(int, const juce::String&) override {}
    void getStateInformation(juce::MemoryBlock&) override;
    void setStateInformation(const void*, int) override;

private:
    void render(juce::AudioBuffer<float>&, juce::MidiBuffer&, bool bypassed);
    struct RenderSettings
    {
        int source = 0, variant = 0;
        HarmonyConfig harmony;
        unsigned generation = 0;
        std::array<float,3> voiceGain {1,1,1};
        float originalGain=1;
    };
    RenderSettings captureSettings() const noexcept;
    RenderSettings readSettings() noexcept;
    void resetMusical(const RenderSettings&) noexcept;
    HarmonyConfig musicalConfig() const noexcept;
    void applyState(const std::array<float,30>&);
    PitchTracker tracker;
    HarmonySelector selector;
    std::atomic<unsigned> stateGeneration { 0 };
    std::recursive_mutex stateMutex; // State serialization only; never render.
    bool recallingState=false,applyingDeferredState=false;
    std::optional<std::array<float,30>> deferredState;
    RenderSettings renderedSettings;
    studio::Factory factory;
    std::unique_ptr<studio::Session> session;
    std::vector<float> leadDelay;
    std::size_t leadPosition=0;
    std::array<float,3> voiceGains {1,1,1};
    float originalGain=1;
    std::atomic<unsigned> resetGeneration {0},restartGeneration {0};
    unsigned renderedReset=0,renderedRestart=0;
    bool lastOffline=false;
    std::atomic<studio::Status> renderStatus {studio::Status::preparing};
    std::atomic<float> studioHz {0},meterPeak {0};
    std::atomic<unsigned> studioActive {0};
    std::atomic<std::int64_t> lastRenderTick {0};
    unsigned renderedGeneration = 0;
    int lastSource = -1, lastVariant = -1;
    bool lastBypassed = false;
    std::uint32_t trackingEpoch = 0;
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
    juce::AudioParameterChoice *modeChoice = nullptr, *rootChoice = nullptr,
        *scaleChoice = nullptr, *trackerChoice = nullptr;
    std::array<juce::AudioParameterBool*, 12> customChoices {};
    std::array<juce::AudioParameterInt*, 3> degreeChoices {}, octaveChoices {};
    std::array<juce::AudioParameterBool*,3> voiceEnabled {};
    std::array<juce::AudioParameterFloat*,3> voiceLevels {};
    juce::AudioParameterFloat* originalLevel=nullptr;
    friend class ProcessorTestAccess;
};
}
