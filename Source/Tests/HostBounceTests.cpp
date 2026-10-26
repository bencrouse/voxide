#include "PluginProcessor.h"
#include <AudioToolbox/AudioToolbox.h>
#include <CoreFoundation/CoreFoundation.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <unistd.h>
#include <fcntl.h>
#include <cerrno>

namespace
{
void require(bool value,const char* text) { if (!value) throw std::runtime_error(text); }
void checked(OSStatus value,const char* text) { require(value==noErr,text); }
float signal(int at,int rate)
{
    if (at>=rate || (at>=rate/3 && at<rate/3+rate/20)) return 0;
    return at==0?.01f:static_cast<float>(.02*std::sin(6.283185307179586*(at<rate/2?220:330)*at/rate));
}
struct Input
{
    int rate;bool selected;
    static OSStatus render(void* context,AudioUnitRenderActionFlags*,const AudioTimeStamp* time,UInt32,UInt32 frames,AudioBufferList* buffers)
    {
        const auto& input=*static_cast<Input*>(context);
        for (UInt32 channel=0;channel<buffers->mNumberBuffers;++channel)
        {
            auto& buffer=buffers->mBuffers[channel];if (!buffer.mData) return kAudio_ParamError;
            auto* audio=static_cast<float*>(buffer.mData);
            for (UInt32 i=0;i<frames;++i) audio[i]=input.selected?signal(static_cast<int>(time->mSampleTime)+static_cast<int>(i),input.rate):.07f;
            buffer.mDataByteSize=frames*sizeof(float);
        }
        return noErr;
    }
};
struct Bundle
{
    CFBundleRef bundle=nullptr;
    AudioComponent component=nullptr;
    explicit Bundle(const std::string& path)
    {
        auto url=CFURLCreateFromFileSystemRepresentation(nullptr,reinterpret_cast<const UInt8*>(path.data()),static_cast<CFIndex>(path.size()),true);
        require(url,"Component URL");bundle=CFBundleCreate(nullptr,url);CFRelease(url);
        require(bundle,"Create component bundle");
        require(CFBundleGetIdentifier(bundle) && CFEqual(CFBundleGetIdentifier(bundle),CFSTR("com.voxide.audio.voxide")),"Wrong product bundle");
        auto entries=static_cast<CFArrayRef>(CFBundleGetValueForInfoDictionaryKey(bundle,CFSTR("AudioComponents")));
        require(entries && CFGetTypeID(entries)==CFArrayGetTypeID() && CFArrayGetCount(entries)==1,"Wrong component metadata");
        auto entry=static_cast<CFDictionaryRef>(CFArrayGetValueAtIndex(entries,0));
        require(CFGetTypeID(entry)==CFDictionaryGetTypeID(),"Invalid AU entry");
        auto matches=[&](CFStringRef key,CFStringRef expected)
        { const auto value=CFDictionaryGetValue(entry,key);return value && CFGetTypeID(value)==CFStringGetTypeID() && CFEqual(value,expected); };
        require(matches(CFSTR("type"),CFSTR("aumf")) && matches(CFSTR("subtype"),CFSTR("Vx00"))
            && matches(CFSTR("manufacturer"),CFSTR("Vxid")),"Wrong AU identity");
        auto factoryName=static_cast<CFStringRef>(CFDictionaryGetValue(entry,CFSTR("factoryFunction")));
        require(factoryName && CFGetTypeID(factoryName)==CFStringGetTypeID(),"Missing factory metadata");
        require(CFBundleLoadExecutable(bundle),"Load exact component");
        auto factory=reinterpret_cast<AudioComponentFactoryFunction>(CFBundleGetFunctionPointerForName(bundle,factoryName));
        require(factory,"Product factory missing");
        const AudioComponentDescription description {'aumf','Vx00','Vxid',0,0};UInt32 version=0;
        auto versionValue=CFDictionaryGetValue(entry,CFSTR("version"));
        require(versionValue && CFGetTypeID(versionValue)==CFNumberGetTypeID()
            && CFNumberGetValue(static_cast<CFNumberRef>(versionValue),kCFNumberSInt32Type,&version),"Missing component version");
        // Process-local only, even when explicitly testing an installed bundle.
        component=AudioComponentRegister(&description,CFSTR("voxide PR08 exact-bundle integration"),version,factory);
        require(component,"Register exact bundle in process");
    }
    ~Bundle() { if (bundle) CFRelease(bundle); }
};
struct Unit
{
    AudioUnit unit=nullptr;
    struct Parameter { AudioUnitParameterID id;float minimum,maximum; };
    std::map<std::string,Parameter> parameters;
    voxide::Processor parameterContract;
    std::atomic<unsigned> latencyNotifications {0};
    explicit Unit(AudioComponent component)
    {
        checked(AudioComponentInstanceNew(component,&unit),"Instantiate exact AU");UInt32 bytes=0;
        checked(AudioUnitGetPropertyInfo(unit,kAudioUnitProperty_ParameterList,kAudioUnitScope_Global,0,&bytes,nullptr),"Parameter list size");
        require(bytes==30*sizeof(AudioUnitParameterID),"Host parameter compatibility changed");std::vector<AudioUnitParameterID> ids(30);
        checked(AudioUnitGetProperty(unit,kAudioUnitProperty_ParameterList,kAudioUnitScope_Global,0,ids.data(),&bytes),"Parameters");
        require(ids.front()==449045605u,"Legacy source AU ID changed");
        for (auto id:ids)
        {
            AudioUnitParameterInfo info {};bytes=sizeof(info);
            checked(AudioUnitGetProperty(unit,kAudioUnitProperty_ParameterInfo,kAudioUnitScope_Global,id,&info,&bytes),"Parameter info");
            require(parameters.emplace(info.name,Parameter{id,info.minValue,info.maxValue}).second,"Duplicate parameter label");
            if ((info.flags&kAudioUnitParameterFlag_CFNameRelease) && info.cfNameString) CFRelease(info.cfNameString);
        }
        checked(AudioUnitAddPropertyListener(unit,kAudioUnitProperty_Latency,latencyChanged,this),"Latency listener");
    }
    ~Unit()
    {
        if (unit) { AudioUnitRemovePropertyListenerWithUserData(unit,kAudioUnitProperty_Latency,latencyChanged,this);AudioComponentInstanceDispose(unit); }
    }
    static void latencyChanged(void* context,AudioUnit,AudioUnitPropertyID,AudioUnitScope,AudioUnitElement)
    { ++static_cast<Unit*>(context)->latencyNotifications; }
    float rawValue(const char* name,float value) const
    {
        // Pinned JUCE AU exposes [0, steps-1] for discrete controls and [0,1]
        // for continuous controls, not the processor's physical degree/dB units.
        const auto au=parameters.at(name);
        for (auto* base:parameterContract.getParameters())
            if (auto* ranged=dynamic_cast<juce::RangedAudioParameter*>(base);ranged && ranged->getName(1024)==name)
            {
                return au.minimum+(au.maximum-au.minimum)*ranged->convertTo0to1(value);
            }
        throw std::runtime_error("Missing physical parameter mapping");
    }
    float get(const char* name) const
    {
        AudioUnitParameterValue observed=0;
        checked(AudioUnitGetParameter(unit,parameters.at(name).id,kAudioUnitScope_Global,0,&observed),"Read AU parameter");return observed;
    }
    void set(const char* name,float value)
    {
        const auto raw=rawValue(name,value);
        checked(AudioUnitSetParameter(unit,parameters.at(name).id,kAudioUnitScope_Global,0,raw,0),"Set AU parameter");
        require(juce::exactlyEqual(raw,get(name)),"AU automation readback mismatch");
    }
    std::map<std::string,float> initialValues(bool side,bool dry) const
    {
        std::map<std::string,float> values;
        for (auto* base:parameterContract.getParameters())
            if (auto* ranged=dynamic_cast<juce::RangedAudioParameter*>(base))
                values.emplace(ranged->getName(1024).toStdString(),ranged->convertFrom0to1(ranged->getDefaultValue()));
        require(values.size()==30,"Incomplete initial parameter contract");
        values.at("Vocal source")=side?1.f:0.f;values.at("Scale root")=5;values.at("Scale (12-TET)")=1;
        values.at("Voice 1 degree steps")=0;values.at("Voice 2 level")=-6;
        if (dry) for (const char* name:{"Voice 1 enabled","Voice 2 enabled","Voice 3 enabled"}) values.at(name)=0;
        return values;
    }
    void initial(bool side,bool dry)
    {
        for (const auto& [name,value]:initialValues(side,dry)) set(name.c_str(),value);
    }
    bool matchesInitial(bool side,bool dry) const
    {
        for (const auto& [name,value]:initialValues(side,dry))
            if (!juce::exactlyEqual(get(name.c_str()),rawValue(name.c_str(),value))) return false;
        return true;
    }
    CFPropertyListRef state()
    {
        CFPropertyListRef result=nullptr;UInt32 size=sizeof(result);
        checked(AudioUnitGetProperty(unit,kAudioUnitProperty_ClassInfo,kAudioUnitScope_Global,0,&result,&size),"Save AU state");require(result,"Missing AU state");return result;
    }
    void restore(CFPropertyListRef state)
    { checked(AudioUnitSetProperty(unit,kAudioUnitProperty_ClassInfo,kAudioUnitScope_Global,0,&state,sizeof(state)),"Restore AU state"); }
    void initialize(int rate,bool offline,Input& main,Input& side)
    {
        AudioStreamBasicDescription format {};format.mSampleRate=rate;format.mFormatID=kAudioFormatLinearPCM;
        format.mFormatFlags=static_cast<AudioFormatFlags>(kAudioFormatFlagsNativeFloatPacked)|static_cast<AudioFormatFlags>(kAudioFormatFlagIsNonInterleaved);
        format.mBytesPerPacket=format.mBytesPerFrame=sizeof(float);format.mFramesPerPacket=1;format.mChannelsPerFrame=1;format.mBitsPerChannel=32;
        for (UInt32 bus:{0u,1u}) checked(AudioUnitSetProperty(unit,kAudioUnitProperty_StreamFormat,kAudioUnitScope_Input,bus,&format,sizeof(format)),"Input format");
        format.mChannelsPerFrame=2;checked(AudioUnitSetProperty(unit,kAudioUnitProperty_StreamFormat,kAudioUnitScope_Output,0,&format,sizeof(format)),"Output format");
        UInt32 maximum=1024;checked(AudioUnitSetProperty(unit,kAudioUnitProperty_MaximumFramesPerSlice,kAudioUnitScope_Global,0,&maximum,sizeof(maximum)),"Maximum frames");
        AURenderCallbackStruct a {Input::render,&main},b {Input::render,&side};
        checked(AudioUnitSetProperty(unit,kAudioUnitProperty_SetRenderCallback,kAudioUnitScope_Input,0,&a,sizeof(a)),"Main input callback");
        checked(AudioUnitSetProperty(unit,kAudioUnitProperty_SetRenderCallback,kAudioUnitScope_Input,1,&b,sizeof(b)),"Side input callback");
        UInt32 nonRealtime=offline?1u:0u;checked(AudioUnitSetProperty(unit,kAudioUnitProperty_OfflineRender,kAudioUnitScope_Global,0,&nonRealtime,sizeof(nonRealtime)),"AU offline property");
        checked(AudioUnitInitialize(unit),"Initialize AU");
        double latency=0;UInt32 bytes=sizeof(latency);checked(AudioUnitGetProperty(unit,kAudioUnitProperty_Latency,kAudioUnitScope_Global,0,&latency,&bytes),"AU latency");
        require(std::abs(latency-.1)<1e-10,"Reported AU latency is not 100 ms");
        for (int i=0;i<10 && !latencyNotifications.load();++i) CFRunLoopRunInMode(kCFRunLoopDefaultMode,.01,false);
        require(latencyNotifications.load()>0,"AU did not notify its initial latency");
    }
};
const std::array<int,5> events {4096,8192,12288,16384,18432};
void set(voxide::Processor& p,const char* id,float value)
{
    for (auto* base:p.getParameters()) if (auto* parameter=dynamic_cast<juce::RangedAudioParameter*>(base);parameter && parameter->paramID==id)
    { parameter->setValueNotifyingHost(parameter->convertTo0to1(value));return; }
    throw std::runtime_error("Reference parameter missing");
}
std::vector<float> reference(int rate,bool dry)
{
    voxide::Processor p;set(p,"scaleRoot",5);set(p,"scaleSet",1);set(p,"voiceDegree1",0);set(p,"voiceLevel2",-6);
    if (dry) for (const auto* id:{"voiceEnabled1","voiceEnabled2","voiceEnabled3"}) set(p,id,0);
    p.setNonRealtime(true);p.prepareToPlay(rate,128);std::vector<float> result;std::size_t event=0;bool bypass=false;
    for (int at=0;at<rate+rate*6/10;)
    {
        if (event<events.size() && at==events[event])
        {
            if (event==0) { set(p,"scaleRoot",7);set(p,"scaleSet",2); }
            if (event==1) set(p,"voiceDegree1",-2);
            if (event==2) set(p,"voiceLevel2",-9);
            if (event==3) { bypass=true;p.reset(); }
            if (event==4) bypass=false;
            ++event;
        }
        int n=std::min(128,rate+rate*6/10-at);if (event<events.size()) n=std::min(n,events[event]-at);
        juce::AudioBuffer<float> audio(2,n);juce::MidiBuffer midi;
        for (int i=0;i<n;++i) audio.setSample(0,i,signal(at+i,rate));
        if (bypass) p.processBlockBypassed(audio,midi);else p.processBlock(audio,midi);
        require(p.studioStatus().status==voxide::studio::Status::ready,"Healthy reference faulted");
        for (int i=0;i<n;++i) result.push_back(audio.getSample(0,i));at+=n;
    }
    return result;
}
std::vector<float> capture(Unit& u,int rate,bool offline,bool selectedSide,const std::vector<int>& partitions,bool verifyRecall=false)
{
    Input main {rate,!selectedSide},side {rate,selectedSide};u.initialize(rate,offline,main,side);
    if (verifyRecall) require(u.matchesInitial(selectedSide,false),"Initialized AU lost recalled parameters before audio/automation");
    std::vector<float> result;std::array<float,1024> left {},right {};
    struct Buffers { UInt32 count=2;AudioBuffer data[2]; } buffers;
    buffers.data[0]={1,1024*sizeof(float),left.data()};buffers.data[1]={1,1024*sizeof(float),right.data()};
    const auto epoch=std::chrono::steady_clock::now();std::size_t event=0,partition=0;
    for (int at=0;at<rate+rate*6/10;)
    {
        if (event<events.size() && at==events[event])
        {
            if (event==0) { u.set("Scale root",7);u.set("Scale (12-TET)",2); }
            if (event==1) u.set("Voice 1 degree steps",-2);
            if (event==2) u.set("Voice 2 level",-9);
            if (event==3 || event==4)
            { UInt32 bypass=event==3?1u:0u;checked(AudioUnitSetProperty(u.unit,kAudioUnitProperty_BypassEffect,kAudioUnitScope_Global,0,&bypass,sizeof(bypass)),"Toggle AU bypass"); }
            ++event;
        }
        int n=std::min(partitions[partition++%partitions.size()],rate+rate*6/10-at);if (event<events.size()) n=std::min(n,events[event]-at);
        if (!offline) std::this_thread::sleep_until(epoch+std::chrono::nanoseconds(static_cast<std::uint64_t>(at)*1000000000ull/static_cast<unsigned>(rate)));
        AudioTimeStamp time {};time.mFlags=kAudioTimeStampSampleTimeValid;time.mSampleTime=at;AudioUnitRenderActionFlags flags=0;
        for (auto& b:buffers.data) b.mDataByteSize=static_cast<UInt32>(n)*sizeof(float);
        checked(AudioUnitRender(u.unit,&flags,&time,0,static_cast<UInt32>(n),reinterpret_cast<AudioBufferList*>(&buffers)),"Render exact AU");
        for (int i=0;i<n;++i)
        { require(std::isfinite(left[static_cast<std::size_t>(i)]) && juce::exactlyEqual(left[static_cast<std::size_t>(i)],right[static_cast<std::size_t>(i)]),"Invalid AU output");result.push_back(left[static_cast<std::size_t>(i)]); }
        at+=n;
    }
    checked(AudioUnitUninitialize(u.unit),"Uninitialize exact AU");return result;
}
void equal(const std::vector<float>& actual,const std::vector<float>& expected,int rate,bool dry)
{
    if (actual!=expected)
    {
        std::size_t first=0,differences=0,last=0;double maximum=0;
        for (std::size_t i=0;i<std::min(actual.size(),expected.size());++i) if (!juce::exactlyEqual(actual[i],expected[i]))
        { if (!differences) first=i;++differences;last=i;maximum=std::max(maximum,static_cast<double>(std::abs(actual[i]-expected[i]))); }
        std::cerr<<"AU mismatch rate="<<rate<<" dry="<<dry<<" sizes="<<actual.size()<<'/'<<expected.size()<<" first="<<first<<" last="<<last<<" count="<<differences<<" max="<<maximum;
        if (first<actual.size() && first<expected.size()) std::cerr<<" actual="<<actual[first]<<" expected="<<expected[first];std::cerr<<'\n';
        throw std::runtime_error("Exact AU/reference bounce/automation/bypass/recall mismatch");
    }
    bool wet=false;
    for (std::size_t i=0;i<actual.size();++i)
    {
        const float lead=i<static_cast<std::size_t>(rate/10)?0.f:signal(static_cast<int>(i)-rate/10,rate);
        if (dry) require(juce::exactlyEqual(actual[i],lead),"AU first-sample/unity alignment mismatch");
        if (i>static_cast<std::size_t>(rate/2) && i<static_cast<std::size_t>(rate) && std::abs(actual[i]-lead)>1e-4f) wet=true;
    }
    require(dry || wet,"AU harmony check passed on delayed lead only");
    for (std::size_t i=actual.size()-static_cast<std::size_t>(rate/10);i<actual.size();++i) require(std::abs(actual[i])<1e-6f,"AU tail truncated/not cleared");
}
void writeBytes(const std::string& path,const void* data,std::size_t size)
{
    const int file=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
    require(file>=0,"Refusing existing/unsafe evidence destination");std::size_t written=0;
    while (written<size)
    {
        const auto n=::write(file,static_cast<const char*>(data)+written,size-written);
        if (n<0 && errno==EINTR) continue;
        if (n<=0) { ::close(file);throw std::runtime_error("Write evidence failed"); }
        written+=static_cast<std::size_t>(n);
    }
    require(::close(file)==0,"Close evidence failed");
}
CFPropertyListRef readState(const std::string& path)
{
    std::ifstream input(path,std::ios::binary);require(input.good(),"Read state fixture");std::vector<char> bytes((std::istreambuf_iterator<char>(input)),{});
    auto data=CFDataCreate(nullptr,reinterpret_cast<const UInt8*>(bytes.data()),static_cast<CFIndex>(bytes.size()));
    auto state=CFPropertyListCreateWithData(nullptr,data,kCFPropertyListImmutable,nullptr,nullptr);CFRelease(data);require(state,"Invalid saved AU state");return state;
}
void recallParameterGuards(AudioComponent component)
{
    Unit u(component);u.initial(false,false);require(u.matchesInitial(false,false),"Initial AU parameter fixture mismatch");
    // Each omitted field must be detected even though the original audio fixture
    // cannot distinguish F minor from default C major before automation starts.
    for (const char* name:{"Scale root","Scale (12-TET)"})
    {
        u.set(name,0);require(!u.matchesInitial(false,false),"Recall guard accepted a defaulted key/scale");
        u.initial(false,false);require(u.matchesInitial(false,false),"Recall negative control did not restore fixture");
    }
}
}
int main(int argc,char** argv)
{
    std::string report;
    try
    {
        juce::ScopedJuceInitialiser_GUI gui;require(argc>=3 && std::string(argv[1])=="--component","Pass --component exact.component");
        std::string save,restore,audio;
        for (int i=3;i<argc;i+=2)
        {
            require(i+1<argc,"Missing option value");const std::string key=argv[i];
            if (key=="--report") report=argv[i+1];else if (key=="--save-state") save=argv[i+1];
            else if (key=="--restore-state") restore=argv[i+1];else if (key=="--audio") audio=argv[i+1];else throw std::runtime_error("Unknown host-test option");
        }
        require(save.empty() || restore.empty(),"Choose save or restore");Bundle bundle(argv[2]);recallParameterGuards(bundle.component);int cases=0;
        if (!save.empty() || !restore.empty())
        {
            Unit u(bundle.component);
            if (!restore.empty()) { auto state=readState(restore);u.restore(state);CFRelease(state); }
            else
            {
                u.initial(false,false);auto state=u.state();auto bytes=CFPropertyListCreateData(nullptr,state,kCFPropertyListBinaryFormat_v1_0,0,nullptr);CFRelease(state);
                require(bytes,"Serialize AU state");writeBytes(save,CFDataGetBytePtr(bytes),static_cast<std::size_t>(CFDataGetLength(bytes)));CFRelease(bytes);
            }
            require(u.matchesInitial(false,false),"AU ClassInfo did not restore all initial parameters");
            const auto output=capture(u,48000,true,false,{512},true);equal(output,reference(48000,false),48000,false);
            require(!audio.empty(),"State process test requires an output capture");writeBytes(audio,output.data(),output.size()*sizeof(float));cases=1;
        }
        else
        {
            for (int rate:{44100,48000}) for (bool dry:{false,true})
            {
                const auto expected=reference(rate,dry);
                for (int mode=0;mode<3;++mode)
                {
                    Unit u(bundle.component);const bool side=mode==2;u.initial(side,dry);
                    const auto output=capture(u,rate,mode!=0,side,mode==0?std::vector<int>{128}:mode==1?std::vector<int>{512}:std::vector<int>{1,137,1024,32,257});
                    equal(output,expected,rate,dry);++cases;
                }
            }
            Unit changed(bundle.component);
            for (int rate:{44100,48000})
            {
                changed.initial(false,false);changed.latencyNotifications.store(0);
                const auto output=capture(changed,rate,true,false,{512});
                equal(output,reference(rate,false),rate,false);++cases;
            }
        }
        const auto json=std::string("{\"schema\":\"voxide.pr08-native-host.v1\",\"status\":\"pass\",\"pid\":")+std::to_string(getpid())
            +",\"cases\":"+std::to_string(cases)+",\"exact_reference\":true,\"latency_notifications\":true,\"initial_parameters_checked\":true,\"recall_parameter_negative_controls\":2,\"installed_registry_or_Logic_test\":false,\"scope\":\"Exact-bundle synthetic functional API test, not Logic PDC or vocal qualification\"}\n";
        if (!report.empty()) writeBytes(report,json.data(),json.size());std::cout<<json;return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr<<e.what()<<'\n';
        if (!report.empty() && !std::filesystem::exists(report)) { const std::string failed="{\"schema\":\"voxide.pr08-native-host.v1\",\"status\":\"fail\"}\n";writeBytes(report,failed.data(),failed.size()); }
        return 1;
    }
}
