#include "PluginProcessor.h"
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>

namespace
{
void require(bool condition, const char* message)
{
    if (!condition) throw std::runtime_error(message);
}

void checkRender(voxide::Processor& processor, int frames, bool sidechain, bool bypassed)
{
    juce::AudioBuffer<float> buffer(juce::jmax(processor.getTotalNumInputChannels(),
                                            processor.getTotalNumOutputChannels()), frames);
    buffer.clear();
    for (int channel = 0; channel < buffer.getNumChannels(); ++channel)
        for (int i = 0; i < frames; ++i)
            buffer.setSample(channel, i, 0.75f);
    auto source = processor.getBusBuffer(buffer, true, sidechain ? 1 : 0);
    for (int i = 0; i < frames && source.getNumChannels() > 0; ++i)
        source.setSample(0, i, static_cast<float>(i % 17 - 8) / 16.0f);
    juce::MidiBuffer midi;
    if (frames > 0) midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), frames - 1);
    if (bypassed) processor.processBlockBypassed(buffer, midi);
    else processor.processBlock(buffer, midi);
    auto output = processor.getBusBuffer(buffer, false, 0);
    for (int i = 0; i < frames; ++i)
        for (int channel = 0; channel < 2; ++channel)
            require(std::bit_cast<std::uint32_t>(output.getSample(channel, i))
                         == std::bit_cast<std::uint32_t>(source.getNumChannels() > 0 ? static_cast<float>(i % 17 - 8) / 16.0f : 0.0f),
                    "Pass-through channel/alias mismatch");
    require(midi.isEmpty(), "Unexpected MIDI output");
}
}

int main()
{
    try
    {
        // No audio device, microphone, GUI window, install, or host is opened.
        voxide::Processor processor;
        require(processor.acceptsMidi() && !processor.producesMidi() && !processor.isMidiEffect(),
                "Wrong MIDI contract");
        require(processor.getMainBusNumInputChannels() == 1
                    && processor.getMainBusNumOutputChannels() == 2, "Wrong default layout");
        for (const auto rate : { 44100.0, 48000.0 })
        {
            processor.prepareToPlay(rate, 1024);
            require(processor.getLatencySamples() == 0 && processor.getTailLengthSeconds() == 0.0,
                    "Unexpected delay/tail");
            for (int mainChannels : { 1, 2 })
            {
                for (int sidechainChannels : { 0, 1, 2 })
                {
                    auto layout = processor.getBusesLayout();
                    layout.inputBuses.set(0, juce::AudioChannelSet::canonicalChannelSet(mainChannels));
                    layout.inputBuses.set(1, juce::AudioChannelSet::canonicalChannelSet(sidechainChannels));
                    require(processor.setBusesLayout(layout), "Source layout rejected");
                    for (int frames : { 0, 1, 32, 64, 128, 257, 512, 1024 })
                        for (bool selectedSidechain : { false, true })
                            for (bool bypassed : { false, true })
                            {
                                processor.sourceParameter().setValueNotifyingHost(selectedSidechain ? 1.0f : 0.0f);
                                checkRender(processor, frames, selectedSidechain, bypassed);
                            }
                }
            }
            processor.releaseResources();
        }
        auto invalid = processor.getBusesLayout();
        invalid.outputBuses.set(0, juce::AudioChannelSet::mono());
        require(!processor.isBusesLayoutSupported(invalid), "Invalid output layout accepted");
        invalid = processor.getBusesLayout();
        invalid.inputBuses.set(1, juce::AudioChannelSet::create5point1());
        require(!processor.isBusesLayoutSupported(invalid), "Invalid sidechain accepted");
        juce::MemoryBlock first, second;
        processor.sourceParameter().setValueNotifyingHost(1.0f);
        processor.getStateInformation(first);
        processor.sourceParameter().setValueNotifyingHost(0.0f);
        processor.setStateInformation(first.getData(), static_cast<int>(first.getSize()));
        require(processor.sourceParameter().getIndex() == 1, "Source recall failed");
        processor.setStateInformation(nullptr, 0);
        const char malformed[] = "invalid";
        processor.setStateInformation(malformed, sizeof(malformed));
        processor.getStateInformation(second);
        require(first == second, "Malformed state changed source");
        auto invalidState = first;
        static_cast<unsigned char*>(invalidState.getData())[invalidState.getSize() - 1] = 2;
        processor.setStateInformation(invalidState.getData(), static_cast<int>(invalidState.getSize()));
        require(processor.sourceParameter().getIndex() == 1, "Invalid source choice accepted");
        constexpr char legacy[] = "voxide-shell-v1";
        processor.setStateInformation(legacy, sizeof(legacy));
        require(processor.sourceParameter().getIndex() == 0, "Legacy source default failed");
        std::cout << "Processor: main/sidechain, rates/blocks, MIDI, layout, state passed\n";
        return EXIT_SUCCESS;
    }
    catch (const std::exception& error)
    {
        std::cerr << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
