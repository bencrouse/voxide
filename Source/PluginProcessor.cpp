#include "PluginProcessor.h"
#include "BuildInfo.h"
#include "DSP/PassThrough.h"
#include "DiagnosticLog.h"
#include <bit>
#include <cmath>
#include <cstring>
#include <limits>

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
    modeChoice = new juce::AudioParameterChoice(juce::ParameterID { "harmonyMode", 2 }, "Target mode", juce::StringArray { "Scale intervals", "Absolute MIDI" }, 0);
    rootChoice = new juce::AudioParameterChoice(juce::ParameterID { "scaleRoot", 2 }, "Scale root", juce::StringArray { "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B" }, 0);
    juce::StringArray scaleNames;
    for (const auto& scale : scaleCatalog()) scaleNames.add(scale.name);
    scaleChoice = new juce::AudioParameterChoice(juce::ParameterID { "scaleSet", 2 }, "Scale (12-TET)", scaleNames, 0);
    trackerChoice = new juce::AudioParameterChoice(juce::ParameterID { "pitchTracker", 2 }, "Causal tracker", juce::StringArray { "YIN baseline", "Multi-candidate YIN" }, 1);
    for (auto* parameter : { modeChoice, rootChoice, scaleChoice, trackerChoice }) addParameter(parameter);
    for (std::size_t i = 0; i < customChoices.size(); ++i)
    {
        customChoices[i] = new juce::AudioParameterBool(juce::ParameterID { "customPc" + juce::String(static_cast<int>(i)), 2 },
            "Custom root + " + juce::String(static_cast<int>(i)), (0x0ab5 & (1 << i)) != 0);
        addParameter(customChoices[i]);
    }
    for (std::size_t i = 0; i < 3; ++i)
    {
        const auto suffix = juce::String(static_cast<int>(i + 1));
        degreeChoices[i] = new juce::AudioParameterInt(juce::ParameterID { "voiceDegree" + suffix, 2 }, "Voice " + suffix + " degree steps", -11, 11, i == 0 ? 2 : i == 1 ? 4 : 0);
        octaveChoices[i] = new juce::AudioParameterInt(juce::ParameterID { "voiceOctave" + suffix, 2 }, "Voice " + suffix + " octaves", -2, 2, i == 2 ? 1 : 0);
        addParameter(degreeChoices[i]); addParameter(octaveChoices[i]);
    }
}

void Processor::prepareToPlay(double rate, int)
{
    setLatencySamples(0);
    diagnosticRate = rate;
    reset();
}

void Processor::reset()
{
    resetMusical(captureSettings());
    diagnosticFrame = 0;
    ++diagnosticEpoch;
    held.fill(0);
    heldKnown = true;
    wasPlaying = false;
    lastHostSample = -1;
    lastHostSampleKnown = false;
    lastHostFrames = 0;
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

Processor::RenderSettings Processor::captureSettings() const noexcept
{
    // Generation is captured first: if recall overlaps this read, the following
    // callback must observe the later generation and clear transient history again.
    const auto generation = stateGeneration.load(std::memory_order_acquire);
    return { sourceChoice->getIndex(), trackerChoice->getIndex(), musicalConfig(), generation };
}

void Processor::resetMusical(const RenderSettings& settings) noexcept
{
    ++trackingEpoch;
    lastSource = settings.source;
    lastVariant = settings.variant;
    tracker.prepare(diagnosticRate, lastVariant == 0 ? TrackerVariant::yin : TrackerVariant::multiCandidate);
    selector.reset();
    selector.configure(settings.harmony);
    renderedGeneration = settings.generation;
}

HarmonyConfig Processor::musicalConfig() const noexcept
{
    HarmonyConfig config;
    config.midiMode = modeChoice->getIndex() == 1;
    config.root = rootChoice->getIndex(); config.scale = scaleChoice->getIndex();
    config.customMask = 0;
    for (std::size_t i = 0; i < 12; ++i)
        if (customChoices[i]->get()) config.customMask |= static_cast<std::uint16_t>(1u << i);
    for (std::size_t i = 0; i < 3; ++i)
    {
        config.degrees[i] = degreeChoices[i]->get(); config.octaves[i] = octaveChoices[i]->get();
    }
    return config;
}

void Processor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi)
{
    render(buffer, midi, false);
}

void Processor::processBlockBypassed(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi)
{
    render(buffer, midi, true);
}

namespace
{
struct SignalSummary
{
    float peak = 0.0f;
    std::uint32_t nonFinite = 0;
    std::uint64_t hash = 14695981039346656037ull;
};

SignalSummary summarize(const float* input, int frames) noexcept
{
    SignalSummary summary;
    for (int i = 0; i < frames; ++i)
    {
        const float value = input != nullptr ? input[i] : 0.0f;
        if (std::isfinite(value)) summary.peak = std::max(summary.peak, std::abs(value));
        else ++summary.nonFinite;
        summary.hash = (summary.hash ^ std::bit_cast<std::uint32_t>(value)) * 1099511628211ull;
    }
    return summary;
}
}

void Processor::render(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi, bool bypassed)
{
    juce::ScopedNoDenormals noDenormals;
    // AU enables all buses even when disconnected. Never infer connection from
    // enablement or signal level; an explicitly selected silent source stays silent.
    const auto settings = captureSettings();
    const int inputBus = settings.source;
    const auto main = getBusBuffer(buffer, true, 0);
    const auto side = getBusBuffer(buffer, true, 1);
    const auto mainSummary = summarize(main.getNumChannels() > 0 ? main.getReadPointer(0) : nullptr, buffer.getNumSamples());
    const auto sideSummary = summarize(side.getNumChannels() > 0 ? side.getReadPointer(0) : nullptr, buffer.getNumSamples());
    const auto input = getBusBuffer(buffer, true, inputBus);
    auto output = getBusBuffer(buffer, false, 0);
    DiagnosticEvent event;
    event.tick = static_cast<std::uint64_t>(juce::Time::getHighResolutionTicks());
    event.frame = diagnosticFrame;
    event.block = ++blockCounter;
    event.epoch = diagnosticEpoch;
    event.frames = static_cast<std::uint32_t>(buffer.getNumSamples());
    event.sampleRate = diagnosticRate;
    event.source = static_cast<std::uint8_t>(inputBus);
    event.bypassed = bypassed ? 1 : 0;
    event.midiTruncatedBlocks = truncatedMidiBlocks;
    if (auto* playhead = getPlayHead())
        if (const auto position = playhead->getPosition())
        {
            event.transportKnown = 1;
            event.playing = position->getIsPlaying() ? 1 : 0;
            if (const auto sample = position->getTimeInSamples())
            {
                event.hostSampleKnown = 1;
                event.hostSample = *sample;
            }
        }
    const bool positionKnown = event.hostSampleKnown != 0 && lastHostSampleKnown;
    const bool expectedPositionOverflows = lastHostSample > std::numeric_limits<std::int64_t>::max() - lastHostFrames;
    const bool jumpedWhilePlaying = positionKnown && wasPlaying && event.playing != 0
        && (expectedPositionOverflows || event.hostSample != lastHostSample + lastHostFrames);
    if ((wasPlaying && event.transportKnown != 0 && event.playing == 0)
        || (positionKnown && event.hostSample < lastHostSample) || jumpedWhilePlaying)
    {
        held.fill(0);
        heldKnown = true;
        resetMusical(settings);
    }
    if (event.transportKnown != 0) wasPlaying = event.playing != 0;
    lastHostSample = event.hostSample;
    lastHostSampleKnown = event.hostSampleKnown != 0;
    lastHostFrames = event.frames;
    if (lastSource != inputBus || lastVariant != settings.variant
        || lastBypassed != bypassed || renderedGeneration != settings.generation)
        resetMusical(settings);
    lastBypassed = bypassed;
    selector.configure(settings.harmony);
    // Musical delivery is independent of the 64-record diagnostic budget. The
    // 4096-event safety ceiling fails closed, rather than leaving stuck notes.
    auto next = midi.cbegin();
    const auto end = midi.cend();
    unsigned delivered = 0;
    bool overflow = false;
    const auto* samples = input.getNumChannels() > 0 ? input.getReadPointer(0) : nullptr;
    for (int sample = 0; sample < buffer.getNumSamples(); ++sample)
    {
        while (next != end && (*next).samplePosition <= sample)
        {
            const auto message = *next;
            if (++delivered > 4096 || message.samplePosition < 0)
            {
                selector.panic(); overflow = true; next = end; break;
            }
            if (!bypassed) selector.midi(message.data, message.numBytes);
            ++next;
        }
        if (!bypassed && tracker.push(samples != nullptr ? samples[sample] : 0.0f))
            selector.pitch(tracker.frame());
    }
    if (next != end) { selector.panic(); overflow = true; }
    // Selected input is analysed before the aliased output is written.
    passThrough(samples, output.getWritePointer(0), output.getWritePointer(1), buffer.getNumSamples());
    event.pitchHz = tracker.frame().hz;
    event.pitchConfidence = tracker.frame().confidence;
    event.pitchVoiced = tracker.frame().voiced ? 1 : 0;
    event.pitchBegin = tracker.frame().begin; event.pitchEnd = tracker.frame().end;
    event.pitchAvailable = tracker.frame().available;
    event.trackingEpoch = trackingEpoch;
    event.musicalMidiKnown = selector.midiKnown() ? 1 : 0;
    const auto midiSummary = selector.midiSummary();
    event.musicalKeyPresses = midiSummary.keyPresses;
    event.musicalPhysicalKeys = midiSummary.physicalKeys;
    event.musicalSustainedKeys = midiSummary.sustainedKeys;
    event.musicalSoundingPitches = midiSummary.soundingPitches;
    event.musicalOverflow = overflow ? 1 : 0;
    for (std::size_t i = 0; i < 3; ++i)
    {
        event.targetMidi[i] = selector.targets()[i].midi;
        event.targetActive[i] = selector.targets()[i].active ? 1 : 0;
    }
    auto heldCount = [this]
    {
        unsigned count = 0;
        for (auto mask : held) count += static_cast<unsigned>(std::popcount(mask));
        return static_cast<std::uint16_t>(count);
    };
    unsigned inspected = 0;
    for (const auto message : midi)
    {
        if (inspected++ == 64)
        {
            ++truncatedMidiBlocks;
            heldKnown = false;
            held.fill(0);
            break;
        }
        auto midiEvent = event;
        midiEvent.kind = DiagnosticEvent::Kind::midi;
        midiEvent.offset = message.samplePosition;
        midiEvent.originalMidiSize = static_cast<std::uint32_t>(message.numBytes);
        midiEvent.midiSize = static_cast<std::uint8_t>(std::min(3, message.numBytes));
        for (unsigned i = 0; i < midiEvent.midiSize; ++i) midiEvent.midi[i] = message.data[i];
        const bool validOffset = message.samplePosition >= 0 && message.samplePosition < buffer.getNumSamples();
        if (!validOffset)
        {
            heldKnown = false;
            held.fill(0);
        }
        if (message.numBytes >= 3 && validOffset)
        {
            const auto command = message.data[0] & 0xf0;
            const auto channel = message.data[0] & 0x0f;
            const auto note = message.data[1] & 0x7f;
            auto& mask = held[static_cast<std::size_t>(channel * 2 + note / 64)];
            const auto bit = std::uint64_t { 1 } << (note % 64);
            if (command == 0x90 && message.data[2] != 0) mask |= bit;
            if (command == 0x80 || (command == 0x90 && message.data[2] == 0)) mask &= ~bit;
            if (command == 0xb0 && (message.data[1] == 120 || message.data[1] == 123))
            {
                held[static_cast<std::size_t>(channel * 2)] = 0;
                held[static_cast<std::size_t>(channel * 2 + 1)] = 0;
            }
        }
        midiEvent.heldKeys = heldCount();
        midiEvent.heldKnown = heldKnown ? 1 : 0;
        midiEvent.sequence = ++sequence;
        diagnostics.push(midiEvent);
    }
    const auto left = summarize(output.getReadPointer(0), buffer.getNumSamples());
    const auto right = summarize(output.getReadPointer(1), buffer.getNumSamples());
    event.mainPeak = mainSummary.peak;
    event.sidePeak = sideSummary.peak;
    event.leftPeak = left.peak;
    event.rightPeak = right.peak;
    event.sourceHash = inputBus == 0 ? mainSummary.hash : sideSummary.hash;
    event.leftHash = left.hash;
    event.rightHash = right.hash;
    event.nonFinite = mainSummary.nonFinite + sideSummary.nonFinite + left.nonFinite + right.nonFinite;
    event.heldKeys = heldCount();
    event.heldKnown = heldKnown ? 1 : 0;
    event.midiTruncatedBlocks = truncatedMidiBlocks;
    event.sequence = ++sequence;
    diagnostics.push(event);
    diagnosticFrame += static_cast<std::uint64_t>(buffer.getNumSamples());
    // Tracking/target selection only: unchanged lead; no synthesis or MIDI output.
    midi.clear();
}

namespace
{
class ShellEditor final : public juce::AudioProcessorEditor, private juce::Timer
{
public:
    explicit ShellEditor(Processor& owner)
        : AudioProcessorEditor(owner), ownerProcessor(owner), sourceAttachment(owner.sourceParameter(),
            [this](float value) { source.setSelectedItemIndex(juce::roundToInt(value), juce::dontSendNotification); }, nullptr)
    {
        setWantsKeyboardFocus(false);
        source.addItemList({ "Main input", "Sidechain" }, 1);
        source.setTitle("Vocal source");
        source.setTooltip("Choose the routed bus explicitly. Silent or disconnected sidechain does not fall back to main input.");
        source.onChange = [this] { sourceAttachment.setValueAsCompleteGesture(static_cast<float>(source.getSelectedItemIndex())); };
        sourceAttachment.sendInitialUpdate();
        addAndMakeVisible(source);
        addAndMakeVisible(startLog);
        addAndMakeVisible(stopLog);
        startLog.onClick = [this]
        {
            logAfter = static_cast<std::uint64_t>(juce::Time::getHighResolutionTicks());
            logger.start(juce::File(build::diagnosticDirectory), ownerProcessor.instanceId(), ownerProcessor.diagnosticQueue().dropped());
            repaint();
        };
        stopLog.onClick = [this]
        {
            drain(2048);
            logger.stop(ownerProcessor.diagnosticQueue().dropped());
            repaint();
        };
        startLog.setTitle("Start diagnostic log");
        stopLog.setTitle("Stop diagnostic log");
        // Discard stale queued history; no index reset races with the renderer.
        DiagnosticEvent ignored;
        for (int i = 0; i < 2048 && ownerProcessor.diagnosticQueue().pop(ignored); ++i) {}
        parameterEditor = std::make_unique<juce::GenericAudioProcessorEditor>(owner);
        addAndMakeVisible(*parameterEditor);
        setSize(1100, 600);
        startTimerHz(20);
    }

    ~ShellEditor() override
    {
        stopTimer();
        drain(2048);
        logger.stop(ownerProcessor.diagnosticQueue().dropped());
    }

    void resized() override
    {
        source.setBounds(140, 96, 260, 28);
        startLog.setBounds(20, 332, 190, 30);
        stopLog.setBounds(225, 332, 190, 30);
        if (parameterEditor) parameterEditor->setBounds(680, 0, 420, getHeight());
    }

    void paint(juce::Graphics& g) override
    {
        g.fillAll(juce::Colours::darkslategrey);
        g.setColour(juce::Colours::white);
        g.setFont(20.0f);
        g.drawText("voxide — causal tracking / targets", 20, 16, 640, 32, juce::Justification::left);
        g.setFont(14.0f);
        g.drawText(juce::String(build::version) + " / " + build::diagnosticBuild + " / " + build::revision,
                   20, 48, 640, 22, juce::Justification::left);
        g.drawText("Instance " + ownerProcessor.instanceId(), 20, 70, 640, 22, juce::Justification::left);
        g.drawText("Vocal source", 20, 96, 110, 28, juce::Justification::left);
        const double age = last.tick == 0 ? -1.0 : juce::Time::highResolutionTicksToSeconds(
            juce::Time::getHighResolutionTicks() - static_cast<juce::int64>(last.tick));
        const auto fresh = age >= 0.0 && age < 0.5;
        g.setColour(fresh ? juce::Colours::lightgreen : juce::Colours::orange);
        g.drawText(fresh ? "RENDERING — " + juce::String(last.playing != 0 ? "playing" : "stopped/live")
                         : "STALE / NO CURRENT RENDER CALLBACK", 20, 138, 640, 24, juce::Justification::left);
        g.setColour(juce::Colours::white);
        auto db = [](float peak) { return peak > 0.0f ? juce::String(juce::Decibels::gainToDecibels(peak), 1) : juce::String("−inf"); };
        g.drawText("Main " + db(last.mainPeak) + " dB   Side " + db(last.sidePeak) + " dB   Out "
            + db(last.leftPeak) + " / " + db(last.rightPeak) + " dB", 20, 168, 640, 22, juce::Justification::left);
        g.drawText("Epoch " + juce::String(last.epoch) + "  frame " + juce::String(static_cast<juce::int64>(last.frame))
            + "  host " + juce::String(static_cast<juce::int64>(last.hostSample))
            + "  block " + juce::String(last.frames), 20, 194, 640, 22, juce::Justification::left);
        g.drawText("MIDI seen " + juce::String(static_cast<juce::int64>(midiSeen)) + "  last " + lastMidi
            + "  presses " + (last.musicalMidiKnown != 0 ? juce::String(last.musicalKeyPresses) : juce::String("unknown"))
            + "  sounding " + juce::String(last.musicalSoundingPitches),
            20, 220, 640, 22, juce::Justification::left);
        g.drawText("Dropped records " + juce::String(static_cast<juce::int64>(ownerProcessor.diagnosticQueue().dropped()))
            + "  MIDI-overflow blocks " + juce::String(static_cast<juce::int64>(last.midiTruncatedBlocks)),
            20, 246, 640, 22, juce::Justification::left);
        g.drawText("Dry pass-through only. No harmonies. Logs contain metadata, not PCM.",
            20, 278, 640, 22, juce::Justification::left);
        g.drawText(logger.error().isNotEmpty() ? logger.error() : logger.active() ? "Logging metadata" : "Log stopped (also stops when this editor closes)",
            20, 304, 640, 22, juce::Justification::left);
        g.setFont(11.0f);
        g.drawText(logger.path(), 20, 370, 640, 22, juce::Justification::centredLeft, true);
        g.setFont(14.0f);
        g.drawText("Pitch " + juce::String(last.pitchHz, 2) + " Hz  confidence " + juce::String(last.pitchConfidence, 3)
            + (last.pitchVoiced ? "  VOICED" : "  uncertain / unvoiced"), 20, 410, 640, 24, juce::Justification::left);
        for (int i = 0; i < 3; ++i)
            g.drawText("Voice " + juce::String(i + 1) + ": " + (last.targetActive[i] ? juce::String(last.targetMidi[i], 2) + " MIDI" : "inactive"),
                20, 442 + 26 * i, 640, 24, juce::Justification::left);
        g.drawText("12-TET sets only. Degree steps: 0 = unison, 2 = third. Octaves separate.", 20, 536, 640, 24, juce::Justification::left);
        g.drawText("Readouts are callback snapshots; no audible harmonies yet.", 20, 562, 640, 24, juce::Justification::left);
    }

private:
    void drain(int budget = 512)
    {
        DiagnosticEvent event;
        for (int i = 0; i < budget && ownerProcessor.diagnosticQueue().pop(event); ++i)
        {
            if (event.kind == DiagnosticEvent::Kind::audio) last = event;
            else
            {
                ++midiSeen;
                lastMidi = juce::String::toHexString(event.midi, event.midiSize, 0)
                    + " @" + juce::String(event.offset);
            }
            if (event.tick >= logAfter) logger.append(event);
        }
    }
    void timerCallback() override
    {
        drain();
        startLog.setEnabled(!logger.active());
        stopLog.setEnabled(logger.active());
        repaint();
    }
    Processor& ownerProcessor;
    DiagnosticEvent last;
    std::uint64_t midiSeen = 0, logAfter = 0;
    juce::String lastMidi = "none";
    DiagnosticLog logger;
    juce::ComboBox source;
    juce::TextButton startLog { "Start diagnostic log" }, stopLog { "Stop diagnostic log" };
    juce::ParameterAttachment sourceAttachment;
    std::unique_ptr<juce::GenericAudioProcessorEditor> parameterEditor;
};
}

juce::AudioProcessorEditor* Processor::createEditor() { return new ShellEditor(*this); }

void Processor::getStateInformation(juce::MemoryBlock& destination)
{
    constexpr char prefix[] = "voxide-tracking-v3";
    const auto& parameters = getParameters();
    destination.setSize(sizeof(prefix) + static_cast<std::size_t>(parameters.size()) * sizeof(float));
    std::memcpy(destination.getData(), prefix, sizeof(prefix));
    auto* bytes = static_cast<unsigned char*>(destination.getData()) + sizeof(prefix);
    for (auto* parameter : parameters)
    {
        const auto bits = std::bit_cast<std::uint32_t>(parameter->getValue());
        for (unsigned j = 0; j < 4; ++j) *bytes++ = static_cast<unsigned char>(bits >> (j * 8));
    }
}

void Processor::setStateInformation(const void* data, int size)
{
    if (data == nullptr || size <= 0) return;
    constexpr char legacy[] = "voxide-shell-v1";
    constexpr char prefix[] = "voxide-shell-v2";
    constexpr char current[] = "voxide-tracking-v3";
    const auto& parameters = getParameters();
    if (size == static_cast<int>(sizeof(current) + static_cast<std::size_t>(parameters.size()) * sizeof(float))
        && std::memcmp(data, current, sizeof(current)) == 0)
    {
        std::array<float, 23> values {};
        if (parameters.size() != static_cast<int>(values.size())) return;
        const auto* bytes = static_cast<const unsigned char*>(data) + sizeof(current);
        for (auto& value : values)
        {
            std::uint32_t bits = 0;
            for (unsigned j = 0; j < 4; ++j) bits |= static_cast<std::uint32_t>(*bytes++) << (j * 8);
            value = std::bit_cast<float>(bits);
            if (!std::isfinite(value) || value < 0 || value > 1) return;
        }
        for (int i = 0; i < parameters.size(); ++i) parameters[i]->setValueNotifyingHost(values[static_cast<std::size_t>(i)]);
        stateGeneration.fetch_add(1, std::memory_order_release);
        return;
    }
    auto restoreLegacy = [&](int source)
    {
        for (auto* parameter : parameters) parameter->setValueNotifyingHost(parameter->getDefaultValue());
        sourceChoice->setValueNotifyingHost(static_cast<float>(source));
        stateGeneration.fetch_add(1, std::memory_order_release);
    };
    if (size == static_cast<int>(sizeof(legacy)) && std::memcmp(data, legacy, sizeof(legacy)) == 0)
        restoreLegacy(0);
    else if (size == static_cast<int>(sizeof(prefix) + 1) && std::memcmp(data, prefix, sizeof(prefix)) == 0)
    {
        const auto sourceIndex = static_cast<const unsigned char*>(data)[sizeof(prefix)];
        if (sourceIndex <= 1) restoreLegacy(sourceIndex);
    }
}
}
