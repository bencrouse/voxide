#include <AudioToolbox/AudioToolbox.h>
#include <CoreFoundation/CoreFoundation.h>
#include <array>
#include <chrono>
#include <cmath>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>

namespace
{
void require(bool value,const char* text) { if (!value) throw std::runtime_error(text); }
void checked(OSStatus value,const char* text) { require(value==noErr,text); }
struct Input
{
    static float signal(int frame)
    { return (frame==0?.04f:0.f)+static_cast<float>(.01*std::sin(frame*.017)); }
    static OSStatus render(void*,AudioUnitRenderActionFlags*,const AudioTimeStamp* time,UInt32,UInt32 frames,AudioBufferList* buffers)
    {
        for (UInt32 c=0;c<buffers->mNumberBuffers;++c)
        {
            if (!buffers->mBuffers[c].mData) return kAudio_ParamError;
            auto* out=static_cast<float*>(buffers->mBuffers[c].mData);
            for (UInt32 i=0;i<frames;++i) out[i]=signal(static_cast<int>(time->mSampleTime)+static_cast<int>(i));
            buffers->mBuffers[c].mDataByteSize=frames*sizeof(float);
        }
        return noErr;
    }
};
void test(AudioComponent component,int rate)
{
    struct Instance
    {
        AudioUnit unit=nullptr;
        explicit Instance(AudioComponent c) { checked(AudioComponentInstanceNew(c,&unit),"Instantiate built AU"); }
        ~Instance() { if (unit) AudioComponentInstanceDispose(unit); }
    } instance(component);
    auto unit=instance.unit;
    AudioStreamBasicDescription mono {};
    mono.mSampleRate=rate;mono.mFormatID=kAudioFormatLinearPCM;
    mono.mFormatFlags=static_cast<AudioFormatFlags>(kAudioFormatFlagsNativeFloatPacked)
        |static_cast<AudioFormatFlags>(kAudioFormatFlagIsNonInterleaved);
    mono.mBytesPerPacket=mono.mBytesPerFrame=sizeof(float);mono.mFramesPerPacket=1;mono.mChannelsPerFrame=1;mono.mBitsPerChannel=32;
    checked(AudioUnitSetProperty(unit,kAudioUnitProperty_StreamFormat,kAudioUnitScope_Input,0,&mono,sizeof(mono)),"Input format");
    auto stereo=mono;stereo.mChannelsPerFrame=2;
    checked(AudioUnitSetProperty(unit,kAudioUnitProperty_StreamFormat,kAudioUnitScope_Output,0,&stereo,sizeof(stereo)),"Output format");
    UInt32 maximum=128;
    checked(AudioUnitSetProperty(unit,kAudioUnitProperty_MaximumFramesPerSlice,kAudioUnitScope_Global,0,&maximum,sizeof(maximum)),"Maximum frames");
    AURenderCallbackStruct input {Input::render,nullptr};
    checked(AudioUnitSetProperty(unit,kAudioUnitProperty_SetRenderCallback,kAudioUnitScope_Input,0,&input,sizeof(input)),"Synthetic input callback");
    UInt32 bytes=0;
    checked(AudioUnitGetPropertyInfo(unit,kAudioUnitProperty_ParameterList,kAudioUnitScope_Global,0,&bytes,nullptr),"Parameter list size");
    require(bytes==4*sizeof(AudioUnitParameterID),"Wrong evaluation parameter count");
    std::array<AudioUnitParameterID,4> parameters {};
    checked(AudioUnitGetProperty(unit,kAudioUnitProperty_ParameterList,kAudioUnitScope_Global,0,parameters.data(),&bytes),"Parameter list");
    bool disabled=false;
    for (auto id:parameters)
    {
        AudioUnitParameterInfo info {};bytes=sizeof(info);
        checked(AudioUnitGetProperty(unit,kAudioUnitProperty_ParameterInfo,kAudioUnitScope_Global,id,&info,&bytes),"Parameter info");
        if (std::strcmp(info.name,"Harmonies")==0)
        { checked(AudioUnitSetParameter(unit,id,kAudioUnitScope_Global,0,0,0),"Disable wet for impulse reference");disabled=true; }
        if ((info.flags&kAudioUnitParameterFlag_CFNameRelease) && info.cfNameString) CFRelease(info.cfNameString);
    }
    require(disabled,"Harmony parameter missing");
    checked(AudioUnitInitialize(unit),"Initialize built AU");
    double latency=0;bytes=sizeof(latency);
    checked(AudioUnitGetProperty(unit,kAudioUnitProperty_Latency,kAudioUnitScope_Global,0,&latency,&bytes),"AU latency property");
    require(std::abs(latency-.1)<1e-10,"AU latency is not 100 ms");
    std::array<float,128> left {},right {};
    struct Buffers { UInt32 count=2;AudioBuffer data[2]; } output;
    output.data[0]={1,128*sizeof(float),left.data()};output.data[1]={1,128*sizeof(float),right.data()};
    const auto epoch=std::chrono::steady_clock::now();
    for (int begin=0;begin<rate/4;begin+=128)
    {
        std::this_thread::sleep_until(epoch+std::chrono::nanoseconds(static_cast<std::uint64_t>(begin)*1000000000ull/static_cast<unsigned>(rate)));
        const int block=begin/128;
        if (block==12 || block==24 || block==48 || block==60)
        {
            UInt32 bypass=(block==12 || block==48)?1:0;
            checked(AudioUnitSetProperty(unit,kAudioUnitProperty_BypassEffect,kAudioUnitScope_Global,0,&bypass,sizeof(bypass)),"Toggle actual AU bypass");
        }
        AudioTimeStamp time {};time.mFlags=kAudioTimeStampSampleTimeValid;time.mSampleTime=begin;
        AudioUnitRenderActionFlags flags=0;
        checked(AudioUnitRender(unit,&flags,&time,0,128,reinterpret_cast<AudioBufferList*>(&output)),"Render built AU");
        for (int i=0;i<128;++i)
        {
            const int at=begin+i-rate/10;
            const float expected=at<0?0.f:Input::signal(at);
            require(left[i]==expected && right[i]==expected,"Built AU impulse/continuous lead/bypass alignment mismatch");
        }
    }
    checked(AudioUnitUninitialize(unit),"Uninitialize built AU");
}
}
int main(int argc,char** argv)
{
    try
    {
        require(argc==2,"Pass the uninstalled evaluation component path");
        const auto* path=reinterpret_cast<const UInt8*>(argv[1]);
        auto url=CFURLCreateFromFileSystemRepresentation(nullptr,path,static_cast<CFIndex>(std::strlen(argv[1])),true);
        require(url!=nullptr,"Bundle URL");auto bundle=CFBundleCreate(nullptr,url);CFRelease(url);
        require(bundle && CFBundleLoadExecutable(bundle),"Load exact built component");
        auto entries=static_cast<CFArrayRef>(CFBundleGetValueForInfoDictionaryKey(bundle,CFSTR("AudioComponents")));
        require(entries && CFArrayGetCount(entries)==1,"Evaluation component metadata missing");
        auto entry=static_cast<CFDictionaryRef>(CFArrayGetValueAtIndex(entries,0));
        auto name=static_cast<CFStringRef>(CFDictionaryGetValue(entry,CFSTR("factoryFunction")));
        require(name!=nullptr,"Factory metadata missing");
        auto factory=reinterpret_cast<AudioComponentFactoryFunction>(CFBundleGetFunctionPointerForName(bundle,name));
        require(factory!=nullptr,"Evaluation factory missing");
        const AudioComponentDescription description {'aufx','Vx6b','Vxid',0,0};
        // Process-local registration only: no installed AU, devices or Logic.
        auto component=AudioComponentRegister(&description,CFSTR("voxide Studio Eval smoke"),0x000100,factory);
        require(component!=nullptr,"Register built component in this process");
        test(component,44100);test(component,48000);CFRelease(bundle);
        std::cout<<"Built AU: both rates, four parameters, latency property, exact delayed impulse/continuous lead across bypass passed; no installation/device/Logic\n";
        return 0;
    }
    catch (const std::exception& e) { std::cerr<<e.what()<<'\n';return 1; }
}
