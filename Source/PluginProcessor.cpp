#include "PluginProcessor.h"
#include "BuildInfo.h"
#include "DSP/PassThrough.h"
#include <cstring>

namespace voxide
{
Processor::Processor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::mono(), true)
          .withInput("Vocal sidechain", juce::AudioChannelSet::mono(), false)
          .withOutput("Output", juce::AudioChannelSet::stereo(), true))
{
    sourceChoice = new juce::AudioParameterChoice(juce::ParameterID { "sourceBus", 1 },
        "Vocal source", juce::StringArray { "Main input", "Sidechain" }, 0);
    addParameter(sourceChoice);
}

void Processor::prepareToPlay(double, int)
{
    setLatencySamples(0);
}

bool Processor::isBusesLayoutSupported(const BusesLayout& layout) const
{
    if (layout.inputBuses.size() != 2 || layout.outputBuses.size() != 1
        || layout.getMainOutputChannelSet() != juce::AudioChannelSet::stereo())
        return false;

    const auto supportedInput = [](const juce::AudioChannelSet& channels)
    {
        return channels == juce::AudioChannelSet::mono()
            || channels == juce::AudioChannelSet::stereo();
    };
    return supportedInput(layout.getMainInputChannelSet())
        && (layout.getChannelSet(true, 1).isDisabled()
            || supportedInput(layout.getChannelSet(true, 1)));
}

void Processor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi)
{
    processBlockBypassed(buffer, midi);
}

void Processor::processBlockBypassed(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi)
{
    juce::ScopedNoDenormals noDenormals;
    // AU enables all buses even when disconnected. Never infer connection from
    // enablement or signal level; an explicitly selected silent source stays silent.
    const int inputBus = sourceChoice->getIndex();
    const auto input = getBusBuffer(buffer, true, inputBus);
    auto output = getBusBuffer(buffer, false, 0);
    // Mono-source contract: use channel 1 when the host supplies a stereo source.
    // Read each sample before writing either output (the bus storage can alias).
    passThrough(input.getNumChannels() > 0 ? input.getReadPointer(0) : nullptr,
                output.getWritePointer(0), output.getWritePointer(1), buffer.getNumSamples());
    // PR 00 accepts but intentionally ignores MIDI. No MIDI output is advertised.
    midi.clear();
}

namespace
{
class ShellEditor final : public juce::AudioProcessorEditor
{
public:
    explicit ShellEditor(Processor& owner)
        : AudioProcessorEditor(owner), sourceAttachment(owner.sourceParameter(),
            [this](float value) { source.setSelectedItemIndex(juce::roundToInt(value), juce::dontSendNotification); }, nullptr)
    {
        setWantsKeyboardFocus(false);
        source.addItemList({ "Main input", "Sidechain" }, 1);
        source.setTitle("Vocal source");
        source.setTooltip("Choose the routed bus explicitly. Silent or disconnected sidechain does not fall back to main input.");
        source.onChange = [this] { sourceAttachment.setValueAsCompleteGesture(static_cast<float>(source.getSelectedItemIndex())); };
        sourceAttachment.sendInitialUpdate();
        addAndMakeVisible(source);
        setSize(460, 195);
    }

    void resized() override { source.setBounds(140, 105, 290, 28); }

    void paint(juce::Graphics& g) override
    {
        g.fillAll(juce::Colours::darkslategrey);
        g.setColour(juce::Colours::white);
        g.setFont(20.0f);
        g.drawText("voxide — pass-through shell", 20, 20, 420, 32, juce::Justification::left);
        g.setFont(14.0f);
        g.drawText("No harmonies yet. MIDI is accepted, not processed.",
                   20, 63, 420, 24, juce::Justification::left);
        g.drawText("Vocal source", 20, 105, 110, 28, juce::Justification::left);
        g.drawText(juce::String(build::version) + " / " + build::revision + " / " + build::profile,
                   20, 152, 420, 24, juce::Justification::left);
    }

private:
    juce::ComboBox source;
    juce::ParameterAttachment sourceAttachment;
};
}

juce::AudioProcessorEditor* Processor::createEditor() { return new ShellEditor(*this); }

void Processor::getStateInformation(juce::MemoryBlock& destination)
{
    constexpr char prefix[] = "voxide-shell-v2";
    destination.setSize(sizeof(prefix) + 1);
    std::memcpy(destination.getData(), prefix, sizeof(prefix));
    static_cast<unsigned char*>(destination.getData())[sizeof(prefix)] = static_cast<unsigned char>(sourceChoice->getIndex());
}

void Processor::setStateInformation(const void* data, int size)
{
    if (data == nullptr || size <= 0) return;
    constexpr char legacy[] = "voxide-shell-v1";
    constexpr char prefix[] = "voxide-shell-v2";
    if (size == static_cast<int>(sizeof(legacy)) && std::memcmp(data, legacy, sizeof(legacy)) == 0)
        sourceChoice->setValueNotifyingHost(0.0f);
    else if (size == static_cast<int>(sizeof(prefix) + 1) && std::memcmp(data, prefix, sizeof(prefix)) == 0)
    {
        const auto sourceIndex = static_cast<const unsigned char*>(data)[sizeof(prefix)];
        if (sourceIndex <= 1) sourceChoice->setValueNotifyingHost(static_cast<float>(sourceIndex));
    }
}
}
