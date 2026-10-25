#include "PluginProcessor.h"
#include <bit>
#include <cmath>
#include <cstring>
#include <limits>

namespace voxide
{
namespace
{
juce::AudioParameterFloatAttributes levelAttributes()
{
    return juce::AudioParameterFloatAttributes().withLabel("dB")
        .withStringFromValueFunction([](float value,int){return value<=-60?juce::String("Off"):juce::String(value,1);})
        .withValueFromStringFunction([](const juce::String& text){return text.trim().equalsIgnoreCase("Off")?-60.f:text.getFloatValue();});
}
}
Processor::Processor(studio::Factory nativeFactory)
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::mono(), true)
          .withInput("Vocal sidechain", juce::AudioChannelSet::mono(), false)
          .withOutput("Output", juce::AudioChannelSet::stereo(), true)), factory(nativeFactory)
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
    for (std::size_t i=0;i<3;++i)
    {
        const auto suffix=juce::String(static_cast<int>(i+1));
        voiceEnabled[i]=new juce::AudioParameterBool(juce::ParameterID{"voiceEnabled"+suffix,3},"Voice "+suffix+" enabled",true);
        voiceLevels[i]=new juce::AudioParameterFloat(juce::ParameterID{"voiceLevel"+suffix,3},"Voice "+suffix+" level",juce::NormalisableRange<float>{-60,0},0,
            levelAttributes());
        addParameter(voiceEnabled[i]);addParameter(voiceLevels[i]);
    }
    originalLevel=new juce::AudioParameterFloat(juce::ParameterID{"originalLevel",3},"Original level",juce::NormalisableRange<float>{-60,0},0,
        levelAttributes());
    addParameter(originalLevel);
}
Processor::~Processor() { releaseResources(); }

void Processor::prepareToPlay(double rate, int)
{
    releaseResources();
    const int latency=std::isfinite(rate) && rate>0 && rate<=384000?static_cast<int>(std::floor(rate*.1)):0;
    setLatencySamples(latency);leadDelay.assign(static_cast<std::size_t>(latency),0);leadPosition=0;
    diagnosticRate = rate;
    {
        // Host preparation is off render. Wait for a complete recall instead of
        // seeding the render cache/gain ramps with an in-flight transaction.
        const std::lock_guard lock(stateMutex);
        renderedSettings=captureSettings();
    }
    resetMusical(renderedSettings);
    voiceGains=renderedSettings.voiceGain;originalGain=renderedSettings.originalGain;
    diagnosticFrame=0;++diagnosticEpoch;held.fill(0);heldKnown=true;wasPlaying=false;
    lastHostSampleKnown=false;lastHostFrames=0;lastSource=renderedSettings.source;lastBypassed=false;lastOffline=false;
    renderedReset=resetGeneration.load(std::memory_order_acquire);renderedRestart=restartGeneration.load(std::memory_order_acquire);
    if (!juce::exactlyEqual(rate,44100.) && !juce::exactlyEqual(rate,48000.)) { renderStatus.store(studio::Status::unsupportedRate);return; }
    try { session=std::make_unique<studio::Session>(static_cast<int>(rate),factory);renderStatus.store(session->snapshot().status); }
    catch (...) { renderStatus.store(studio::Status::initializationFailed); }
}

void Processor::reset()
{
    resetGeneration.fetch_add(1,std::memory_order_release);
}
void Processor::releaseResources()
{
    session.reset();renderStatus.store(studio::Status::preparing);studioHz.store(0);studioActive.store(0);meterPeak.store(0);lastRenderTick.store(0);
}
studio::Snapshot Processor::studioStatus() const noexcept
{ return {renderStatus.load(std::memory_order_relaxed),studioHz.load(std::memory_order_relaxed),studioActive.load(std::memory_order_relaxed)}; }

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
    RenderSettings settings;settings.source=sourceChoice->getIndex();settings.variant=trackerChoice->getIndex();
    settings.harmony=musicalConfig();settings.generation=generation;
    auto gain=[](float db) { return db<=-60?0.f:juce::Decibels::decibelsToGain(db); };
    for (std::size_t i=0;i<3;++i) settings.voiceGain[i]=voiceEnabled[i]->get()?gain(voiceLevels[i]->get()):0.f;
    settings.originalGain=gain(originalLevel->get());return settings;
}
Processor::RenderSettings Processor::readSettings() noexcept
{
    // A recall is a multi-parameter transaction. Never spin, wait, or lock the
    // renderer: an overlapping transaction leaves the previous snapshot intact.
    const auto before=stateGeneration.load(std::memory_order_acquire);
    if (!(before&1u))
    {
        for (auto* p:getParameters())
        {
            const float value=p->getValue();
            if (!std::isfinite(value) || value<0 || value>1)
            { if (session) session->fail();return renderedSettings; }
        }
        const auto candidate=captureSettings();
        const auto after=stateGeneration.load(std::memory_order_acquire);
        if (before==after) renderedSettings=candidate;
    }
    return renderedSettings;
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
    const auto settings = readSettings();
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
    const auto reset=resetGeneration.load(std::memory_order_acquire),restart=restartGeneration.load(std::memory_order_acquire);
    const bool hostReset=reset!=renderedReset;
    const bool offline=isNonRealtime();
    bool discontinuity=lastSource!=inputBus || offline!=lastOffline || (hostReset && bypassed==lastBypassed);
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
    if ((lastHostFrames>0 && event.transportKnown!=0 && wasPlaying!=(event.playing!=0))
        || (positionKnown && event.hostSample < lastHostSample) || jumpedWhilePlaying) discontinuity=true;
    const bool harmonyRestart=renderedGeneration!=settings.generation || restart!=renderedRestart || lastVariant!=settings.variant;
    if (discontinuity || hostReset || harmonyRestart)
    {
        held.fill(0);
        heldKnown = true;
        resetMusical(settings);
    }
    if (discontinuity) { std::fill(leadDelay.begin(),leadDelay.end(),0.f);leadPosition=0; }
    if (session && (discontinuity || hostReset || harmonyRestart)) session->restart(restart!=renderedRestart);
    if (session) session->begin(settings.harmony,settings.variant==0?TrackerVariant::yin:TrackerVariant::multiCandidate,offline,settings.harmony.midiMode);
    renderedReset=reset;renderedRestart=restart;lastOffline=offline;
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
    const float step=diagnosticRate>0?static_cast<float>(1./(.01*diagnosticRate)):1.f;
    for (int i=0;i<buffer.getNumSamples();++i)
    {
        float sample=samples?samples[i]:0;
        if (!std::isfinite(sample)) sample=0;
        float lead=sample;
        if (!leadDelay.empty()) { lead=leadDelay[leadPosition];leadDelay[leadPosition]=sample;if (++leadPosition==leadDelay.size()) leadPosition=0; }
        originalGain+=std::clamp(settings.originalGain-originalGain,-step,step);
        const auto voices=session?session->push(sample):std::array<float,3>{};
        double wet=0;
        for (std::size_t v=0;v<3;++v)
        { voiceGains[v]+=std::clamp(settings.voiceGain[v]-voiceGains[v],-step,step);wet+=static_cast<double>(voices[v])*voiceGains[v]/3.; }
        float dry=bypassed?lead:lead*originalGain;
        if (!std::isfinite(dry)) { if (session) session->fail();dry=lead; }
        const double mixed=bypassed?static_cast<double>(lead):static_cast<double>(dry)+wet;
        const bool valid=std::isfinite(mixed) && std::abs(mixed)<=std::numeric_limits<float>::max();
        if (!valid && session) session->fail();
        const float value=valid?static_cast<float>(mixed):dry;
        for (int channel=0;channel<output.getNumChannels();++channel) output.setSample(channel,i,value);
    }
    if (session)
    {
        const auto status=session->snapshot();renderStatus.store(status.status,std::memory_order_relaxed);studioHz.store(status.hz,std::memory_order_relaxed);
        unsigned active=status.active;
        for (std::size_t v=0;v<3;++v) if (settings.voiceGain[v]<=0) active&=~(1u<<v);
        studioActive.store(bypassed?0:active,std::memory_order_relaxed);
    }
    meterPeak.store(inputBus==0?mainSummary.peak:sideSummary.peak,std::memory_order_relaxed);
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
    lastRenderTick.store(static_cast<std::int64_t>(event.tick),std::memory_order_relaxed);
    diagnosticFrame += static_cast<std::uint64_t>(buffer.getNumSamples());
    // MIDI remains compatibility/diagnostic input, never generated output.
    midi.clear();
}

void Processor::getStateInformation(juce::MemoryBlock& destination)
{
    const std::lock_guard lock(stateMutex);
    constexpr char prefix[] = "voxide-studio-v4";
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

void Processor::applyState(const std::array<float,30>& values)
{
    // Called under stateMutex, including reentrant host/listener calls. Coalesce
    // nested requests into one last-wins deferred recall. Notifications from that
    // deferred recall cannot schedule another, bounding recursive listener cycles.
    if (recallingState)
    {
        if (!applyingDeferredState) deferredState=values;
        return;
    }
    const juce::ScopedValueSetter<bool> recalling(recallingState,true);
    deferredState.reset();
    auto publish=[&](const std::array<float,30>& state)
    {
        stateGeneration.fetch_add(1,std::memory_order_acq_rel);
        const auto& parameters=getParameters();
        for (int i=0;i<parameters.size();++i) parameters[i]->setValue(state[static_cast<std::size_t>(i)]);
        stateGeneration.fetch_add(1,std::memory_order_release);
        // Only a complete, even-generation state is observable to synchronous
        // listeners, including reentrant saves/preparation and render callbacks.
        for (auto* p:parameters) p->sendValueChangedMessageToListeners(p->getValue());
    };
    publish(values);
    if (deferredState)
    {
        const auto pending=*deferredState;deferredState.reset();
        const juce::ScopedValueSetter<bool> deferred(applyingDeferredState,true);
        publish(pending);
    }
}

void Processor::setStateInformation(const void* data, int size)
{
    const std::lock_guard lock(stateMutex);
    if (data == nullptr || size <= 0) return;
    constexpr char legacy[] = "voxide-shell-v1";
    constexpr char prefix[] = "voxide-shell-v2";
    constexpr char tracking[] = "voxide-tracking-v3";
    constexpr char current[] = "voxide-studio-v4";
    const auto& parameters = getParameters();
    const bool v4=size==static_cast<int>(sizeof(current)+30*sizeof(float)) && std::memcmp(data,current,sizeof(current))==0;
    const bool v3=size==static_cast<int>(sizeof(tracking)+23*sizeof(float)) && std::memcmp(data,tracking,sizeof(tracking))==0;
    if (v4 || v3)
    {
        std::array<float, 30> values {};
        if (parameters.size() != static_cast<int>(values.size())) return;
        for (std::size_t i=0;i<values.size();++i) values[i]=parameters[static_cast<int>(i)]->getDefaultValue();
        if (v3) for (std::size_t i=23;i<29;i+=2) values[i]=0; // Old sessions were dry-only.
        const auto* bytes = static_cast<const unsigned char*>(data) + (v4?sizeof(current):sizeof(tracking));
        for (std::size_t index=0;index<(v4?30u:23u);++index)
        {
            std::uint32_t bits = 0;
            for (unsigned j = 0; j < 4; ++j) bits |= static_cast<std::uint32_t>(*bytes++) << (j * 8);
            const auto value = std::bit_cast<float>(bits);
            if (!std::isfinite(value) || value < 0 || value > 1) return;
            values[index]=value;
        }
        applyState(values);
        return;
    }
    auto restoreLegacy = [&](int source)
    {
        std::array<float,30> values {};
        for (std::size_t i=0;i<values.size();++i) values[i]=parameters[static_cast<int>(i)]->getDefaultValue();
        values[0]=static_cast<float>(source);
        for (std::size_t i=23;i<29;i+=2) values[i]=0;
        applyState(values);
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
