#include <AudioToolbox/AudioToolbox.h>
#include <CoreFoundation/CoreFoundation.h>
#include <array>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

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

    static OSStatus render(void* context, AudioUnitRenderActionFlags*, const AudioTimeStamp*,
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
                samples[i] = input.value;
            buffer.mDataByteSize = frames * static_cast<UInt32>(sizeof(float));
        }
        return noErr;
    }
};

struct Instance
{
    AudioUnit unit = nullptr;
    explicit Instance(AudioComponent component) { checked(AudioComponentInstanceNew(component, &unit), "instantiate"); }
    ~Instance() { if (unit != nullptr) AudioComponentInstanceDispose(unit); }
};

void renderCase(AudioComponent component, bool sideConnected, bool sideSelected,
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
        UInt32 bytes = 0;
        checked(AudioUnitGetPropertyInfo(unit, kAudioUnitProperty_ParameterList, kAudioUnitScope_Global,
                                         0, &bytes, nullptr), "parameter list size");
        require(bytes == sizeof(AudioUnitParameterID), "Expected the single vocal-source parameter");
        AudioUnitParameterID sourceParameter = 0;
        checked(AudioUnitGetProperty(unit, kAudioUnitProperty_ParameterList, kAudioUnitScope_Global,
                                     0, &sourceParameter, &bytes), "parameter list");
        checked(AudioUnitSetParameter(unit, sourceParameter, kAudioUnitScope_Global, 0, 1.0f, 0), "select sidechain");
    }
    const UInt32 bypass = bypassed ? 1u : 0u;
    checked(AudioUnitSetProperty(unit, kAudioUnitProperty_BypassEffect, kAudioUnitScope_Global,
                                 0, &bypass, sizeof(bypass)), "bypass");
    checked(AudioUnitInitialize(unit), "initialize");
    std::array<float, 137> left {}, right {};
    auto* output = static_cast<AudioBufferList*>(std::calloc(1, sizeof(AudioBufferList) + sizeof(AudioBuffer)));
    require(output != nullptr, "output allocation");
    output->mNumberBuffers = 2;
    output->mBuffers[0] = { 1, frames * static_cast<UInt32>(sizeof(float)), left.data() };
    output->mBuffers[1] = { 1, frames * static_cast<UInt32>(sizeof(float)), right.data() };
    AudioTimeStamp timestamp {};
    timestamp.mFlags = kAudioTimeStampSampleTimeValid;
    AudioUnitRenderActionFlags flags = 0;
    const auto status = AudioUnitRender(unit, &flags, &timestamp, 0, frames, output);
    std::free(output);
    checked(status, "render");
    const float expected = sideSelected ? (sideConnected ? sideValue : 0.0f) : main.value;
    for (UInt32 i = 0; i < frames; ++i)
        require(std::abs(left[i] - expected) < 1.0e-7f && std::abs(right[i] - expected) < 1.0e-7f,
                "AU samples disagree: side connected=" + std::to_string(sideConnected)
                    + ", side selected=" + std::to_string(sideSelected)
                    + ", bypass=" + std::to_string(bypassed)
                    + ", expected=" + std::to_string(expected)
                    + ", left=" + std::to_string(left[i]) + ", right=" + std::to_string(right[i]));
    require(main.calls > 0, "Main render callback was not exercised");
    if (sideConnected) require(side.calls > 0, "Sidechain render callback was not exercised");
    checked(AudioUnitUninitialize(unit), "uninitialize");
}
}

int main(int argc, char** argv)
{
    try
    {
        require(argc == 2, "Pass the built AU component directory");
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
        auto component = AudioComponentRegister(&description, CFSTR("voxide render test"), 1, factory);
        require(component != nullptr, "process-local AU registration");
        int cases = 0;
        for (double rate : { 44100.0, 48000.0 })
            for (UInt32 frames : { 32u, 64u, 137u })
                for (bool sideConnected : { false, true })
                    for (bool sideSelected : { false, true })
                        for (bool bypassed : { false, true })
                            for (float side : { -0.375f, 0.0f })
                            {
                                renderCase(component, sideConnected, sideSelected, bypassed, side, rate, frames);
                                ++cases;
                            }
        CFRelease(bundle);
        std::cout << "Device-free built AU sample tests passed: " << cases << " cases\n";
        return EXIT_SUCCESS;
    }
    catch (const std::exception& error)
    {
        std::cerr << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
