#include "InteractionProcessor.h"
#include "EngineeringProbe.h"
#include "AllocationAudit.h"
#include <algorithm>
#include <bit>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>

using namespace voxide;
using namespace voxide::interaction;
namespace
{
void require(bool value,const char* message) { if (!value) throw std::runtime_error(message); }
void save(const std::string& path, const char* data,std::size_t bytes)
{
    const int fd=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600); require(fd>=0,"Evidence path exists/unwritable");
    while (bytes)
    {
        const auto n=::write(fd,data,bytes);
        if (n<0 && errno==EINTR) continue;
        if (n<=0) { ::close(fd); throw std::runtime_error("Evidence write failed"); }
        data+=n; bytes-=static_cast<std::size_t>(n);
    }
    require(::close(fd)==0,"Evidence close failed");
}
void save(const std::string& path,const std::string& text) { save(path,text.data(),text.size()); }
int integer(const std::string& text)
{
    std::size_t used=0; const int value=std::stoi(text,&used); require(used==text.size(),"Invalid integer"); return value;
}
std::vector<Event> loadEvents(const char* path)
{
    std::ifstream stream(path); require(stream.good(),"Cannot read events");
    std::vector<Event> events; std::string line;
    while (std::getline(stream,line))
    {
        std::istringstream row(line); Event e; char kind=0; unsigned a=0,b=0,c=0;
        require(static_cast<bool>(row>>e.available>>e.source>>kind),"Invalid event header");
        if (kind=='P')
        {
            e.kind=Event::Kind::pitch; int voiced=0;
            require(static_cast<bool>(row>>e.pitch.hz>>e.pitch.confidence>>voiced>>e.pitch.begin>>e.pitch.end) && (voiced==0 || voiced==1),"Invalid oracle frame");
            e.pitch.voiced=voiced!=0;
        }
        else if (kind=='T')
        {
            e.kind=Event::Kind::targets; require(static_cast<bool>(row>>e.targetMidi[0]>>e.targetMidi[1]>>e.targetMidi[2]>>e.mask),"Invalid targets");
        }
        else if (kind=='M')
        {
            e.kind=Event::Kind::midi; require(static_cast<bool>(row>>a>>b>>c) && a<=255 && b<=127 && c<=127,"Invalid MIDI bytes");
            e.bytes={static_cast<std::uint8_t>(a),static_cast<std::uint8_t>(b),static_cast<std::uint8_t>(c)};
        }
        else if (kind=='H')
        {
            e.kind=Event::Kind::harmony;
            require(static_cast<bool>(row>>e.harmony.root>>e.harmony.scale>>e.harmony.customMask
                >>e.harmony.degrees[0]>>e.harmony.degrees[1]>>e.harmony.degrees[2]>>e.harmony.octaves[0]>>e.harmony.octaves[1]>>e.harmony.octaves[2]),"Invalid harmony state");
        }
        else throw std::runtime_error("Unknown event kind");
        std::string extra; require(!(row>>extra),"Extra event data");
        require(e.available>=e.source && (events.empty() || e.available>=events.back().available) && events.size()<100000,"Invalid event chronology");
        events.push_back(e);
    }
    return events;
}
struct Callback { std::uint64_t begin=0,frames=0,ns=0; std::size_t allocations=0; };
void selfTest()
{
    if (audit::available) require(audit::selfTest(),"Allocation audit controls failed");
    std::size_t stoppedReconstructionAllocations=0;
    for (int rate : {44100,48000}) for (auto treatment : {Treatment::native,Treatment::shared}) for (auto mode : {Mode::oraclePrescribed,Mode::livePrescribed,Mode::scale,Mode::midi})
    {
        Settings s; s.engine.rate=rate;
#ifdef VOXIDE_ENGINE_rubberband
        s.engine.window=1;
#endif
        s.treatment=treatment; s.mode=mode;
        Processor processor(s,engines::create); processor.start();
        require(!processor.configureStopped(s),"Running reconfiguration accepted");
        Event pitch; pitch.pitch.hz=220; pitch.pitch.confidence=1; pitch.pitch.voiced=true;
        require(processor.post(pitch),"Initial pitch rejected");
        for (std::uint8_t note : {57,64,69}) { Event e; e.kind=Event::Kind::midi; e.bytes={0x90,note,100}; require(processor.post(e),"MIDI chord rejected"); }
        for (int i=0;i<rate/2;++i)
        {
            const auto output=processor.push(i<rate/10?static_cast<float>(.05*std::sin(6.283185307179586*220*i/rate)):0);
            require(std::isfinite(output.sumAligned) && std::isfinite(output.sumDirect),"Nonfinite interaction render");
            Telemetry t; while (processor.readTelemetry(t)) {}
        }
        processor.stop(); audit::begin(); const bool reset=processor.resetStopped();
        stoppedReconstructionAllocations+=audit::end(); require(reset,"Stopped reset failed"); processor.start();
        for (int i=0;i<rate/3;++i) require(std::abs(processor.push(0).sumAligned)<1e-6,"Stopped graph reconstruction leaked history");
        processor.stop();
    }
    if (audit::available) require(stoppedReconstructionAllocations>0,"Stopped reconstruction allocation control did not exercise auditor");
    std::cout<<"Native three-voice smoke/reset/configuration checks passed; stopped reconstruction allocation calls="<<stoppedReconstructionAllocations
        <<" (off render, intentionally allocating); quality/callback-allocation gates remain separate\n";
}
}
int main(int argc,char** argv)
{
    try
    {
        if (argc==2 && std::string(argv[1])=="--self-test") { selfTest(); return 0; }
        if (argc==7 && std::string(argv[1])=="--engineering")
            return runEngineering({integer(argv[2]),integer(argv[3]),integer(argv[4])},integer(argv[5]),argv[6]);
        if (argc==2 && std::string(argv[1])=="--describe")
        {
            std::cout<<"{\"schema\":\"voxide.interaction-capabilities.v1\",\"engine\":\""<<engines::engineName()
                <<"\",\"compiled_source_identity\":\""<<VOXIDE_INTERACTION_SOURCE_IDENTITY<<"\",\"profile\":\""<<VOXIDE_INTERACTION_PROFILE
                <<"\",\"sanitizer\":\""<<VOXIDE_INTERACTION_SANITIZER<<"\",\"audit_available\":"<<(audit::available?"true":"false")
                <<",\"shift_limits\":[12,24],\"inactive_uncertain_supported\":true,\"engineering_probe_v1\":true}\n";
            return 0;
        }
        require(argc==11 || argc==13,"Usage: interaction <rate> <window> <hop> <mode0..3> <treatment0..1> <profile0..1> <events> <prefix> <blocks-csv> <tail-frames> [<shift-limit12or24> <inactive-uncertain0or1>] < mono-f32");
        require(std::endian::native==std::endian::little && sizeof(float)==4,"Requires little-endian float32");
        Settings s; s.engine={integer(argv[1]),integer(argv[2]),integer(argv[3])};
        s.mode=static_cast<Mode>(integer(argv[4])); s.treatment=static_cast<Treatment>(integer(argv[5])); s.profile=static_cast<Profile>(integer(argv[6]));
        if (argc==13)
        {
            s.shiftLimit=integer(argv[11]); const int inactive=integer(argv[12]);
            require(inactive==0 || inactive==1,"Invalid uncertainty policy"); s.inactiveUncertain=inactive!=0;
        }
        auto events=loadEvents(argv[7]);
        std::vector<int> blocks; std::istringstream partition(argv[9]); std::string token;
        while (std::getline(partition,token,',')) { const int n=integer(token); require(n>=1 && n<=4096,"Invalid callback size"); blocks.push_back(n); }
        require(!blocks.empty(),"No callbacks"); const int tail=integer(argv[10]); require(tail>=0 && tail<=s.engine.rate*2,"Invalid zero-tail");
        std::vector<float> input; std::array<float,4096> scratch {};
        while (std::cin.read(reinterpret_cast<char*>(scratch.data()),sizeof(scratch)) || std::cin.gcount()>0)
        {
            require(std::cin.gcount()%4==0,"Partial PCM float");
            input.insert(input.end(),scratch.begin(),scratch.begin()+std::cin.gcount()/4);
            require(input.size()<=48000*120,"Two-minute source bound exceeded");
        }
        require(!std::cin.bad() && !input.empty(),"Invalid input stream");
        require(events.empty() || events.back().available<input.size(),"Event outside source");
        if (audit::available) require(audit::selfTest(),"Allocation audit controls failed");
        const auto total=input.size()+static_cast<std::size_t>(tail);
        std::array<std::vector<float>,10> outputs;
        for (auto& channel:outputs) channel.resize(total);
        std::vector<Telemetry> telemetry; telemetry.reserve(total*6/static_cast<unsigned>(std::max(1,s.engine.hop))+events.size()+10000);
        std::vector<Callback> callbacks; callbacks.reserve(total/static_cast<unsigned>(*std::min_element(blocks.begin(),blocks.end()))+1);
        Processor processor(s,engines::create); processor.start();
        std::size_t position=0,event=0,blockIndex=0;
        while (position<total)
        {
            const auto frames=std::min(total-position,static_cast<std::size_t>(blocks[blockIndex++%blocks.size()]));
            Callback callback {position,frames,0,0};
            const auto start=std::chrono::steady_clock::now(); audit::begin();
            try
            {
                for (std::size_t i=position;i<position+frames;++i)
                {
                    while (event<events.size() && events[event].available<=i) require(processor.post(events[event++]),"Event mailbox overflow");
                    const auto out=processor.push(i<input.size()?input[i]:0);
                    outputs[0][i]=out.leadDirect; outputs[1][i]=out.leadAligned;
                    for (std::size_t v=0;v<3;++v) { outputs[2+v][i]=out.native[v]; outputs[5+v][i]=out.voices[v]; }
                    outputs[8][i]=out.sumDirect; outputs[9][i]=out.sumAligned;
                }
            }
            catch (...) { audit::end(); throw; }
            callback.allocations=audit::end();
            callback.ns=static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count());
            callbacks.push_back(callback); position+=frames;
            Telemetry t;
            while (processor.readTelemetry(t))
            {
                // Consumer-side callback availability never backdates native delivery.
                if (t.kind==Telemetry::Kind::output) t.available=position;
                telemetry.push_back(t);
            }
        }
        audit::begin(); processor.stop(); const auto finishAllocations=audit::end();
        Telemetry t; while (processor.readTelemetry(t)) { if (t.kind==Telemetry::Kind::output) t.available=total; telemetry.push_back(t); }
        const auto& counts=processor.stats(); const std::string prefix=argv[8];
        const std::array<const char*,10> names {"lead-direct","lead-aligned","native1","native2","native3","voice1","voice2","voice3","sum-direct","sum-aligned"};
        for (std::size_t i=0;i<names.size();++i) save(prefix+"-"+names[i]+".f32",reinterpret_cast<const char*>(outputs[i].data()),outputs[i].size()*4);
        std::ostringstream csv,control;
        csv<<"begin,frames,ns,allocations\n";
        for (const auto& c:callbacks) csv<<c.begin<<','<<c.frames<<','<<c.ns<<','<<c.allocations<<'\n';
        save(prefix+"-callbacks.csv",csv.str());
        control<<std::setprecision(17)<<"kind,epoch,wall,source,voice,requested,available,frame_begin,frame_end,frame_available,hz,confidence,voiced,active,target_midi,requested_shift,applied_shift,weight,first_output,count,request_kind\n";
        for (const auto& e:telemetry) control<<static_cast<int>(e.kind)<<','<<e.epoch<<','<<e.wall<<','<<e.source<<','<<e.voice<<','<<e.requested<<','<<e.available<<','<<e.frameBegin<<','<<e.frameEnd<<','<<e.frameAvailable<<','<<e.hz<<','<<e.confidence<<','<<e.voiced<<','<<e.active<<','<<e.targetMidi<<','<<e.requestedShift<<','<<e.appliedShift<<','<<e.weight<<','<<e.firstOutput<<','<<e.count<<','<<e.requestKind<<'\n';
        save(prefix+"-telemetry.csv",control.str());
        std::ostringstream report;
        report<<std::setprecision(17)<<"{\"schema\":\"voxide.interaction-render.v1\",\"engine\":\""<<engines::engineName()<<"\",\"profile\":\""<<VOXIDE_INTERACTION_PROFILE
            <<"\",\"sanitizer\":\""<<VOXIDE_INTERACTION_SANITIZER<<"\",\"compiled_source_identity\":\""<<VOXIDE_INTERACTION_SOURCE_IDENTITY
            <<"\",\"sample_rate\":"<<s.engine.rate<<",\"window\":"<<s.engine.window<<",\"hop\":"<<s.engine.hop<<",\"mode\":"<<static_cast<int>(s.mode)
            <<",\"treatment\":"<<static_cast<int>(s.treatment)<<",\"reserve_profile\":"<<static_cast<int>(s.profile)<<",\"source_frames\":"<<input.size()<<",\"zero_tail\":"<<tail
            <<",\"output_frames\":"<<total<<",\"latency_samples\":"<<processor.latencySamples()<<",\"analysis_delay_samples\":"<<processor.analysisDelaySamples()
            <<",\"shift_limit\":"<<s.shiftLimit<<",\"inactive_uncertain\":"<<(s.inactiveUncertain?"true":"false")
            <<",\"lead_gain\":1,\"harmony_gain_each\":0.333333333333333333,\"ramp_semitones_per_second\":2400,\"crossfade_ms\":10,\"audit_available\":"<<(audit::available?"true":"false")
            <<",\"finish_allocations\":"<<finishAllocations<<",\"unrendered_finish_peak\":"<<counts.unrenderedFinishPeak
            <<",\"telemetry_dropped\":"<<counts.telemetryDropped<<",\"bad_events\":"<<counts.badEvents<<",\"late_controls\":"<<counts.lateControls
            <<",\"invalid_input\":"<<counts.invalidInput<<",\"missing_metadata\":"<<counts.missingMetadata<<",\"rejected_targets\":"<<counts.rejectedTargets<<",\"fifo_overflow\":"<<counts.fifoOverflow<<",\"voices\":[";
        for (std::size_t v=0;v<3;++v)
        {
            if (v) report<<',';
            report<<"{\"native_frames\":"<<counts.nativeFrames[v]<<",\"underflows\":"<<counts.underflows[v]<<",\"late_samples\":"<<counts.lateSamples[v]
                <<",\"native_input_hash\":\""<<counts.inputHashes[v]<<"\",\"control_hash\":\""<<counts.controlHashes[v]<<"\"}";
        }
        report<<"]}\n"; save(prefix+"-native.json",report.str());
        return 0;
    }
    catch (const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
    catch (const char* e) { std::cerr<<e<<'\n'; return 1; }
}
