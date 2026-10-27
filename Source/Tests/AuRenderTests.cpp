#include <AudioToolbox/AudioToolbox.h>
#include <CoreFoundation/CoreFoundation.h>
#include <array>
#include <cmath>
#include <cstdlib>
#include <cstdint>
#include <iostream>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <algorithm>

namespace
{
void require(bool condition, const std::string& message)
{
    if (!condition) throw std::runtime_error(message);
}

void checked(OSStatus status, const char* operation)
{
    require(status == noErr, std::string(operation) + ": " + std::to_string(status));
}

struct Input
{
    float value;
    int calls = 0;

    static float sample(float base, std::uint64_t index)
    {
        return base == 0.0f ? 0.0f : base + static_cast<float>(static_cast<int>(index % 31) - 15) / 1024.0f;
    }

    static OSStatus render(void* context, AudioUnitRenderActionFlags*, const AudioTimeStamp* time,
                           UInt32, UInt32 frames, AudioBufferList* buffers)
    {
        auto& input = *static_cast<Input*>(context);
        ++input.calls;
        for (UInt32 channel = 0; channel < buffers->mNumberBuffers; ++channel)
        {
            auto& buffer = buffers->mBuffers[channel];
            if (buffer.mData == nullptr) return kAudio_ParamError;
            auto* samples = static_cast<float*>(buffer.mData);
            for (UInt32 i = 0; i < frames; ++i)
                samples[i] = sample(input.value, static_cast<std::uint64_t>(time->mSampleTime) + i);
            buffer.mDataByteSize = frames * static_cast<UInt32>(sizeof(float));
        }
        return noErr;
    }
};

AudioUnitParameterID sourceId(AudioUnit);
void disableVoices(AudioUnit unit)
{
    UInt32 bytes=0;checked(AudioUnitGetPropertyInfo(unit,kAudioUnitProperty_ParameterList,kAudioUnitScope_Global,0,&bytes,nullptr),"parameter size");
    std::vector<AudioUnitParameterID> ids(bytes/sizeof(AudioUnitParameterID));
    checked(AudioUnitGetProperty(unit,kAudioUnitProperty_ParameterList,kAudioUnitScope_Global,0,ids.data(),&bytes),"parameters");
    int disabled=0;
    for (auto id:ids)
    {
        AudioUnitParameterInfo info {};bytes=sizeof(info);
        checked(AudioUnitGetProperty(unit,kAudioUnitProperty_ParameterInfo,kAudioUnitScope_Global,id,&info,&bytes),"parameter info");
        if (std::string(info.name).find(" enabled")!=std::string::npos)
        { checked(AudioUnitSetParameter(unit,id,kAudioUnitScope_Global,0,0,0),"disable harmony");++disabled; }
        if ((info.flags&kAudioUnitParameterFlag_CFNameRelease) && info.cfNameString) CFRelease(info.cfNameString);
    }
    require(disabled==3,"Three voice enables missing");
}

struct Transport
{
    bool playing = true;
    double position = 0;
    int calls = 0;
    static OSStatus get(void* context, Boolean* playing, Boolean* changed, Float64* position,
                        Boolean* cycling, Float64* cycleStart, Float64* cycleEnd)
    {
        auto& state = *static_cast<Transport*>(context);
        ++state.calls;
        if (playing) *playing = state.playing;
        if (changed) *changed = true;
        if (position) *position = state.position;
        if (cycling) *cycling = false;
        if (cycleStart) *cycleStart = 0;
        if (cycleEnd) *cycleEnd = 0;
        return noErr;
    }
};

struct Instance
{
    AudioUnit unit = nullptr;
    explicit Instance(AudioComponent component) { checked(AudioComponentInstanceNew(component, &unit), "instantiate"); }
    ~Instance() { if (unit != nullptr) AudioComponentInstanceDispose(unit); }
};

int renderCase(AudioComponent component, bool sideConnected, bool sideSelected,
                bool bypassed, float sideValue, double rate, UInt32 frames)
{
    Instance instance(component);
    auto unit = instance.unit;
    AudioStreamBasicDescription inputFormat {};
    inputFormat.mSampleRate = rate;
    inputFormat.mFormatID = kAudioFormatLinearPCM;
    inputFormat.mFormatFlags = static_cast<AudioFormatFlags>(kAudioFormatFlagsNativeFloatPacked)
                            | static_cast<AudioFormatFlags>(kAudioFormatFlagIsNonInterleaved);
    inputFormat.mBytesPerPacket = inputFormat.mBytesPerFrame = sizeof(float);
    inputFormat.mFramesPerPacket = 1;
    inputFormat.mChannelsPerFrame = 1;
    inputFormat.mBitsPerChannel = 32;
    checked(AudioUnitSetProperty(unit, kAudioUnitProperty_StreamFormat, kAudioUnitScope_Input,
                                 0, &inputFormat, sizeof(inputFormat)), "main format");
    checked(AudioUnitSetProperty(unit, kAudioUnitProperty_StreamFormat, kAudioUnitScope_Input,
                                 1, &inputFormat, sizeof(inputFormat)), "sidechain format");
    auto outputFormat = inputFormat;
    outputFormat.mChannelsPerFrame = 2;
    checked(AudioUnitSetProperty(unit, kAudioUnitProperty_StreamFormat, kAudioUnitScope_Output,
                                 0, &outputFormat, sizeof(outputFormat)), "output format");
    Input main { 0.25f }, side { sideValue };
    Transport transport;
    HostCallbackInfo callbacks {};
    callbacks.hostUserData = &transport;
    callbacks.transportStateProc = Transport::get;
    checked(AudioUnitSetProperty(unit, kAudioUnitProperty_HostCallbacks, kAudioUnitScope_Global,
                                 0, &callbacks, sizeof(callbacks)), "transport callback");
    AURenderCallbackStruct mainCallback { Input::render, &main };
    checked(AudioUnitSetProperty(unit, kAudioUnitProperty_SetRenderCallback, kAudioUnitScope_Input,
                                 0, &mainCallback, sizeof(mainCallback)), "connect main");
    if (sideConnected)
    {
        AURenderCallbackStruct sideCallback { Input::render, &side };
        checked(AudioUnitSetProperty(unit, kAudioUnitProperty_SetRenderCallback, kAudioUnitScope_Input,
                                     1, &sideCallback, sizeof(sideCallback)), "connect sidechain");
    }
    if (sideSelected)
    {
        checked(AudioUnitSetParameter(unit, sourceId(unit), kAudioUnitScope_Global, 0, 1.0f, 0), "select sidechain");
    }
    const UInt32 bypass = bypassed ? 1u : 0u;
    checked(AudioUnitSetProperty(unit, kAudioUnitProperty_BypassEffect, kAudioUnitScope_Global,
                                 0, &bypass, sizeof(bypass)), "bypass");
    disableVoices(unit);checked(AudioUnitInitialize(unit), "initialize");
    double latencySeconds=0;UInt32 latencyBytes=sizeof(latencySeconds);
    checked(AudioUnitGetProperty(unit,kAudioUnitProperty_Latency,kAudioUnitScope_Global,0,&latencySeconds,&latencyBytes),"latency");
    require(std::abs(latencySeconds-.1)<1e-10,"Product AU latency is not 100 ms");
    std::array<float, 137> left {}, right {};
    auto* output = static_cast<AudioBufferList*>(std::calloc(1, sizeof(AudioBufferList) + sizeof(AudioBuffer)));
    require(output != nullptr, "output allocation");
    output->mNumberBuffers = 2;
    output->mBuffers[0] = { 1, frames * static_cast<UInt32>(sizeof(float)), left.data() };
    output->mBuffers[1] = { 1, frames * static_cast<UInt32>(sizeof(float)), right.data() };
    AudioTimeStamp timestamp {};
    timestamp.mFlags = kAudioTimeStampSampleTimeValid;
    AudioUnitRenderActionFlags flags = 0;
    const int latency=static_cast<int>(rate/10),warm=(latency+static_cast<int>(frames)-1)/static_cast<int>(frames),blocks=warm+8;
    std::uint64_t renderClock=0;
    for (int pass = 0; pass < 4; ++pass)
    {
        // Monotonic render clock, independently stopped/backward/forward project time.
        transport.playing = pass != 1;
        if (pass == 3) checked(AudioUnitReset(unit, kAudioUnitScope_Global, 0), "reset");
        for (int block=0;block<blocks;++block)
        {
        timestamp.mSampleTime=static_cast<double>(renderClock);
        transport.position=pass==1?static_cast<double>(frames):static_cast<double>((pass==2?20000:(pass+1)*frames)+block*frames);
        if (!bypassed && pass==0 && (block==3 || block==6 || block==warm+2 || block==warm+4))
        {
            const UInt32 toggle=(block==3 || block==warm+2)?1u:0u;
            checked(AudioUnitSetProperty(unit,kAudioUnitProperty_BypassEffect,kAudioUnitScope_Global,0,&toggle,sizeof(toggle)),"continuous bypass transition");
        }
        checked(MusicDeviceMIDIEvent(unit, 0x90, 60, 100, 7), "MIDI note-on");
        checked(MusicDeviceMIDIEvent(unit, 0x80, 60, 0, 23), "MIDI note-off");
        checked(AudioUnitRender(unit, &flags, &timestamp, 0, frames, output), "render");
        const float base = sideSelected ? (sideConnected ? sideValue : 0.0f) : main.value;
        for (UInt32 i = 0; i < frames; ++i)
        {
            const auto expected=block*static_cast<int>(frames)+static_cast<int>(i)<latency?0.f:Input::sample(base,renderClock+i-static_cast<unsigned>(latency));
            require(std::abs(left[i] - expected) < 1.0e-7f && std::abs(right[i] - expected) < 1.0e-7f,
                    "AU routing/transport sample mismatch in pass " + std::to_string(pass));
        }
        renderClock+=frames;
        }
    }
    std::free(output);
    require(transport.calls >= 4, "AU did not request host transport context");
    require(main.calls > 0, "Main render callback was not exercised");
    if (sideConnected) require(side.calls > 0, "Sidechain render callback was not exercised");
    checked(AudioUnitUninitialize(unit), "uninitialize");
    return blocks*4;
}

AudioUnitParameterID sourceId(AudioUnit unit)
{
    UInt32 size = 0;
    checked(AudioUnitGetPropertyInfo(unit, kAudioUnitProperty_ParameterList, kAudioUnitScope_Global,
                                     0, &size, nullptr), "parameter list size");
    require(size == 31 * sizeof(AudioUnitParameterID), "Unexpected studio parameter count");
    std::vector<AudioUnitParameterID> ids(size / sizeof(AudioUnitParameterID));
    checked(AudioUnitGetProperty(unit, kAudioUnitProperty_ParameterList, kAudioUnitScope_Global,
                                 0, ids.data(), &size), "source parameter");
    require(ids.front() == 449045605u, "Legacy source automation index moved");
    std::sort(ids.begin(), ids.end());
    require(std::adjacent_find(ids.begin(), ids.end()) == ids.end(), "Duplicate AU parameter ID");
    require(std::find(ids.begin(), ids.end(), 449045605u) != ids.end(), "Source parameter ID changed");
    return 449045605u;
}

void stateRoundTrip(AudioComponent component)
{
    Instance first(component);
    checked(AudioUnitSetParameter(first.unit, sourceId(first.unit), kAudioUnitScope_Global, 0, 1.0f, 0), "source before save");
    CFPropertyListRef state = nullptr;
    UInt32 size = sizeof(state);
    checked(AudioUnitGetProperty(first.unit, kAudioUnitProperty_ClassInfo, kAudioUnitScope_Global,
                                 0, &state, &size), "save AU state");
    require(state != nullptr, "AU state missing");
    Instance restored(component);
    checked(AudioUnitSetProperty(restored.unit, kAudioUnitProperty_ClassInfo, kAudioUnitScope_Global,
                                 0, &state, sizeof(state)), "restore fresh AU state");
    CFRelease(state);
    checked(AudioUnitInitialize(restored.unit), "initialize restored AU");
    checked(AudioUnitReset(restored.unit, kAudioUnitScope_Global, 0), "reset restored AU");
    AudioUnitParameterValue value = 0;
    checked(AudioUnitGetParameter(restored.unit, sourceId(restored.unit), kAudioUnitScope_Global, 0, &value), "read restored source");
    require(std::abs(value - 1.0f) < 1.0e-7f, "Source did not survive AU state/new instance/reset");
    checked(AudioUnitUninitialize(restored.unit), "uninitialize restored AU");
}
}

int main(int argc, char** argv)
{
    std::string reportPath;
    try
    {
        require(argc == 2 || (argc == 4 && std::string(argv[2]) == "--report"),
                "Pass the built AU component directory [--report file.json]");
        if (argc == 4)
        {
            reportPath = argv[3];
            std::ofstream initial(reportPath);
            require(initial.good(), "Cannot initialize AU report");
            initial << "{\"schema\":\"voxide.native-au.v2\",\"status\":\"running\"}\n";
        }
        const std::string path(argv[1]);
        auto url = CFURLCreateFromFileSystemRepresentation(nullptr,
            reinterpret_cast<const UInt8*>(path.data()), static_cast<CFIndex>(path.size()), true);
        require(url != nullptr, "bundle URL");
        auto bundle = CFBundleCreate(nullptr, url);
        CFRelease(url);
        require(bundle != nullptr && CFBundleLoadExecutable(bundle), "load built component");
        auto factory = reinterpret_cast<AudioComponentFactoryFunction>(
            CFBundleGetFunctionPointerForName(bundle, CFSTR("voxideAUFactory")));
        require(factory != nullptr, "AU factory symbol");
        const AudioComponentDescription description { 'aumf', 'Vx00', 'Vxid', 0, 0 };
        // Process-local registration loads this exact build. No installed component,
        // registry lookup, audio device, microphone, or Logic is used.
        const auto descriptions = static_cast<CFArrayRef>(CFBundleGetValueForInfoDictionaryKey(bundle, CFSTR("AudioComponents")));
        require(descriptions != nullptr && CFArrayGetCount(descriptions) == 1, "Component metadata missing");
        const auto item = static_cast<CFDictionaryRef>(CFArrayGetValueAtIndex(descriptions, 0));
        const auto versionValue = static_cast<CFNumberRef>(CFDictionaryGetValue(item, CFSTR("version")));
        UInt32 version = 0;
        require(versionValue != nullptr && CFNumberGetValue(versionValue, kCFNumberSInt32Type, &version), "Component version missing");
        auto component = AudioComponentRegister(&description, CFSTR("voxide render test"), version, factory);
        require(component != nullptr, "process-local AU registration");
        int cases = 0,renderedBlocks=0;
        for (double rate : { 44100.0, 48000.0 })
            for (UInt32 frames : { 32u, 64u, 137u })
                for (bool sideConnected : { false, true })
                    for (bool sideSelected : { false, true })
                        for (bool bypassed : { false, true })
                            for (float side : { -0.375f, 0.0f })
                            {
                                renderedBlocks+=renderCase(component, sideConnected, sideSelected, bypassed, side, rate, frames);
                                ++cases;
                            }
        stateRoundTrip(component);
        if (argc == 4)
        {
            std::ofstream report(argv[3]);
            require(report.good(), "Cannot open AU report output");
            report << "{\"schema\":\"voxide.native-au.v2\",\"status\":\"pass\",\"component_version\":" << version
                   << ",\"routing_cases\":" << cases
                   << ",\"rendered_blocks\":" << renderedBlocks << ",\"midi_api_events\":" << renderedBlocks*2
                   << ",\"latency_seconds\":0.1,\"continuous_bypass_reference\":true"
                   << ",\"state_round_trip\":true,\"transport_callbacks_observed\":true,"
                   << "\"midi_offset_delivery_observed\":false,"
                    << "\"scope\":\"Built AU, harmonies disabled, aligned selected original without devices or Logic; MIDI offsets asserted separately in production processor tests\"}\n";
            report.flush();
            require(report.good(), "AU report write failed");
        }
        CFRelease(bundle);
        std::cout << "Device-free built AU tests passed: " << cases << " routes, 100 ms aligned lead, bypass continuity, transport/reset and fresh-instance state\n";
        return EXIT_SUCCESS;
    }
    catch (const std::exception& error)
    {
        if (!reportPath.empty())
        {
            std::ofstream failed(reportPath);
            failed << "{\"schema\":\"voxide.native-au.v2\",\"status\":\"fail\"}\n";
        }
        std::cerr << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
