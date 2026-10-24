#include "EngineeringProbe.h"
#include "InteractionProcessor.h"
#include "AllocationAudit.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cerrno>
#include <fcntl.h>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <unistd.h>
#include <vector>

namespace voxide::interaction
{
namespace
{
using Clock=std::chrono::steady_clock;
std::uint64_t elapsed(Clock::time_point start)
{
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-start).count());
}
void require(bool value,const char* text) { if(!value) throw std::runtime_error(text); }
void save(const std::string& path,const char* bytes,std::size_t count)
{
    const int fd=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);
    require(fd>=0,"Engineering evidence exists/unwritable");
    while(count)
    {
        const auto n=::write(fd,bytes,count);
        if(n<0 && errno==EINTR) continue;
        if(n<=0) { ::close(fd); throw std::runtime_error("Engineering write failed"); }
        bytes+=n; count-=static_cast<std::size_t>(n);
    }
    require(::close(fd)==0,"Engineering close failed");
}
void save(const std::string& path,const std::string& value) { save(path,value.data(),value.size()); }
struct Callback { std::uint64_t begin=0,frames=0,ns=0; std::size_t allocations=0; };
struct Capture
{
    std::vector<Output> output;
    std::vector<Callback> callbacks;
    std::vector<Telemetry> controls;
    Stats stats;
    bool complete=false;
    std::size_t processed=0,finishAllocations=0;
    std::uint64_t finishNs=0;
    std::string error;
};
std::vector<float> source(int rate)
{
    std::vector<float> result(static_cast<std::size_t>(rate*5+rate*3/5));
    double phase=0;
    std::uint32_t noise=0x564f5849;
    for(int i=0;i<rate*5;++i)
    {
        const double seconds=static_cast<double>(i)/rate;
        const double hz=seconds<.8?82.4068892282175:seconds<1.6?220:seconds<2.4?1046.5022612023945:
            seconds<2.8?220:seconds<4?220*std::exp2(2*std::sin((seconds-2.8)*6.283185307179586)/12):110;
        phase+=6.283185307179586*hz/rate;
        noise^=noise<<13;noise^=noise>>17;noise^=noise<<5;
        float value=0;
        if(seconds>=2.4 && seconds<2.8) value=static_cast<float>((static_cast<double>(noise)/4294967295.0-.5)*.02);
        else for(int harmonic=1;harmonic<=6;++harmonic)
            if(harmonic*hz<rate*.45) value+=static_cast<float>(.04/harmonic*std::sin(harmonic*phase));
        // Final .6 seconds are supplied zero input, not removed from capture/timing.
        result[static_cast<std::size_t>(i)]=value;
    }
    return result;
}
std::array<Event,4> events(int rate)
{
    std::array<Event,4> result;
    for(auto& event:result) event.kind=Event::Kind::harmony;
    result[1].source=result[1].available=static_cast<std::uint64_t>(std::llround(rate*1.6));
    result[1].harmony.degrees={0,0,0}; result[1].harmony.octaves={-1,0,1};
    result[2].source=result[2].available=static_cast<std::uint64_t>(std::llround(rate*2.8));
    result[2].harmony.degrees={-2,-4,0}; result[2].harmony.octaves={0,0,-1};
    result[3].source=result[3].available=static_cast<std::uint64_t>(rate*4.0);
    return result; // Final configuration equals the initial one before stopped reset.
}
Capture capture(Processor& processor,const std::vector<float>& input,int rate,int block)
{
    Capture result;
    result.output.resize(input.size());
    result.callbacks.reserve(input.size()/static_cast<unsigned>(block)+1);
    result.controls.reserve(input.size()/16+1024);
    const auto musical=events(rate);
    std::size_t next=0;
    processor.start();
    try
    {
        for(std::size_t begin=0;begin<input.size();)
        {
            const auto count=std::min(static_cast<std::size_t>(block),input.size()-begin);
            Callback row{begin,count,0,0};
            const auto start=Clock::now(); audit::begin();
            try
            {
                for(std::size_t i=begin;i<begin+count;++i)
                {
                    while(next<musical.size() && musical[next].available<=i)
                        require(processor.post(musical[next++]),"Engineering control inbox overflow");
                    result.output[i]=processor.push(input[i]); ++result.processed;
                }
            }
            catch(...) { row.allocations=audit::end(); row.ns=elapsed(start); result.callbacks.push_back(row); throw; }
            row.allocations=audit::end(); row.ns=elapsed(start);
            result.callbacks.push_back(row); begin+=count;
            Telemetry t;
            while(processor.readTelemetry(t)) if(t.kind==Telemetry::Kind::control) result.controls.push_back(t);
        }
        const auto start=Clock::now(); audit::begin();
        try { processor.stop(); }
        catch(...) { result.finishAllocations=audit::end(); result.finishNs=elapsed(start); throw; }
        result.finishAllocations=audit::end(); result.finishNs=elapsed(start);
        Telemetry t; while(processor.readTelemetry(t)) if(t.kind==Telemetry::Kind::control) result.controls.push_back(t);
        result.complete=true;
    }
    catch(const std::exception& error) { audit::end(); result.error=error.what(); }
    catch(const char* error) { audit::end(); result.error=error; }
    result.stats=processor.stats();
    result.output.resize(result.processed);
    return result;
}
std::array<float,10> channels(const Output& sample)
{
    return {sample.leadDirect,sample.leadAligned,sample.native[0],sample.native[1],sample.native[2],
            sample.voices[0],sample.voices[1],sample.voices[2],sample.sumDirect,sample.sumAligned};
}
void retain(const std::string& prefix,const Capture& capture)
{
    for(std::size_t channel=0;channel<10;++channel)
    {
        std::vector<float> values; values.reserve(capture.output.size());
        for(const auto& sample:capture.output) values.push_back(channels(sample)[channel]);
        save(prefix+"-channel"+std::to_string(channel)+".f32",reinterpret_cast<const char*>(values.data()),values.size()*4);
    }
    std::ostringstream callbacks,controls;
    callbacks<<"begin,frames,ns,allocations\n";
    for(const auto& row:capture.callbacks) callbacks<<row.begin<<','<<row.frames<<','<<row.ns<<','<<row.allocations<<'\n';
    save(prefix+"-callbacks.csv",callbacks.str());
    controls<<std::setprecision(17)<<"voice,source,wall,frame_available,hz,confidence,voiced,active,shift\n";
    for(const auto& t:capture.controls) controls<<t.voice<<','<<t.source<<','<<t.wall<<','<<t.frameAvailable<<','<<t.hz<<','<<t.confidence<<','<<t.voiced<<','<<t.active<<','<<t.appliedShift<<'\n';
    save(prefix+"-controls.csv",controls.str());
    save(prefix+"-error.txt",capture.error);
}
void stats(std::ostream& out,const Capture& capture,const char* label)
{
    const auto& s=capture.stats;
    out<<"{\"name\":\""<<label<<"\",\"complete\":"<<(capture.complete?"true":"false")<<",\"processed\":"<<capture.processed
       <<",\"finish_allocations\":"<<capture.finishAllocations<<",\"finish_ns\":"<<capture.finishNs
       <<",\"finish_peak\":"<<s.unrenderedFinishPeak<<",\"bad_events\":"<<s.badEvents<<",\"late_controls\":"<<s.lateControls
       <<",\"telemetry_dropped\":"<<s.telemetryDropped<<",\"invalid_input\":"<<s.invalidInput<<",\"missing_metadata\":"<<s.missingMetadata
       <<",\"fifo_overflow\":"<<s.fifoOverflow<<",\"rejected_targets\":"<<s.rejectedTargets<<",\"voices\":[";
    for(int v=0;v<3;++v)
    {
        if(v) out<<',';
        out<<"{\"underflows\":"<<s.underflows[v]<<",\"late_samples\":"<<s.lateSamples[v]<<",\"native_frames\":"<<s.nativeFrames[v]
           <<",\"input_hash\":\""<<s.inputHashes[v]<<"\",\"control_hash\":\""<<s.controlHashes[v]<<"\"}";
    }
    out<<"]}";
}
}
int runEngineering(engines::Config config,int block,const std::string& prefix)
{
    require((config.rate==44100 || config.rate==48000) && (block==128 || block==512),"Unsupported bounded engineering rate/block");
    const bool signalsmith=std::string(engines::engineName())=="signalsmith";
    require((signalsmith && config.window==2048 && config.hop==512) || (!signalsmith && config.window==1 && config.hop==128),"Only the two studio candidates may be benchmarked");
    if(audit::available) require(audit::selfTest(),"Allocation audit controls failed");
    const auto input=source(config.rate);
    save(prefix+"-source.f32",reinterpret_cast<const char*>(input.data()),input.size()*4);
    Settings settings;settings.engine=config;settings.mode=Mode::scale;settings.profile=Profile::mix;
    settings.shiftLimit=12;settings.inactiveUncertain=true;
    auto start=Clock::now();audit::begin();
    auto processor=std::make_unique<Processor>(settings,engines::create);
    const auto setupAllocations=audit::end(); const auto setupNs=elapsed(start);
    const auto cold=capture(*processor,input,config.rate,block);
    bool restartRejected=false;
    if(cold.complete) { try { processor->start(); } catch(const std::logic_error&) { restartRejected=true; } }
    start=Clock::now();audit::begin();
    bool reset=false;
    if(cold.complete) reset=processor->resetStopped();
    const auto resetAllocations=audit::end(); const auto resetNs=elapsed(start);
    const auto afterReset=reset?capture(*processor,input,config.rate,block):Capture{};
    // Fresh construction AFTER both workloads deliberately exercises process-warm
    // lifetime behavior. No native reset or priming workaround is substituted.
    start=Clock::now();audit::begin();
    auto fresh=std::make_unique<Processor>(settings,engines::create);
    const auto freshAllocations=audit::end(); const auto freshNs=elapsed(start);
    const auto warmFresh=capture(*fresh,input,config.rate,block);
    retain(prefix+"-cold",cold);retain(prefix+"-reset",afterReset);retain(prefix+"-fresh",warmFresh);
    std::ostringstream report;report<<std::setprecision(17)
        <<"{\"schema\":\"voxide.studio-engineering-native.v1\",\"compiled_source_identity\":\""<<VOXIDE_INTERACTION_SOURCE_IDENTITY
        <<"\",\"profile\":\""<<VOXIDE_INTERACTION_PROFILE<<"\",\"sanitizer\":\""<<VOXIDE_INTERACTION_SANITIZER
        <<"\",\"engine\":\""<<engines::engineName()<<"\",\"audit_available\":"<<(audit::available?"true":"false")
        <<",\"rate\":"<<config.rate<<",\"window\":"<<config.window<<",\"hop\":"<<config.hop<<",\"block\":"<<block
        <<",\"frames\":"<<input.size()<<",\"source_frames\":"<<config.rate*5<<",\"zero_tail\":"<<config.rate*3/5
        <<",\"shift_limit\":12,\"inactive_uncertain\":true,\"voices\":3,\"reserve_ms\":100"
        <<",\"setup_allocations\":"<<setupAllocations<<",\"setup_ns\":"<<setupNs<<",\"reset_allocations\":"<<resetAllocations<<",\"reset_ns\":"<<resetNs
        <<",\"fresh_allocations\":"<<freshAllocations<<",\"fresh_ns\":"<<freshNs<<",\"restart_rejected\":"<<(restartRejected?"true":"false")
        <<",\"reset_reconstructed\":"<<(reset?"true":"false")<<",\"captures\":[";
    stats(report,cold,"cold");report<<',';stats(report,afterReset,"reset");report<<',';stats(report,warmFresh,"fresh");report<<"]}\n";
    save(prefix+"-engineering.json",report.str());
    return cold.complete && afterReset.complete && warmFresh.complete && reset && restartRejected?0:1;
}
}
