#include "EngineAdapter.h"
#include "PitchTracker.h"
#include "HarmonySelector.h"
#include "AllocationAudit.h"
#include "TraceAllocations.h"
#include <algorithm>
#include <bit>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace voxide;
namespace
{
void check(bool value,const char* text) { if(!value) throw std::runtime_error(text); }
int integer(const char* text) { std::size_t n=0; int v=std::stoi(text,&n); check(n==std::string(text).size(),"Invalid integer"); return v; }
struct Event { std::uint64_t sample=0; double hz=220; std::array<double,3> shifts{}; };
struct Packet { int voice=0; std::uint64_t first=0, wall=0; int count=0; };
struct Control { int voice=0; std::int64_t source=0; std::uint64_t wall=0,request=0,frameBegin=0,frameEnd=0,frameAvailable=0; double desired=0,shift=0,hz=0; bool voiced=false; };
struct StateApplication { std::uint64_t request=0,available=0; std::array<int,3> slots{}; };
struct Capture
{
    std::array<std::vector<float>,3> output;
    std::vector<Packet> packets;
    std::vector<Control> controls;
    std::vector<PitchFrame> pitchFrames;
    std::vector<std::size_t> allocations;
    std::vector<StateApplication> states;
    std::array<std::uint64_t,3> nonfinite{};
    std::array<std::int64_t,3> firstNonfinite{-1,-1,-1};
    std::array<std::uint64_t,3> inputHash{14695981039346656037ull,14695981039346656037ull,14695981039346656037ull};
    std::array<std::uint64_t,3> controlHash{14695981039346656037ull,14695981039346656037ull,14695981039346656037ull};
    std::size_t finishAllocations=0;
};
void drain(engines::Engine& engine,Capture& c,int voice,std::uint64_t wall)
{
    std::array<float,1024> scratch{}; unsigned calls=0;
    while(engine.available()>0)
    {
        check(++calls<=128,"Unbounded retrieval");
        const int requested=std::min(engine.available(),static_cast<int>(scratch.size()));
        const int n=engine.retrieve(scratch.data(),requested); check(n>0 && n<=requested,"Invalid retrieval");
        c.packets.push_back({voice,c.output[voice].size(),wall,n});
        for(int i=0;i<n;++i)
        {
            if(!std::isfinite(scratch[i]))
            {
                ++c.nonfinite[voice];
                if(c.firstNonfinite[voice]<0) c.firstNonfinite[voice]=static_cast<std::int64_t>(c.output[voice].size());
            }
            c.output[voice].push_back(scratch[i]); // Preserve invalid raw evidence; never audition/install.
        }
    }
}
// Every engine is a newly constructed graph. Finalization is terminal; there is
// deliberately no start() method capable of restarting a finalized native stream.
using Voices=std::array<std::unique_ptr<engines::Engine>,3>;
Capture render(engines::Config config,const std::vector<float>& input,const std::vector<Event>& events,int hold,int mode,Voices* existing=nullptr,bool finalize=true)
{
    const bool trailing=mode==1,replay=mode==2;
    Capture result;
    for(auto& stem:result.output) stem.reserve(input.size()*2+131072);
    result.packets.reserve(input.size()/8+4096); result.controls.reserve(input.size()/8+4096);
    result.allocations.reserve(input.size()/32+4096); result.pitchFrames.reserve(input.size()/128+16);
    result.states.reserve(events.size());
    Voices fresh;
    auto& voices=existing?*existing:fresh;
    if(!existing) for(auto& voice:voices) voice=engines::create(config,1,replay?200:events.front().hz);
    const auto info=voices[0]->info(); check(info.quantum>0 && info.quantum<=512,"Invalid quantum");
    std::array<float,512> zero{};
    for(int v=0;v<3;++v) for(int left=info.startPad;left>0;)
    { const int n=std::min(left,info.quantum); voices[v]->process(zero.data(),n); drain(*voices[v],result,v,0); left-=n; }
    PitchTracker tracker; tracker.prepare(config.rate);
    HarmonySelector state; HarmonyConfig musical; musical.midiMode=true; state.configure(musical);
    std::array<int,3> oldNotes{-1,-1,-1}; std::size_t stateEvent=0;
    PitchFrame frame; std::size_t applied=0,received=0; std::uint64_t ingested=0;
    std::array<double,3> shift{};
    for(std::size_t begin=0;begin<input.size();begin+=info.quantum)
    {
        const int n=static_cast<int>(std::min(input.size()-begin,static_cast<std::size_t>(info.quantum)));
        const auto wall=begin+n+hold; const auto source=static_cast<std::int64_t>(begin)-info.controlLag;
        audit::begin();
        while(ingested<std::min<std::uint64_t>(wall,input.size()))
        {
            while(!replay && stateEvent<events.size() && events[stateEvent].sample==ingested)
            {
                const auto& e=events[stateEvent++];
                for(int note:oldNotes) if(note>=0) { const std::uint8_t bytes[]{0x80,static_cast<std::uint8_t>(note),0}; state.midi(bytes,3); }
                for(int v=0;v<3;++v)
                {
                    const int note=static_cast<int>(std::round(69+12*std::log2(e.hz/440)+e.shifts[v])); oldNotes[v]=note;
                    check(note>=0 && note<=127,"Diagnostic MIDI range");
                    const std::uint8_t bytes[]{0x90,static_cast<std::uint8_t>(note),100}; state.midi(bytes,3);
                }
                result.states.push_back({e.sample,ingested+1,state.midiSlots()});
            }
            if(trailing && tracker.push(input[ingested])) result.pitchFrames.push_back(tracker.frame());
            ++ingested;
        }
        while(received+1<events.size() && events[received+1].sample<wall) ++received;
        while(applied+1<=received && events[applied+1].sample<=(replay?begin:static_cast<std::uint64_t>(std::max<std::int64_t>(0,source)))) ++applied;
        if(trailing)
        {
            // One explicit alternative: newest AVAILABLE trailing frame whose
            // support ends no later than the engine's processing-source time.
            // This is a causal trailing estimate, not oracle instantaneous F0.
            for(auto it=result.pitchFrames.rbegin();it!=result.pitchFrames.rend();++it)
                if(source>=0 && it->end<=static_cast<std::uint64_t>(source)+1) { frame=*it; break; }
        }
        const auto& event=events[applied];
        for(int v=0;v<3;++v)
        {
            const bool voiced=replay?event.hz>0:source>=0 && (!trailing || frame.voiced);
            const double hz=trailing?frame.hz:event.hz;
            const double sourceMidi=hz>0?69+12*std::log2(hz/440):0;
            const double oracleMidi=event.hz>0?69+12*std::log2(event.hz/440):0;
            double desired=event.shifts[v];
            // Prescribed absolute targets are identical across oracle/trailing.
            if(trailing && voiced) desired=oracleMidi+event.shifts[v]-sourceMidi;
            const bool valid=voiced && desired>=-24.000001 && desired<=24.000001;
            if(replay) shift[v]=desired;
            else if(valid) shift[v]+=std::clamp(std::clamp(desired,-24.0,24.0)-shift[v],-2400.0*n/config.rate,2400.0*n/config.rate);
            voices[v]->control(std::exp2(shift[v]/12),valid?hz:0);
            result.controls.push_back({v,source,wall,event.sample,frame.begin,frame.end,frame.available,desired,shift[v],hz,valid});
            for(int i=0;i<n;++i) result.inputHash[v]=(result.inputHash[v]^std::bit_cast<std::uint32_t>(input[begin+i]))*1099511628211ull;
            for(double value:{shift[v],valid?hz:0}) result.controlHash[v]=(result.controlHash[v]^std::bit_cast<std::uint64_t>(value))*1099511628211ull;
            voices[v]->process(input.data()+begin,n); drain(*voices[v],result,v,wall);
        }
        result.allocations.push_back(audit::end());
    }
    audit::begin();
    if(finalize) for(int v=0;v<3;++v) { voices[v]->finish(); drain(*voices[v],result,v,input.size()+hold); }
    result.finishAllocations=audit::end(); return result;
}
std::vector<Event> readEvents(const char* path,std::size_t frames,bool replay)
{
    std::ifstream in(path); check(in.good(),"Cannot read events"); std::vector<Event> events; std::string line;
    while(std::getline(in,line))
    {
        std::istringstream row(line); Event e;
        check(static_cast<bool>(row>>e.sample>>e.hz>>e.shifts[0]>>e.shifts[1]>>e.shifts[2]),"Malformed event");
        std::string extra; check(!(row>>extra) && e.sample<frames && std::isfinite(e.hz) && ((replay && e.hz==0) || (e.hz>=82.4 && e.hz<=1046.6)),"Invalid event bounds");
        check(events.empty()?e.sample==0:e.sample>events.back().sample,"Invalid event order");
        for(double shift:e.shifts) check(std::isfinite(shift) && shift>=-24 && shift<=24,"Invalid shift");
        events.push_back(e);
    }
    check(!events.empty(),"No initial event"); return events;
}
void selfTest()
{
    if(audit::available) check(audit::selfTest(),"Allocation interposition self test failed");
    HarmonySelector selector; HarmonyConfig config; config.midiMode=true; selector.configure(config);
    const std::array<std::uint8_t,3> notes{52,64,69};
    for(auto note:notes) { const std::uint8_t bytes[]{0x90,note,100}; selector.midi(bytes,3); }
    check(selector.midiKnown() && selector.midiSlots()==std::array<int,3>{52,64,69},"Actual MIDI state application failed");
    engines::Config engine;
    if(std::string(ARCHITECTURE_BACKEND)=="rubberband") engine.window=1;
    else { engine.window=256; engine.hop=32; }
    const auto fresh=[&] { return engines::create(engine,1,220); };
    auto a=fresh(); auto b=fresh(); check(a.get()!=b.get(),"Shared engine states");
    std::cout<<"Allocation controls, MIDI-state application and independent construction passed; render instances are single-use\n";
}
}
int main(int argc,char** argv)
{
    try
    {
        if(argc==2 && std::string(argv[1])=="--self-test") { selfTest(); return 0; }
        check(argc==11,"Usage: rate window hop hold events prefix warm trace trailing source-f32");
        const engines::Config config{integer(argv[1]),integer(argv[2]),integer(argv[3])};
        const int hold=integer(argv[4]),warm=integer(argv[7]),traceStacks=integer(argv[8]),trailing=integer(argv[9]);
        check(hold>=0 && hold<=4800 && warm>=0 && warm<=2 && (traceStacks==0 || traceStacks==1) && trailing>=0 && trailing<=2,"Invalid diagnostic option");
        std::ifstream in(argv[10],std::ios::binary|std::ios::ate); check(in.good(),"Missing source");
        auto bytes=in.tellg(); check(bytes>0 && bytes%4==0 && bytes<=48000*30*4,"Invalid source size"); in.seekg(0);
        std::vector<float> input(static_cast<std::size_t>(bytes)/4); in.read(reinterpret_cast<char*>(input.data()),bytes); check(in.good(),"Source read failed");
        for(float x:input) check(std::isfinite(x),"Nonfinite input");
        const auto events=readEvents(argv[5],input.size(),trailing==2);
        if(audit::available) check(audit::selfTest(),"Audit controls failed");
        trace::enable(traceStacks!=0);
        // Warm EXACTLY the same full changing-ratio workload, then destroy/rebuild.
        // This tests process-wide initialization, not reusing a contaminated stream.
        if(warm==1) { trace::enable(false); render(config,input,events,hold,trailing); trace::enable(traceStacks!=0); }
        Voices primed;
        if(warm==2)
        {
            // One bounded stopped-initialization test: exact workload on the same
            // instances, reset before finalization, then repeat EVENTFUL audio.
            // This is not a claim that arbitrary future ratios can be prewarmed.
            trace::enable(false);
            for(auto& voice:primed) voice=engines::create(config,1,events.front().hz);
            render(config,input,events,hold,trailing,&primed,false);
            for(auto& voice:primed) voice->reset(1,events.front().hz);
            trace::enable(traceStacks!=0);
        }
        const auto result=render(config,input,events,hold,trailing,warm==2?&primed:nullptr);
        const std::string prefix=argv[6];
        for(int v=0;v<3;++v) { std::ofstream out(prefix+"-voice"+std::to_string(v)+".f32",std::ios::binary); out.write(reinterpret_cast<const char*>(result.output[v].data()),result.output[v].size()*4); check(out.good(),"Stem write failed"); }
        std::ofstream packets(prefix+"-packets.csv"); packets<<"voice,first,wall,count\n";
        for(const auto& p:result.packets) packets<<p.voice<<','<<p.first<<','<<p.wall<<','<<p.count<<'\n';
        std::ofstream controls(prefix+"-controls.csv"); controls<<std::setprecision(17)<<"voice,source,wall,request,frame_begin,frame_end,frame_available,desired,shift,hz,voiced\n";
        for(const auto& c:result.controls) controls<<c.voice<<','<<c.source<<','<<c.wall<<','<<c.request<<','<<c.frameBegin<<','<<c.frameEnd<<','<<c.frameAvailable<<','<<c.desired<<','<<c.shift<<','<<c.hz<<','<<c.voiced<<'\n';
        std::ofstream frames(prefix+"-pitch.csv"); frames<<std::setprecision(17)<<"begin,end,available,hz,confidence,voiced\n";
        for(const auto& f:result.pitchFrames) frames<<f.begin<<','<<f.end<<','<<f.available<<','<<f.hz<<','<<f.confidence<<','<<f.voiced<<'\n';
        std::ofstream states(prefix+"-state.csv"); states<<"request,available,slot0,slot1,slot2\n";
        for(const auto& s:result.states) states<<s.request<<','<<s.available<<','<<s.slots[0]<<','<<s.slots[1]<<','<<s.slots[2]<<'\n';
        std::ofstream allocations(prefix+"-allocations.csv"); allocations<<"quantum,calls\n";
        for(std::size_t i=0;i<result.allocations.size();++i) allocations<<i<<','<<result.allocations[i]<<'\n';
        std::ofstream stacks(prefix+"-stacks.csv"); trace::write(stacks);
        auto engine=engines::create(config,1,events.front().hz); const auto info=engine->info();
        std::ofstream report(prefix+".json"); report<<"{\"identity\":\""<<ARCHITECTURE_IDENTITY<<"\",\"build\":\""<<ARCHITECTURE_BUILD<<"\",\"sanitizer\":\""<<ARCHITECTURE_SANITIZER
            <<"\",\"backend\":\""<<ARCHITECTURE_BACKEND<<"\",\"audit_available\":"<<(audit::available?"true":"false")<<",\"quantum\":"<<info.quantum<<",\"control_lag\":"<<info.controlLag
            <<",\"offset\":"<<info.nominalOffset()<<",\"pad\":"<<info.startPad<<",\"trim\":"<<info.startTrim<<",\"hold\":"<<hold<<",\"warm\":"<<warm<<",\"trace\":"<<traceStacks<<",\"trailing\":"<<trailing
            <<",\"frames\":"<<input.size()<<",\"finish_allocations\":"<<result.finishAllocations<<",\"voices\":[";
        for(int v=0;v<3;++v) { if(v) report<<','; report<<"{\"frames\":"<<result.output[v].size()<<",\"nonfinite\":"<<result.nonfinite[v]<<",\"first_nonfinite\":"<<result.firstNonfinite[v]
            <<",\"input_hash\":\""<<result.inputHash[v]<<"\",\"control_hash\":\""<<result.controlHash[v]<<"\"}"; }
        report<<"]}\n";
        check(report.good() && controls.good() && packets.good() && frames.good() && states.good() && stacks.good() && allocations.good(),"Evidence write failed");
    }
    catch(const std::exception& e) { audit::end(); std::cerr<<e.what()<<'\n'; return 1; }
    catch(const char* e) { audit::end(); std::cerr<<e<<'\n'; return 1; }
}
