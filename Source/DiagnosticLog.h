#pragma once
#include "Diagnostics.h"
#include <juce_core/juce_core.h>

namespace voxide
{
// Non-render use only. Contains no PCM samples; records routing summaries and
// bounded MIDI prefixes. The editor owns the sole queue consumer and this writer.
class DiagnosticLog
{
public:
    // Optional factory is a non-render test seam for filesystem write failures.
    using StreamFactory = std::function<std::unique_ptr<juce::FileOutputStream>(const juce::File&)>;
    explicit DiagnosticLog(StreamFactory factory = {}) : streamFactory(std::move(factory)) {}
    bool start(const juce::File& directory, const juce::String& instance, std::uint64_t droppedBefore = 0);
    void append(const DiagnosticEvent& event);
    void stop(std::uint64_t dropped);
    bool active() const noexcept { return stream != nullptr; }
    juce::String path() const { return file.getFullPathName(); }
    juce::String error() const { return failure; }
    ~DiagnosticLog();

private:
    void writeEvent(const DiagnosticEvent&);
    bool write(juce::DynamicObject* object);
    StreamFactory streamFactory;
    std::unique_ptr<juce::FileOutputStream> stream;
    juce::File file;
    juce::String failure;
    std::uint64_t droppedBaseline = 0, lastSequence = 0;
    // MIDI precedes its audio summary in the queue. Never persist a partial block.
    std::array<DiagnosticEvent, 64> pendingMidi;
    std::size_t pendingCount = 0;
};
}
