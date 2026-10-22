#include "PluginProcessor.h"
#include "AllocationAudit.h"
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <vector>
#include <bit>
#include <functional>
void runTrackingProcessorTests();

namespace
{
void check(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
void set(voxide::Processor& p, const char* id, float real)
{
    for (auto* base : p.getParameters())
        if (auto* parameter = dynamic_cast<juce::RangedAudioParameter*>(base); parameter != nullptr && parameter->paramID == id)
        {
            parameter->setValueNotifyingHost(parameter->convertTo0to1(real));
            return;
        }
    throw std::runtime_error("Parameter not found");
}
struct Position final : juce::AudioPlayHead
{
    bool playing = true;
    juce::int64 sample = 0;
    mutable std::function<void()> onPosition;
    juce::Optional<PositionInfo> getPosition() const override
    {
        if (onPosition) { auto callback = std::move(onPosition); callback(); }
        PositionInfo info; info.setIsPlaying(playing); info.setTimeInSamples(sample); return info;
    }
};
void stateTests()
{
    voxide::Processor p;
    check(p.getParameters().size() == 23, "v3 state parameter layout changed");
    for (int i = 0; i < p.getParameters().size(); ++i)
        check(p.getParameters()[i]->getVersionHint() == (i == 0 ? 1 : 2), "AU version hints no longer preserve legacy automation order");
    for (int i = 0; i < p.getParameters().size(); ++i)
        p.getParameters()[i]->setValueNotifyingHost(static_cast<float>(i % 5) / 4);
    juce::MemoryBlock expected, actual;
    p.getStateInformation(expected);
    for (auto* param : p.getParameters()) param->setValueNotifyingHost(param->getDefaultValue());
    p.setStateInformation(expected.getData(), static_cast<int>(expected.getSize()));
    p.getStateInformation(actual); check(actual == expected, "Full musical state roundtrip failed");
    auto corrupt = expected;
    std::memset(static_cast<char*>(corrupt.getData()) + corrupt.getSize() - 4, 0xff, 4);
    p.setStateInformation(corrupt.getData(), static_cast<int>(corrupt.getSize()));
    p.getStateInformation(actual); check(actual == expected, "Invalid float partially changed state");
    p.setStateInformation(expected.getData(), static_cast<int>(expected.getSize()) - 1);
    p.getStateInformation(actual); check(actual == expected, "Truncated state changed parameters");
    constexpr char legacy[] = "voxide-shell-v2";
    std::array<unsigned char, sizeof(legacy) + 1> v2 {};
    std::memcpy(v2.data(), legacy, sizeof(legacy)); v2.back() = 1;
    p.setStateInformation(v2.data(), static_cast<int>(v2.size()));
    check(p.sourceParameter().getIndex() == 1, "Legacy v2 source lost");
    for (int i = 1; i < p.getParameters().size(); ++i)
        check(std::bit_cast<std::uint32_t>(p.getParameters()[i]->getValue()) == std::bit_cast<std::uint32_t>(p.getParameters()[i]->getDefaultValue()), "Legacy state retained new musical parameters");
    p.getStateInformation(expected); v2.back() = 2;
    p.setStateInformation(v2.data(), static_cast<int>(v2.size()));
    p.getStateInformation(actual); check(expected == actual, "Invalid legacy source changed state");
}
struct Result { voxide::PitchFrame frame; std::array<int,3> slots; std::array<voxide::HarmonyTarget,3> targets; };
Result render(const std::vector<int>& blocks, bool side)
{
    voxide::Processor p;
    auto layout = p.getBusesLayout(); layout.inputBuses.set(1, juce::AudioChannelSet::mono());
    check(p.setBusesLayout(layout), "Tracking sidechain layout failed");
    set(p, "sourceBus", side ? 1.0f : 0.0f); set(p, "harmonyMode", 1);
    p.prepareToPlay(48000, 1024);
    int at = 0;
    std::size_t partition = 0;
    while (at < 12000)
    {
        const int length = std::min(blocks[partition++ % blocks.size()], 12000 - at);
        juce::AudioBuffer<float> audio(2, length); audio.clear();
        auto source = p.getBusBuffer(audio, true, side ? 1 : 0);
        for (int i = 0; i < length; ++i) source.setSample(0, i, static_cast<float>(0.2 * std::sin((at + i) * 6.283185307179586 * 220 / 48000)));
        juce::MidiBuffer midi;
        for (int event : { 0, 49, 257, 769, 1001, 4095, 9000 })
            if (event >= at && event < at + length)
                midi.addEvent(event == 9000 ? juce::MidiMessage::noteOff(1, 64) : juce::MidiMessage::noteOn(1, 60 + event % 12, 0.8f), event - at);
        voxide::audit::begin(); p.processBlock(audio, midi); const auto count = voxide::audit::end();
        check(count == 0, "Processor callback allocated");
        for (int i = 0; i < length; ++i)
            check(std::bit_cast<std::uint32_t>(audio.getSample(0, i)) == std::bit_cast<std::uint32_t>(audio.getSample(1, i)), "Analysed dry lead changed");
        at += length;
    }
    check(p.pitchFrame().voiced && std::abs(p.pitchFrame().hz - 220) < 1, "Wrong selected source analysed");
    return { p.pitchFrame(), p.harmonyState().midiSlots(), p.harmonyState().targets() };
}
void recoveryTests()
{
    voxide::Processor p; Position position; p.setPlayHead(&position);
    p.prepareToPlay(48000, 1024); set(p, "harmonyMode", 1);
    juce::AudioBuffer<float> audio(2, 1024); audio.clear(); juce::MidiBuffer midi;
    for (int i = 0; i < 70; ++i) midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), 0);
    for (int i = 0; i < 70; ++i) midi.addEvent(juce::MidiMessage::noteOff(1, 60), 1);
    p.processBlock(audio, midi);
    check(p.harmonyState().midiSlots()[0] == -1 && p.harmonyState().midiKnown(), "Diagnostic cap truncated musical releases");
    midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), 0); position.sample += 1024; p.processBlock(audio, midi);
    check(p.harmonyState().midiSlots()[0] == 60, "MIDI note not delivered");
    position.playing = false; position.sample += 1024; p.processBlock(audio, midi);
    check(p.harmonyState().midiSlots()[0] == -1, "Stop retained held note");
    position.playing = true; position.sample += 1024;
    midi.addEvent(juce::MidiMessage::noteOn(1, 62, 0.5f), 0); p.processBlock(audio, midi);
    position.sample = 0; p.processBlock(audio, midi);
    check(p.harmonyState().midiSlots()[0] == -1 && p.pitchFrame().available == 0, "Seek retained tracking/held history");
    position.sample += 1024;
    for (int i = 0; i < 4097; ++i) midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), 0);
    voxide::audit::begin(); p.processBlock(audio, midi); const auto count = voxide::audit::end();
    check(count == 0 && !p.harmonyState().midiKnown(), "Musical event overflow did not fail closed allocation-free");
    p.reset(); check(p.harmonyState().midiKnown(), "Reset did not recover unknown MIDI");
    midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), 0); p.processBlock(audio, midi);
    p.processBlockBypassed(audio, midi);
    check(p.harmonyState().midiSlots()[0] == -1, "Bypass retained held state");
    p.processBlock(audio, midi); check(p.harmonyState().midiSlots()[0] == -1, "Unbypass revived notes");
    midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), 0); p.processBlock(audio, midi);
    juce::MemoryBlock saved; p.getStateInformation(saved); p.setStateInformation(saved.getData(), static_cast<int>(saved.getSize()));
    p.processBlock(audio, midi); check(p.harmonyState().midiSlots()[0] == -1, "State recall retained transient MIDI");
    midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), 1024); p.processBlock(audio, midi);
    check(!p.harmonyState().midiKnown(), "Invalid offset did not fail closed");
}
void snapshotTests()
{
    voxide::Processor p; Position position; p.setPlayHead(&position);
    auto layout = p.getBusesLayout(); layout.inputBuses.set(1, juce::AudioChannelSet::mono());
    check(p.setBusesLayout(layout), "Snapshot test layout failed");
    p.prepareToPlay(48000, 1024);
    juce::AudioBuffer<float> audio(2, 1024); juce::MidiBuffer midi;
    auto renderBlock = [&]
    {
        for (int i = 0; i < 1024; ++i)
        {
            const auto sample = static_cast<double>(position.sample + i);
            audio.setSample(0, i, static_cast<float>(0.2 * std::sin(sample * 6.283185307179586 * 220 / 48000)));
            audio.setSample(1, i, static_cast<float>(0.2 * std::sin(sample * 6.283185307179586 * 330 / 48000)));
        }
        p.processBlock(audio, midi); position.sample += 1024;
    };
    renderBlock(); renderBlock(); renderBlock();
    check(p.pitchFrame().voiced, "Snapshot test failed to warm tracker");
    position.playing = false;
    position.onPosition = [&] { set(p, "sourceBus", 1); set(p, "pitchTracker", 0); };
    renderBlock(); // Main was captured before the host changed the controls.
    renderBlock(); // New Side/variant must start a fresh history, not reuse Main.
    check(p.pitchFrame().available == 0, "Mid-callback source/variant change mixed histories");
    renderBlock(); renderBlock();
    check(p.pitchFrame().voiced && std::abs(p.pitchFrame().hz - 330) < 1, "New source was not tracked after snapshot reset");
    position.onPosition = [&] { set(p, "voiceDegree1", 0); };
    const auto shift = p.harmonyState().targets()[0].shift;
    renderBlock();
    check(std::abs(p.harmonyState().targets()[0].shift - shift) < 1e-9, "Harmony config changed within captured callback");
    renderBlock();
    check(std::abs(p.harmonyState().targets()[0].shift) < 1e-9, "Harmony config was not applied on next callback");
    midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), 0); renderBlock();
    juce::MemoryBlock saved; p.getStateInformation(saved);
    position.onPosition = [&] { p.setStateInformation(saved.getData(), static_cast<int>(saved.getSize())); };
    renderBlock();
    check(p.harmonyState().midiSummary().keyPresses == 1, "Recall generation was reread mid-callback");
    renderBlock();
    check(p.harmonyState().midiSummary().keyPresses == 0 && p.pitchFrame().available == 0, "Recall generation did not reset next callback");
}
void authoritativeMidiDiagnostics()
{
    voxide::Processor p; p.prepareToPlay(48000, 64);
    juce::AudioBuffer<float> audio(2, 64); audio.clear(); juce::MidiBuffer midi;
    midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), 0);
    midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), 1);
    midi.addEvent(juce::MidiMessage::noteOff(1, 60), 2);
    p.processBlock(audio, midi);
    voxide::DiagnosticEvent event, last;
    while (p.diagnosticQueue().pop(event)) if (event.kind == voxide::DiagnosticEvent::Kind::audio) last = event;
    check(last.musicalMidiKnown && last.musicalKeyPresses == 1 && last.musicalPhysicalKeys == 1
        && last.musicalSoundingPitches == 1, "Release diagnostics lost repeated held note");
    midi.addEvent(juce::MidiMessage::controllerEvent(1, 64, 127), 0);
    midi.addEvent(juce::MidiMessage::noteOff(1, 60), 1);
    p.processBlock(audio, midi);
    while (p.diagnosticQueue().pop(event)) if (event.kind == voxide::DiagnosticEvent::Kind::audio) last = event;
    check(last.musicalKeyPresses == 0 && last.musicalPhysicalKeys == 0 && last.musicalSustainedKeys == 1
        && last.musicalSoundingPitches == 1, "Release diagnostics lost pedal-held sounding note");
}
}
void runTrackingProcessorTests()
{
    if (voxide::audit::available) check(voxide::audit::selfTest(), "Processor allocation audit self-test failed");
    stateTests(); recoveryTests(); snapshotTests(); authoritativeMidiDiagnostics();
    const auto reference = render({1}, false);
    for (bool side : { false, true })
        for (auto blocks : {std::vector<int>{32}, {64}, {128}, {257}, {512}, {1024}, {32,257,1,1024,128,64,512}})
        {
            const auto actual = render(blocks, side);
            check(std::bit_cast<std::uint64_t>(reference.frame.hz) == std::bit_cast<std::uint64_t>(actual.frame.hz) && reference.frame.available == actual.frame.available
                && reference.slots == actual.slots, "Processor partition/source changed musical decisions");
            for (std::size_t i = 0; i < 3; ++i)
                check(reference.targets[i].active == actual.targets[i].active && std::bit_cast<std::uint64_t>(reference.targets[i].midi) == std::bit_cast<std::uint64_t>(actual.targets[i].midi), "Processor partition target mismatch");
        }
}
