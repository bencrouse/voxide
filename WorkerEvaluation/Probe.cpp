#include "WorkerEngine.h"
#include "../Source/Tests/AllocationAudit.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace
{
using namespace voxide;
using Clock=std::chrono::steady_clock;
void require(bool value,const char* text) { if (!value) throw std::runtime_error(text); }
std::uint64_t ns(Clock::duration duration)
{ return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(duration).count()); }
struct Group
{
    static thread_local Group* active;
    std::array<worker::Engine*,3> workers {};
    unsigned count=0;
    bool fault=false;
    static std::unique_ptr<engines::Engine> create(engines::Config c,double ratio,double hz)
    {
        require(active && active->count<3,"Worker factory needs a stopped setup scope");
        worker::Engine::Options options;
        if (active->fault && active->count==0) options={64,200};
        auto engine=std::make_unique<worker::Engine>(c,ratio,hz,engines::create,options);
        active->workers[active->count++]=engine.get(); return engine;
    }
    bool healthy() const
    { return std::all_of(workers.begin(),workers.end(),[](auto* e) { return !e || e->healthy(); }); }
    void idle() const
    { for (auto* e:workers) if (e) require(e->waitIdle(),"Offline worker completion failed"); }
    struct Scope
    {
        explicit Scope(Group& group) { require(!active,"Nested worker setup"); active=&group; }
        ~Scope() { active=nullptr; }
    };
};
thread_local Group* Group::active=nullptr;
struct Callback { std::uint64_t begin=0,count=0,elapsed=0,late=0,finish=0,deadline=0; std::size_t allocations=0; };
struct Capture
{
    std::vector<interaction::Output> output;
    std::vector<interaction::Telemetry> telemetry;
    std::vector<Callback> callbacks;
    std::vector<worker::Engine::Metrics> workers;
    interaction::Stats stats;
    std::string mode,error;
    bool complete=false,failedClosed=false;
    std::size_t processed=0,finishAllocations=0,firstFailure=0;
    int analysis=0,latency=0;
};
std::vector<float> source(int rate)
{
    // Same shape/phase/noise construction as the retained engineering fixture.
    std::vector<float> result(static_cast<std::size_t>(rate*28/5));
    double phase=0; std::uint32_t noise=0x564f5849;
    for (int i=0;i<rate*5;++i)
    {
        const double seconds=static_cast<double>(i)/rate;
        const double hz=seconds<.8?82.4068892282175:seconds<1.6?220:seconds<2.4?1046.5022612023945:
            seconds<2.8?220:seconds<4?220*std::exp2(2*std::sin((seconds-2.8)*6.283185307179586)/12):110;
        phase+=6.283185307179586*hz/rate;
        noise^=noise<<13; noise^=noise>>17; noise^=noise<<5;
        float value=0;
        if (seconds>=2.4 && seconds<2.8) value=static_cast<float>((static_cast<double>(noise)/4294967295.0-.5)*.02);
        else for (int h=1;h<=6;++h) if (h*hz<rate*.45) value+=static_cast<float>(.04/h*std::sin(h*phase));
        result[static_cast<std::size_t>(i)]=value;
    }
    return result;
}
std::array<interaction::Event,4> events(int rate)
{
    std::array<interaction::Event,4> result;
    for (auto& e:result) e.kind=interaction::Event::Kind::harmony;
    result[1].source=result[1].available=static_cast<std::uint64_t>(std::llround(rate*1.6));
    result[1].harmony.degrees={0,0,0}; result[1].harmony.octaves={-1,0,1};
    result[2].source=result[2].available=static_cast<std::uint64_t>(std::llround(rate*2.8));
    result[2].harmony.degrees={-2,-4,0}; result[2].harmony.octaves={0,0,-1};
    result[3].source=result[3].available=static_cast<std::uint64_t>(rate*4);
    return result;
}
Capture render(int rate,int block,const std::string& mode,const std::vector<float>& input)
{
    Capture result; result.mode=mode; result.firstFailure=input.size();
    result.output.resize(input.size()); result.callbacks.reserve(input.size()/block+1);
    result.telemetry.reserve(input.size()/8+4096); result.workers.reserve(3);
    Group group; group.fault=mode=="fault"; Group::Scope scope(group);
    interaction::Settings settings; settings.engine={rate,1,128}; settings.mode=interaction::Mode::scale;
    settings.profile=interaction::Profile::mix; settings.shiftLimit=12; settings.inactiveUncertain=true;
    interaction::Processor processor(settings,mode=="reference"?engines::create:Group::create);
    result.analysis=processor.analysisDelaySamples(); result.latency=processor.latencySamples();
    const auto musical=events(rate); std::size_t next=0;
    const bool paced=mode=="paced" || mode=="fault";
    processor.start();
    const auto epoch=Clock::now()+std::chrono::milliseconds(20);
    try
    {
        for (std::size_t begin=0;begin<input.size();)
        {
            const auto count=std::min(static_cast<std::size_t>(block),input.size()-begin);
            const auto scheduled=epoch+std::chrono::nanoseconds(static_cast<std::uint64_t>(begin)*1000000000ull/rate);
            if (paced) std::this_thread::sleep_until(scheduled); // Outside callback.
            if (mode=="offline") group.idle(); // Offline coordinator, outside callback.
            Callback row; row.begin=begin; row.count=count;
            row.deadline=(begin+count)*1000000000ull/rate;
            const auto start=Clock::now();
            if (paced && start>scheduled) row.late=ns(start-scheduled);
            audit::begin();
            try
            {
                for (std::size_t i=begin;i<begin+count;++i)
                {
                    while (next<musical.size() && musical[next].available<=i)
                        require(processor.post(musical[next++]),"Control inbox overflow");
                    auto sample=processor.push(input[i]);
                    const auto& stats=processor.stats();
                    if (!group.healthy() || std::any_of(stats.underflows.begin(),stats.underflows.end(),[](auto n) { return n!=0; }))
                    { if (!result.failedClosed) result.firstFailure=i; result.failedClosed=true; }
                    if (result.failedClosed)
                    {
                        sample.native={}; sample.voices={};
                        sample.sumDirect=sample.leadDirect; sample.sumAligned=sample.leadAligned;
                    }
                    result.output[i]=sample; ++result.processed;
                }
            }
            catch (...) { row.allocations=audit::end(); row.elapsed=ns(Clock::now()-start); result.callbacks.push_back(row); throw; }
            row.allocations=audit::end(); const auto end=Clock::now(); row.elapsed=ns(end-start);
            if (paced) row.finish=ns(end-epoch);
            result.callbacks.push_back(row); begin+=count;
            interaction::Telemetry t; while (processor.readTelemetry(t))
            { if (t.kind==interaction::Telemetry::Kind::output) t.available=begin; result.telemetry.push_back(t); }
        }
        audit::begin(); processor.stop(); result.finishAllocations=audit::end();
        interaction::Telemetry t; while (processor.readTelemetry(t))
        { if (t.kind==interaction::Telemetry::Kind::output) t.available=input.size(); result.telemetry.push_back(t); }
        result.complete=true;
    }
    catch (const std::exception& e) { audit::end(); result.error=e.what(); }
    catch (const char* e) { audit::end(); result.error=e; }
    for (auto* engine:group.workers) if (engine) { engine->finish(); result.workers.push_back(engine->metrics()); }
    result.stats=processor.stats(); result.output.resize(result.processed);
    return result; // Processor destruction joins all workers off callback.
}
void raw(const std::filesystem::path& path,const std::vector<float>& values)
{
    require(!std::filesystem::exists(path),"Evidence already exists");
    std::ofstream stream(path,std::ios::binary);
    stream.write(reinterpret_cast<const char*>(values.data()),static_cast<std::streamsize>(values.size()*4));
    require(stream.good(),"Raw write failed");
}
void retain(const std::filesystem::path& directory,const Capture& c,int rate,int block)
{
    require(std::filesystem::create_directory(directory),"Capture directory exists");
    for (int channel=0;channel<10;++channel)
    {
        std::vector<float> values; values.reserve(c.output.size());
        for (const auto& s:c.output)
        {
            const std::array<float,10> channels {s.leadDirect,s.leadAligned,s.native[0],s.native[1],s.native[2],
                s.voices[0],s.voices[1],s.voices[2],s.sumDirect,s.sumAligned};
            values.push_back(channels[channel]);
        }
        raw(directory/("channel"+std::to_string(channel)+".f32"),values);
    }
    std::ofstream callbacks(directory/"callbacks.csv"),telemetry(directory/"telemetry.csv");
    callbacks<<"begin,frames,ns,allocations,late_ns,finish_ns,deadline_ns\n";
    for (const auto& row:c.callbacks) callbacks<<row.begin<<','<<row.count<<','<<row.elapsed<<','<<row.allocations<<','<<row.late<<','<<row.finish<<','<<row.deadline<<'\n';
    telemetry<<std::setprecision(17)<<"kind,epoch,wall,source,voice,requested,available,frame_begin,frame_end,frame_available,hz,confidence,voiced,active,target_midi,requested_shift,applied_shift,first_output,count,request_kind,weight\n";
    for (const auto& t:c.telemetry) telemetry<<static_cast<int>(t.kind)<<','<<t.epoch<<','<<t.wall<<','<<t.source<<','<<t.voice<<','
        <<t.requested<<','<<t.available<<','<<t.frameBegin<<','<<t.frameEnd<<','<<t.frameAvailable<<','<<t.hz<<','<<t.confidence<<','
        <<t.voiced<<','<<t.active<<','<<t.targetMidi<<','<<t.requestedShift<<','<<t.appliedShift<<','<<t.firstOutput<<','<<t.count<<','<<t.requestKind<<','<<t.weight<<'\n';
    require(callbacks.good() && telemetry.good(),"CSV write failed");
    const auto& s=c.stats;
    std::ofstream report(directory/"native.json"); report<<std::setprecision(17)
        <<"{\"schema\":\"voxide.worker-native.v1\",\"identity\":\""<<WORKER_IDENTITY<<"\",\"profile\":\""<<WORKER_PROFILE
        <<"\",\"sanitizer\":\""<<WORKER_SANITIZER<<"\",\"audit_available\":"<<(audit::available?"true":"false")
        <<",\"mode\":\""<<c.mode<<"\",\"rate\":"<<rate<<",\"block\":"<<block<<",\"latency_samples\":"<<c.latency
        <<",\"analysis_samples\":"<<c.analysis<<",\"frames\":"<<c.output.size()<<",\"complete\":"<<(c.complete?"true":"false")
        <<",\"failed_closed\":"<<(c.failedClosed?"true":"false")<<",\"error\":"<<std::quoted(c.error)
        <<",\"first_failure\":"<<c.firstFailure
        <<",\"finish_allocations\":"<<c.finishAllocations<<",\"finish_peak\":"<<s.unrenderedFinishPeak
        <<",\"telemetry_dropped\":"<<s.telemetryDropped<<",\"bad_events\":"<<s.badEvents<<",\"late_controls\":"<<s.lateControls
        <<",\"invalid_input\":"<<s.invalidInput<<",\"missing_metadata\":"<<s.missingMetadata<<",\"fifo_overflow\":"<<s.fifoOverflow<<",\"voices\":[";
    for (int v=0;v<3;++v)
    {
        if (v) report<<',';
        report<<"{\"native_frames\":"<<s.nativeFrames[v]<<",\"underflows\":"<<s.underflows[v]<<",\"late_samples\":"<<s.lateSamples[v]
              <<",\"input_hash\":\""<<s.inputHashes[v]<<"\",\"control_hash\":\""<<s.controlHashes[v]<<"\"}";
    }
    report<<"],\"workers\":[";
    for (std::size_t i=0;i<c.workers.size();++i)
    {
        if (i) report<<','; const auto& m=c.workers[i];
        report<<"{\"setup_allocations\":"<<m.setupAllocations<<",\"body_allocations\":"<<m.bodyAllocations
              <<",\"finish_allocations\":"<<m.finishAllocations<<",\"destroy_allocations\":"<<m.destroyAllocations
              <<",\"commands\":"<<m.commands<<",\"native_frames\":"<<m.nativeFrames<<",\"queue_high_water\":"<<m.queueHighWater
              <<",\"audit_detected\":"<<(m.auditDetected?"true":"false")<<",\"failed\":"<<(m.failed?"true":"false")<<'}';
    }
    report<<"]}\n"; require(report.good(),"Report write failed");
}
}
int main(int argc,char** argv)
{
    try
    {
        if (argc==2 && std::string(argv[1])=="--identity") { std::cout<<WORKER_IDENTITY<<'\n'; return 0; }
        require(argc==5,"Use --suite|--fault rate block NEW-output-directory");
        const std::string command=argv[1],rateText=argv[2],blockText=argv[3];
        require((command=="--suite" || command=="--fault") && (rateText=="44100" || rateText=="48000")
                && (blockText=="128" || blockText=="512"),"Unsupported fixed worker workload");
        require(command!="--fault" || blockText=="128","Fault case is fixed to 128 frames");
        const int rate=std::stoi(rateText),block=std::stoi(blockText);
        const std::filesystem::path directory=argv[4];
        require(std::filesystem::create_directory(directory),"Output directory must be new");
        if (audit::available) require(audit::selfTest(),"Callback allocation detector failed");
        const auto input=source(rate); raw(directory/"source.f32",input);
        if (command=="--fault") retain(directory/"fault",render(rate,block,"fault",input),rate,block);
        else for (const char* mode:{"reference","paced","offline"}) retain(directory/mode,render(rate,block,mode,input),rate,block);
        return 0;
    }
    catch (const std::exception& e) { audit::end(); std::cerr<<e.what()<<'\n'; return 1; }
}
