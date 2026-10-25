// Synthetic-only diagnosis. Does not modify the product wrapper or pinned engine.
#include "../EngineEvaluation/EngineAdapter.h"
#include "../Source/Tests/AllocationAudit.h"
#include "../ArchitectureEvaluation/TraceAllocations.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
using namespace voxide;
constexpr int quantum=128;
constexpr double pi=3.14159265358979323846;
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
std::uint64_t hash(std::uint64_t value, std::uint64_t word) { return (value^word)*1099511628211ull; }
struct Capture
{
    std::array<std::vector<float>,3> output;
    std::array<float,1024> scratch {};
    void drain(engines::Engine& engine, int voice)
    {
        int calls=0;
        while (engine.available()>0)
        {
            require(++calls<=128,"Unbounded retrieval");
            const int requested=std::min(engine.available(),static_cast<int>(scratch.size()));
            const int n=engine.retrieve(scratch.data(),requested);
            require(n>0 && n<=requested,"Invalid retrieval");
            if (voice<0) continue;
            auto& dest=output[static_cast<std::size_t>(voice)];
            require(dest.size()+static_cast<unsigned>(n)<=dest.capacity(),"Capture capacity exceeded");
            for (int i=0;i<n;++i) dest.push_back(scratch[i]); // Retain invalid raw evidence too; Python rejects it.
        }
    }
};
struct DrainControl final : engines::Engine
{
    int remaining=3;
    engines::Info info() const noexcept override { return {}; }
    void control(double,double) override {}
    void process(const float*,int) override {}
    int available() const override { return remaining; }
    int retrieve(float* destination,int maximum) override
    {
        require(maximum>0 && maximum<=remaining,"Probe requested more output than available");
        std::fill_n(destination,maximum,.01f); remaining-=maximum; return maximum;
    }
    void finish() override {}
    void reset(double,double) override { remaining=3; }
};
void raw(const std::string& name, const std::vector<float>& values)
{
    std::ofstream out(name,std::ios::binary);
    out.write(reinterpret_cast<const char*>(values.data()),static_cast<std::streamsize>(values.size()*sizeof(float)));
    require(out.good(),"Raw evidence write failed");
}
}
int main(int argc, char** argv)
{
    try
    {
        if (argc==2 && std::string(argv[1])=="--identity")
        { std::cout<<ALLOCATION_DIAGNOSIS_IDENTITY<<'\n'; return 0; }
        if (argc==2 && std::string(argv[1])=="--self-test")
        {
            audit::begin(); void* volatile p=std::malloc(17); const auto calls=audit::end();
            std::free(p); require(calls>0,"Allocation positive control not detected");
            Capture capture; capture.output[0].reserve(3); DrainControl fake;
            capture.drain(fake,0); require(capture.output[0].size()==3 && fake.available()==0,"Drain positive control failed");
            std::cout<<"Allocation and bounded-drain controls passed; no native engine capture\n"; return 0;
        }
        require(argc==5,"Use rate static|changing fresh|silent NEW-output-directory");
        const std::string rateText=argv[1], workload=argv[2], preparation=argv[3];
        require(rateText=="44100" || rateText=="48000","Unsupported rate");
        const int rate=std::stoi(rateText);
        require(workload=="static" || workload=="changing","Unsupported workload");
        require(preparation=="fresh" || preparation=="silent","Unsupported preparation");
        const std::filesystem::path directory=argv[4];
        require(std::filesystem::create_directory(directory),"Output must be a new directory");
        const auto prefix=directory.string()+"/";
        const int primary=rate*3,total=rate*18/5;
        const double hz=440*std::exp2((40.-69)/12);
        std::vector<float> input(static_cast<std::size_t>(total));
        for (int i=0;i<primary;++i)
        {
            double sample=0;
            for (int h=1;h<=6;++h) sample+=.04/h*std::sin(2*pi*h*hz*i/rate);
            input[static_cast<std::size_t>(i)]=static_cast<float>(sample);
        }
        Capture capture;
        for (auto& voice:capture.output) voice.reserve(static_cast<std::size_t>(total)*2+131072);
        std::ofstream counts(prefix+"allocations.csv"),controls(prefix+"controls.csv");
        require(counts.good() && controls.good(),"Evidence file open failed");
        counts<<"stage,source,voice,calls\n";
        controls<<std::setprecision(17)<<"source,count,voice,shift,ratio\n";
        std::array<std::unique_ptr<engines::Engine>,3> voices;
        audit::begin();
        for (auto& voice:voices) voice=engines::create({rate,1,quantum},1,hz);
        auto calls=audit::end(); counts<<"construct,0,-1,"<<calls<<'\n';
        std::array<float,quantum> zero {};
        if (preparation=="silent")
        {
            audit::begin();
            for (double ratio:{.5,95999./96000,95998./95999,.5,2.,1.})
                for (auto& voice:voices)
                {
                    voice->control(ratio,hz);
                    for (int n=0;n<(rate+4*quantum-1)/(4*quantum);++n)
                    { voice->process(zero.data(),quantum); capture.drain(*voice,-1); }
                }
            calls=audit::end(); counts<<"stopped_silence,0,-1,"<<calls<<'\n';
            audit::begin(); for (auto& voice:voices) voice->reset(1,hz);
            calls=audit::end(); counts<<"stopped_reset,0,-1,"<<calls<<'\n';
        }
        const auto info=voices[0]->info();
        require(info.quantum==quantum && info.nativeVersion==3,"Unexpected engine metadata");
        trace::enable(true); // Diagnostic only: never use this run for timing claims.
        audit::begin();
        for (int v=0;v<3;++v) for (int left=info.startPad;left>0;)
        {
            const int n=std::min(left,quantum); voices[v]->process(zero.data(),n);
            capture.drain(*voices[v],v); left-=n;
        }
        calls=audit::end(); counts<<"stopped_pad,0,-1,"<<calls<<'\n';
        std::array<double,3> shift {};
        std::uint64_t inputHash=14695981039346656037ull,controlHash=inputHash;
        std::size_t callbackAllocations=0,finishAllocations=0;
        for (int begin=0;begin<total;begin+=quantum)
        {
            const int n=std::min(quantum,total-begin);
            std::array<double,3> targets {-12,7,12};
            if (workload=="changing")
            {
                if (begin>=2*rate) targets={-7,12,-12};
                else if (begin>=rate) targets={12,-12,4};
                for (auto& target:targets) if (std::abs(target)<12) target+=.35*std::sin(2*pi*5*begin/rate);
            }
            for (int i=0;i<n;++i) inputHash=hash(inputHash,std::bit_cast<std::uint32_t>(input[static_cast<std::size_t>(begin+i)]));
            for (int v=0;v<3;++v)
            {
                shift[v]+=std::clamp(targets[v]-shift[v],-2400.*n/rate,2400.*n/rate);
                const double ratio=std::exp2(shift[v]/12);
                controlHash=hash(controlHash,std::bit_cast<std::uint64_t>(ratio));
                audit::begin(); voices[v]->control(ratio,hz); calls=audit::end();
                callbackAllocations+=calls; counts<<"control,"<<begin<<','<<v<<','<<calls<<'\n';
                controls<<begin<<','<<n<<','<<v<<','<<shift[v]<<','<<ratio<<'\n';
                audit::begin(); voices[v]->process(input.data()+begin,n); calls=audit::end();
                callbackAllocations+=calls; counts<<"process,"<<begin<<','<<v<<','<<calls<<'\n';
                audit::begin(); capture.drain(*voices[v],v); calls=audit::end();
                callbackAllocations+=calls; counts<<"retrieve,"<<begin<<','<<v<<','<<calls<<'\n';
            }
        }
        for (int v=0;v<3;++v)
        {
            audit::begin(); voices[v]->finish(); capture.drain(*voices[v],v); calls=audit::end();
            finishAllocations+=calls; counts<<"finish,"<<total<<','<<v<<','<<calls<<'\n';
        }
        { std::ofstream stacks(prefix+"stacks.csv"); trace::write(stacks); require(stacks.good(),"Stack write failed"); }
        trace::enable(false);
        raw(prefix+"source.f32",input);
        for (int v=0;v<3;++v) raw(prefix+"voice"+std::to_string(v)+".f32",capture.output[v]);
        counts.flush(); controls.flush(); require(counts.good() && controls.good(),"CSV write failed");
        std::ofstream report(prefix+"native.json");
        report<<"{\"identity\":\""<<ALLOCATION_DIAGNOSIS_IDENTITY<<"\",\"rate\":"<<rate
              <<",\"workload\":\""<<workload<<"\",\"preparation\":\""<<preparation
              <<"\",\"frames\":"<<total<<",\"start_pad\":"<<info.startPad<<",\"start_trim\":"<<info.startTrim
              <<",\"input_hash\":\""<<inputHash<<"\",\"control_hash\":\""<<controlHash
              <<"\",\"callback_allocations\":"<<callbackAllocations<<",\"finish_allocations\":"<<finishAllocations
              <<",\"output_frames\":["<<capture.output[0].size()<<','<<capture.output[1].size()<<','<<capture.output[2].size()<<"]}\n";
        require(report.good(),"Report write failed"); return 0;
    }
    catch (const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
