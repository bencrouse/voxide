#include "DiagnosticLog.h"
#include "BuildInfo.h"

namespace voxide
{
bool DiagnosticLog::write(juce::DynamicObject* object)
{
    const auto line = juce::JSON::toString(juce::var(object), true) + "\n";
    if (stream != nullptr && stream->write(line.toRawUTF8(), line.getNumBytesAsUTF8()))
        return true;
    failure = "Diagnostic log write failed";
    stream.reset();
    return false;
}

bool DiagnosticLog::start(const juce::File& directory, const juce::String& instance, std::uint64_t droppedBefore)
{
    if (active()) return false;
    droppedBaseline = droppedBefore;
    lastSequence = 0;
    pendingCount = 0;
    failure.clear();
    if (directory.createDirectory().failed())
    {
        failure = "Cannot create local diagnostics directory";
        return false;
    }
    file = directory.getChildFile(juce::Uuid().toString() + ".jsonl");
    if (file.exists()) { failure = "Refusing existing log path"; return false; }
    // JUCE's buffered flush discards the short-write result. With buffering off,
    // every JSONL write returns false on a partial write, even if status stays OK.
    stream = streamFactory ? streamFactory(file) : std::make_unique<juce::FileOutputStream>(file, 0);
    if (stream == nullptr || !stream->openedOk())
    {
        failure = "Cannot open diagnostic log";
        stream.reset();
        return false;
    }
    auto* header = new juce::DynamicObject();
    header->setProperty("kind", "header");
    header->setProperty("schema", "voxide.routing.v1");
    header->setProperty("instance", instance);
    header->setProperty("version", build::version);
    header->setProperty("build", build::diagnosticBuild);
    header->setProperty("revision", build::revision);
    header->setProperty("profile", build::profile);
    const auto started = juce::Time::getCurrentTime();
    header->setProperty("started_at", started.toISO8601(true));
    header->setProperty("unix_ms", started.toMilliseconds());
    header->setProperty("tick_hz", juce::Time::getHighResolutionTicksPerSecond());
    header->setProperty("pcm_recorded", false);
    header->setProperty("hash_algorithm", "word-fnv64-v1");
    header->setProperty("dropped_before_capture", static_cast<juce::int64>(droppedBefore));
    return write(header);
}

void DiagnosticLog::append(const DiagnosticEvent& event)
{
    if (!active()) return;
    if (pendingCount != 0 && (pendingMidi[0].block != event.block
                             || pendingMidi[0].epoch != event.epoch))
    {
        failure = "Diagnostic block summary missing";
        stream.reset();
        return;
    }
    if (event.kind == DiagnosticEvent::Kind::midi)
    {
        if (pendingCount == pendingMidi.size())
        {
            failure = "Diagnostic block exceeded MIDI record limit";
            stream.reset();
            return;
        }
        pendingMidi[pendingCount++] = event;
        return;
    }
    for (std::size_t i = 0; i < pendingCount && active(); ++i) writeEvent(pendingMidi[i]);
    pendingCount = 0;
    if (active()) writeEvent(event);
}

void DiagnosticLog::writeEvent(const DiagnosticEvent& event)
{
    auto* row = new juce::DynamicObject();
    row->setProperty("kind", event.kind == DiagnosticEvent::Kind::audio ? "audio" : "midi");
    row->setProperty("tick", static_cast<juce::int64>(event.tick));
    row->setProperty("frame", static_cast<juce::int64>(event.frame));
    row->setProperty("sequence", static_cast<juce::int64>(event.sequence));
    row->setProperty("block", static_cast<juce::int64>(event.block));
    row->setProperty("epoch", static_cast<int>(event.epoch));
    row->setProperty("frames", static_cast<int>(event.frames));
    row->setProperty("sample_rate", event.sampleRate);
    row->setProperty("source", event.source == 0 ? "main" : "sidechain");
    row->setProperty("bypassed", event.bypassed != 0);
    row->setProperty("host_sample", static_cast<juce::int64>(event.hostSample));
    row->setProperty("host_sample_known", event.hostSampleKnown != 0);
    row->setProperty("transport_known", event.transportKnown != 0);
    row->setProperty("playing", event.playing != 0);
    row->setProperty("held_keys", static_cast<int>(event.heldKeys));
    row->setProperty("held_known", event.heldKnown != 0);
    row->setProperty("midi_truncated_blocks", static_cast<juce::int64>(event.midiTruncatedBlocks));
    if (event.kind == DiagnosticEvent::Kind::audio)
    {
        row->setProperty("main_peak", event.mainPeak);
        row->setProperty("side_peak", event.sidePeak);
        row->setProperty("left_peak", event.leftPeak);
        row->setProperty("right_peak", event.rightPeak);
        row->setProperty("non_finite_observations", static_cast<int>(event.nonFinite));
        row->setProperty("source_hash", juce::String::toHexString(static_cast<juce::int64>(event.sourceHash)));
        row->setProperty("left_hash", juce::String::toHexString(static_cast<juce::int64>(event.leftHash)));
        row->setProperty("right_hash", juce::String::toHexString(static_cast<juce::int64>(event.rightHash)));
    }
    else
    {
        row->setProperty("offset", static_cast<int>(event.offset));
        row->setProperty("midi_size", static_cast<int>(event.originalMidiSize));
        row->setProperty("prefix", juce::String::toHexString(event.midi, event.midiSize, 0));
    }
    if (write(row)) lastSequence = event.sequence;
}

void DiagnosticLog::stop(std::uint64_t dropped)
{
    if (!active()) return;
    auto* footer = new juce::DynamicObject();
    footer->setProperty("kind", "end");
    footer->setProperty("dropped_records_total", static_cast<juce::int64>(dropped));
    footer->setProperty("dropped_during_capture", static_cast<juce::int64>(dropped >= droppedBaseline ? dropped - droppedBaseline : 0));
    footer->setProperty("last_sequence", static_cast<juce::int64>(lastSequence));
    footer->setProperty("incomplete_tail_records", static_cast<int>(pendingCount));
    pendingCount = 0;
    write(footer);
    if (stream != nullptr)
    {
        stream->flush();
        if (stream->getStatus().failed()) failure = "Diagnostic log flush failed";
    }
    stream.reset();
}

DiagnosticLog::~DiagnosticLog()
{
    if (active())
    {
        auto* row = new juce::DynamicObject();
        row->setProperty("kind", "aborted");
        row->setProperty("reason", "writer destroyed without explicit stop");
        write(row);
        if (stream != nullptr) stream->flush();
    }
}
}
