#include <CoreAudio/CoreAudio.h>
#include <CoreMIDI/CoreMIDI.h>
#include <CoreFoundation/CoreFoundation.h>
#include <sys/sysctl.h>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace
{
std::string quoted(const std::string& text)
{
    std::ostringstream out;
    out << '"';
    for (unsigned char c : text)
    {
        if (c == '"' || c == '\\') out << '\\' << c;
        else if (c >= 32) out << c;
        else out << ' ';
    }
    out << '"';
    return out.str();
}

std::string stringValue(CFStringRef value)
{
    if (value == nullptr) return {};
    char buffer[2048] {};
    CFStringGetCString(value, buffer, sizeof(buffer), kCFStringEncodingUTF8);
    return buffer;
}

std::string systemString(const char* key)
{
    char buffer[256] {};
    std::size_t size = sizeof(buffer);
    if (sysctlbyname(key, buffer, &size, nullptr, 0) != 0) return "unavailable";
    return buffer;
}

template<class T>
T property(AudioObjectID object, AudioObjectPropertySelector selector,
           AudioObjectPropertyScope scope = kAudioObjectPropertyScopeGlobal)
{
    AudioObjectPropertyAddress address { selector, scope, kAudioObjectPropertyElementMain };
    T result {};
    UInt32 size = sizeof(result);
    AudioObjectGetPropertyData(object, &address, 0, nullptr, &size, &result);
    return result;
}

std::string name(AudioObjectID object)
{
    auto value = property<CFStringRef>(object, kAudioObjectPropertyName);
    const auto result = stringValue(value);
    if (value != nullptr) CFRelease(value);
    return result;
}

unsigned channels(AudioObjectID object, AudioObjectPropertyScope scope)
{
    AudioObjectPropertyAddress address { kAudioDevicePropertyStreamConfiguration, scope, kAudioObjectPropertyElementMain };
    UInt32 size = 0;
    if (AudioObjectGetPropertyDataSize(object, &address, 0, nullptr, &size) != noErr || size == 0) return 0;
    std::vector<unsigned char> storage(size);
    if (AudioObjectGetPropertyData(object, &address, 0, nullptr, &size, storage.data()) != noErr) return 0;
    const auto* buffers = reinterpret_cast<const AudioBufferList*>(storage.data());
    unsigned count = 0;
    for (UInt32 i = 0; i < buffers->mNumberBuffers; ++i) count += buffers->mBuffers[i].mNumberChannels;
    return count;
}
}

int main()
{
    // Read-only property queries. No AudioDeviceStart, AUHAL, microphone capture,
    // MIDI endpoint creation, device changes, hostname, serial, or device UID.
    std::uint64_t memory = 0;
    std::size_t memorySize = sizeof(memory);
    sysctlbyname("hw.memsize", &memory, &memorySize, nullptr, 0);
    const auto input = property<AudioDeviceID>(kAudioObjectSystemObject, kAudioHardwarePropertyDefaultInputDevice);
    const auto output = property<AudioDeviceID>(kAudioObjectSystemObject, kAudioHardwarePropertyDefaultOutputDevice);
    std::cout << "{\"schema\":\"voxide.environment.v1\",\"cpu\":" << quoted(systemString("machdep.cpu.brand_string"))
              << ",\"model\":" << quoted(systemString("hw.model")) << ",\"memory_bytes\":" << memory
              << ",\"coreaudio_default_input\":" << input << ",\"coreaudio_default_output\":" << output
              << ",\"note\":\"CoreAudio reported defaults, not Logic configuration or measured latency\",\"devices\":[";
    AudioObjectPropertyAddress address { kAudioHardwarePropertyDevices, kAudioObjectPropertyScopeGlobal, kAudioObjectPropertyElementMain };
    UInt32 size = 0;
    AudioObjectGetPropertyDataSize(kAudioObjectSystemObject, &address, 0, nullptr, &size);
    std::vector<AudioDeviceID> devices(size / sizeof(AudioDeviceID));
    if (size != 0) AudioObjectGetPropertyData(kAudioObjectSystemObject, &address, 0, nullptr, &size, devices.data());
    bool first = true;
    for (auto device : devices)
    {
        if (!first) std::cout << ',';
        first = false;
        std::cout << "{\"id\":" << device << ",\"name\":" << quoted(name(device))
                  << ",\"input_channels\":" << channels(device, kAudioObjectPropertyScopeInput)
                  << ",\"output_channels\":" << channels(device, kAudioObjectPropertyScopeOutput)
                  << ",\"reported_sample_rate\":" << property<Float64>(device, kAudioDevicePropertyNominalSampleRate)
                  << ",\"reported_buffer_frames\":" << property<UInt32>(device, kAudioDevicePropertyBufferFrameSize) << '}';
    }
    std::cout << "],\"midi_sources\":[";
    for (ItemCount i = 0; i < MIDIGetNumberOfSources(); ++i)
    {
        if (i != 0) std::cout << ',';
        CFStringRef display = nullptr;
        MIDIObjectGetStringProperty(MIDIGetSource(i), kMIDIPropertyDisplayName, &display);
        std::cout << quoted(stringValue(display));
        if (display != nullptr) CFRelease(display);
    }
    std::cout << "]}\n";
}
