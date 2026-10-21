#include "PluginProcessor.h"
#include "DiagnosticLog.h"
#include "DiagnosticsTests.h"
#include <atomic>
#include <stdexcept>
#include <thread>
#include <limits>

namespace
{
void check(bool result, const char* message)
{
    if (!result) throw std::runtime_error(message);
}

class Position final : public juce::AudioPlayHead
{
public:
    bool playing = true;
    juce::int64 sample = 128;
    juce::Optional<PositionInfo> getPosition() const override
    {
        PositionInfo result;
        result.setIsPlaying(playing);
        result.setTimeInSamples(sample);
        return result;
    }
};

class ShortWriteStream final : public juce::FileOutputStream
{
public:
    ShortWriteStream(const juce::File& file, int successfulWrites)
        : FileOutputStream(file, 0), remaining(successfulWrites) {}

    bool write(const void* data, std::size_t size) override
    {
        if (remaining-- > 0) return FileOutputStream::write(data, size);
        // Model a partial filesystem write with no stream-status error.
        FileOutputStream::write(data, size / 2);
        return false;
    }
private:
    int remaining;
};
}

void runDiagnosticsTests()
{
    voxide::DiagnosticQueue<4> small;
    voxide::DiagnosticEvent event, result;
    for (std::uint64_t i = 0; i < 4; ++i) { event.sequence = i; check(small.push(event), "queue filled early"); }
    check(!small.push(event) && small.dropped() == 1 && small.pending() == 4, "overflow not counted");
    for (std::uint64_t i = 0; i < 4; ++i)
        check(small.pop(result) && result.sequence == i, "queue ordering");
    check(!small.pop(result), "queue should be empty");

    voxide::DiagnosticQueue<128> concurrent;
    std::atomic<bool> failed { false };
    std::thread producer([&]
    {
        for (std::uint64_t i = 1; i <= 20000; ++i)
        {
            voxide::DiagnosticEvent next;
            next.sequence = next.frame = i;
            while (!concurrent.push(next)) std::this_thread::yield();
        }
    });
    for (std::uint64_t i = 1; i <= 20000; ++i)
    {
        while (!concurrent.pop(result)) std::this_thread::yield();
        if (result.sequence != i || result.frame != i) failed.store(true);
    }
    producer.join();
    check(!failed.load(), "SPSC torn/out-of-order record");

    voxide::Processor processor;
    Position position;
    processor.setPlayHead(&position);
    processor.prepareToPlay(48000, 64);
    juce::AudioBuffer<float> audio(2, 64);
    audio.clear();
    for (int i = 0; i < 64; ++i) audio.setSample(0, i, 0.125f);
    juce::MidiBuffer midi;
    midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), 7);
    midi.addEvent(juce::MidiMessage::noteOff(1, 60), 23);
    processor.processBlock(audio, midi);
    auto& queue = processor.diagnosticQueue();
    check(queue.pop(result) && result.kind == voxide::DiagnosticEvent::Kind::midi
          && result.offset == 7 && result.heldKeys == 1 && result.midi[0] == 0x90, "note-on diagnostic");
    check(queue.pop(result) && result.offset == 23 && result.heldKeys == 0, "note-off diagnostic");
    check(queue.pop(result) && result.kind == voxide::DiagnosticEvent::Kind::audio, "audio diagnostic missing");
    check(result.hostSample == 128 && result.playing == 1 && result.transportKnown == 1
          && result.frame == 0 && result.frames == 64 && result.sourceHash == result.leftHash
          && result.leftHash == result.rightHash && result.mainPeak > 0.12f, "audio diagnostic context");
    const auto firstEpoch = result.epoch;
    for (int i = 0; i < 100; ++i) midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), i % 64);
    processor.processBlockBypassed(audio, midi);
    int midiCount = 0;
    while (queue.pop(event))
    {
        if (event.kind == voxide::DiagnosticEvent::Kind::midi) ++midiCount;
        else result = event;
    }
    check(midiCount == 64 && result.heldKnown == 0 && result.midiTruncatedBlocks == 1
          && result.bypassed == 1 && result.frame == 64, "bounded MIDI scan/overflow");
    position.playing = false;
    processor.processBlock(audio, midi);
    check(queue.pop(result) && result.heldKnown == 1 && result.heldKeys == 0, "transport-stop recovery");
    processor.prepareToPlay(44100, 64);
    processor.processBlock(audio, midi);
    check(queue.pop(result) && result.epoch != firstEpoch && result.frame == 0, "reprepare epoch");

    std::array<juce::uint8, 4096> sysex {};
    sysex.front() = 0xf0;
    sysex.back() = 0xf7;
    midi.addEvent(sysex.data(), static_cast<int>(sysex.size()), 17);
    processor.processBlock(audio, midi);
    check(queue.pop(event) && event.kind == voxide::DiagnosticEvent::Kind::midi
          && event.originalMidiSize == sysex.size() && event.midiSize == 3
          && event.midi[0] == 0xf0 && event.offset == 17
          && event.midiTruncatedBlocks == 1, "bounded SysEx prefix/prior truncation counter");
    check(queue.pop(result) && result.kind == voxide::DiagnosticEvent::Kind::audio
          && result.midiTruncatedBlocks == event.midiTruncatedBlocks, "SysEx block/counter missing");
    midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), -1);
    processor.processBlock(audio, midi);
    check(queue.pop(event) && event.offset == -1, "Invalid host offset must not be normalized into false evidence");
    while (queue.pop(result)) {}
    processor.reset();
    audio.setSample(0, 0, std::numeric_limits<float>::quiet_NaN());
    processor.processBlock(audio, midi);
    check(queue.pop(event) && event.nonFinite != 0 && event.heldKeys == 0 && event.heldKnown == 1,
          "Reset/non-finite diagnostics");
    audio.setSample(0, 0, 0.125f);
    position.playing = true;
    position.sample = 0;
    midi.addEvent(juce::MidiMessage::noteOn(1, 60, 0.5f), 1);
    processor.processBlock(audio, midi);
    check(queue.pop(event) && event.heldKeys == 1, "Held-key setup before seek");
    check(queue.pop(event) && event.heldKeys == 1, "Held-key block before seek");
    position.sample = 128; // Expected contiguous project position would be 64.
    processor.processBlock(audio, midi);
    check(queue.pop(result) && result.heldKeys == 0 && result.heldKnown == 1, "Forward-seek diagnostic recovery");

    const juce::File directory(VOXIDE_TEST_OUTPUT_DIR);
    voxide::DiagnosticLog log;
    check(log.start(directory, "synthetic-test", 5), "log start failed");
    check(!log.start(directory, "duplicate"), "active log should not be replaced");
    log.append(result);
    const auto path = log.path();
    log.stop(7);
    juce::StringArray lines;
    juce::File(path).readLines(lines);
    lines.removeEmptyStrings();
    check(lines.size() == 3, "log should contain header/event/end");
    check(juce::JSON::parse(lines[0])["pcm_recorded"] == juce::var(false), "PCM privacy marker");
    check(static_cast<int>(juce::JSON::parse(lines[2])["dropped_during_capture"]) == 2, "capture drop baseline");

    // Stop between MIDI publication and its audio summary: keep the prior complete
    // block, report the discarded tail, and never write an orphaned MIDI row.
    check(log.start(directory, "interleaved-test"), "interleaved log start");
    check(juce::File(log.path()).getSize() > 0, "header must be written without a JUCE buffer");
    event = result;
    event.block = event.sequence = 1;
    log.append(event);
    event.kind = voxide::DiagnosticEvent::Kind::midi;
    event.block = event.sequence = 2;
    voxide::DiagnosticQueue<4> interleaved;
    check(interleaved.push(event) && interleaved.pop(event), "interleaved MIDI publication");
    log.append(event);
    log.stop(0);
    lines.clear();
    juce::File(log.path()).readLines(lines);
    lines.removeEmptyStrings();
    check(lines.size() == 3 && juce::JSON::parse(lines[1])["kind"] == juce::var("audio")
          && static_cast<int>(juce::JSON::parse(lines[2])["last_sequence"]) == 1
          && static_cast<int>(juce::JSON::parse(lines[2])["incomplete_tail_records"]) == 1,
          "stop must retain only complete blocks and report incomplete tail");
    event.kind = voxide::DiagnosticEvent::Kind::audio;
    event.sequence = 3;
    check(interleaved.push(event), "late audio summary publication");
    check(log.start(directory, "complete-block-test"), "complete-block log start");
    event.kind = voxide::DiagnosticEvent::Kind::midi;
    event.sequence = 2;
    log.append(event);
    check(interleaved.pop(event), "late audio summary consumption");
    log.append(event);
    log.stop(0);
    lines.clear();
    juce::File(log.path()).readLines(lines);
    lines.removeEmptyStrings();
    check(lines.size() == 4 && juce::JSON::parse(lines[1])["kind"] == juce::var("midi")
          && juce::JSON::parse(lines[2])["kind"] == juce::var("audio")
          && static_cast<int>(juce::JSON::parse(lines[3])["incomplete_tail_records"]) == 0,
          "complete block must flush MIDI before audio");

    for (int successfulWrites = 0; successfulWrites < 3; ++successfulWrites)
    {
        voxide::DiagnosticLog failing([successfulWrites](const juce::File& file)
        {
            return std::make_unique<ShortWriteStream>(file, successfulWrites);
        });
        const bool started = failing.start(directory, "short-write-test");
        check(started == (successfulWrites != 0), "short header write must fail start");
        failing.append(result);
        failing.stop(0);
        check(!failing.active() && failing.error().isNotEmpty(), "short write must fail visibly");
        check(!juce::File(failing.path()).loadFileAsString().trimEnd().endsWith("}"),
              "short-write capture must not appear complete");
    }
    processor.setPlayHead(nullptr);
}
