#pragma once
#include "SessionTelemetry.h"
#include <juce_audio_utils/juce_audio_utils.h>
#include <mutex>
#include <thread>

namespace voxide
{
// UI control owner plus serialized off-render writer, independent of editor lifetime. start is explicit user
// consent to local metadata/file identity capture; it never reads source audio.
class SessionLog final
{
public:
    explicit SessionLog(SessionTelemetry& t) : telemetry(t) {}
    ~SessionLog();
    bool start(const juce::File& directory,const juce::String& instance);
    void stop();
    void drain();
    bool active() const { const std::lock_guard lock(mutex);return file>=0; }
    bool stopping() const { const std::lock_guard lock(mutex);return ending; }
    juce::String error() const { const std::lock_guard lock(mutex);return failure; }
    juce::String path() const { const std::lock_guard lock(mutex);return destination; }
private:
    bool write(juce::var);
    void fail(const juce::String&);
    SessionTelemetry& telemetry;
    mutable std::recursive_mutex mutex; // Writer/UI only; never called from render.
    std::atomic<bool> exit {false};
    std::thread worker;
    int file=-1;
    bool ending=false;
    std::uint64_t lostBefore=0,count=0,last=0,token=0;
    juce::String failure,destination;
};
}
