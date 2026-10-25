#include "Session.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <stdexcept>

namespace voxide::studio
{
namespace
{
constexpr std::size_t capacity=65536;
double approach(double value,double target,double step) { return value+std::clamp(target-value,-step,step); }
struct PitchEvent { std::uint64_t source=0;PitchFrame frame; };
struct MusicEvent { std::uint64_t source=0;HarmonyConfig harmony; };
struct AudioFifo
{
    std::array<float,capacity> audio {};
    std::size_t read=0,write=0,count=0;
    std::uint64_t first=0;
    bool put(float value,std::uint64_t source) noexcept
    {
        if (count==capacity || (count && source!=first+count)) return false;
        if (!count) first=source;
        audio[write]=value;write=(write+1)%capacity;++count;return true;
    }
    bool get(std::uint64_t source,float& value) noexcept
    {
        if (!count || first!=source) return false;
        value=audio[read];read=(read+1)%capacity;--count;++first;return true;
    }
};
}
// Production-only scale/native/100 ms path extracted from the reviewed PR06B
// scheduling contract. Oracle, MIDI synthesis, alternate profiles and engines are
// deliberately absent. Historical evaluators remain byte-for-byte independent.
struct Session::Graph
{
    int rate,latency,analysis,fill=0;
    std::array<std::unique_ptr<Worker>,3> workers;
    std::array<float,capacity> source {};
    std::array<std::array<float,3>,capacity> weights {};
    std::array<AudioFifo,3> output;
    std::array<std::uint64_t,3> raw {},trim {};
    std::array<double,3> shifts {},gains {};
    std::array<float,128> block {};
    std::array<float,1024> scratch {};
    Queue<PitchEvent,512> pitches;
    Queue<MusicEvent,2048> music;
    PitchTracker tracker;
    HarmonySelector selector;
    PitchFrame pitch;
    HarmonyConfig lastConfig;
    TrackerVariant variant=TrackerVariant::multiCandidate;
    std::uint64_t wall=0;
    unsigned activeMask=0;
    bool configured=false,healthy=true;
    explicit Graph(int r,Factory factory) : rate(r),latency(r/10)
    {
        tracker.prepare(rate);analysis=tracker.supportSamples()/2+tracker.hopSamples();
        for (std::size_t v=0;v<3;++v)
        {
            workers[v]=std::make_unique<Worker>(rate,factory);const auto info=workers[v]->info();
            trim[v]=static_cast<unsigned>(info.trim);
            // Exactly the declared start-pad protocol, no preparation workaround.
            for (int remaining=info.pad;remaining>0;)
            { const int n=std::min(128,remaining);workers[v]->process(block.data(),n,1,200);drain(v);remaining-=n; }
        }
    }
    bool allHealthy() const noexcept
    { return healthy && std::all_of(workers.begin(),workers.end(),[](const auto& w){return w && w->healthy();}); }
    void configure(HarmonyConfig config,TrackerVariant selected) noexcept
    {
        config.midiMode=false;
        if (!configured) { variant=selected;tracker.prepare(rate,variant); }
        if (!configured || config!=lastConfig)
        {
            if (!music.push({wall,config})) healthy=false;
            lastConfig=config;configured=true;
        }
    }
    void drain(std::size_t v) noexcept
    {
        for (int calls=0;workers[v]->available()>0;++calls)
        {
            if (calls==64) { healthy=false;return; }
            const int n=workers[v]->retrieve(scratch.data(),static_cast<int>(scratch.size()));
            if (n<1) { healthy=false;return; }
            for (int i=0;i<n;++i)
            {
                if (trim[v]) { --trim[v];continue; }
                const auto at=raw[v]++;
                if ((wall>=static_cast<unsigned>(latency) && at<wall-static_cast<unsigned>(latency))
                    || !output[v].put(scratch[static_cast<std::size_t>(i)],at)) healthy=false;
            }
        }
    }
    void quantum(std::uint64_t processing) noexcept
    {
        PitchEvent nextPitch;
        while (pitches.peek(nextPitch) && nextPitch.source<=processing)
        { pitches.pop(nextPitch);pitch=nextPitch.frame;selector.pitch(pitch); }
        MusicEvent nextMusic;
        while (music.peek(nextMusic) && nextMusic.source<=processing)
        { music.pop(nextMusic);selector.configure(nextMusic.harmony); }
        const bool voiced=pitch.voiced && pitch.confidence>=.85 && pitch.hz>0;
        std::array<bool,3> enabled {};
        activeMask=0;
        for (std::size_t v=0;v<3;++v)
        {
            const auto target=selector.targets()[v];
            const double delta=target.midi-pitch.midi;
            enabled[v]=voiced && target.active && delta>=-12.000001 && delta<=12.000001;
            const double desired=enabled[v]?std::clamp(delta,-12.0,12.0):shifts[v];
            shifts[v]=approach(shifts[v],desired,2400.0*128/rate);
            workers[v]->process(block.data(),128,std::exp2(shifts[v]/12),voiced?pitch.hz:0);drain(v);
            if (enabled[v]) activeMask|=1u<<v;
        }
        for (int i=0;i<128;++i)
        {
            auto& gain=weights[(processing+static_cast<unsigned>(i))%capacity];
            for (std::size_t v=0;v<3;++v)
            { gains[v]=approach(gains[v],enabled[v]?1.0:0.0,1.0/(.010*rate));gain[v]=static_cast<float>(gains[v]); }
        }
    }
    std::array<float,3> push(float input) noexcept
    {
        source[wall%capacity]=input;
        if (tracker.push(input))
        {
            const auto frame=tracker.frame();
            if (!pitches.push({(frame.begin+frame.end)/2,frame})) healthy=false;
        }
        if (wall>=static_cast<unsigned>(analysis))
        {
            block[static_cast<std::size_t>(fill++)]=source[(wall-static_cast<unsigned>(analysis))%capacity];
            if (fill==128) { quantum(wall+1-static_cast<unsigned>(analysis)-128);fill=0; }
        }
        std::array<float,3> result {};
        if (wall>=static_cast<unsigned>(latency))
        {
            const auto at=wall-static_cast<unsigned>(latency);
            for (std::size_t v=0;v<3;++v)
            {
                float sample=0;
                if (!output[v].get(at,sample)) healthy=false;
                result[v]=weights[at%capacity][v]*sample;
                if (!std::isfinite(result[v])) healthy=false;
            }
        }
        ++wall;return result;
    }
};
Session::Session(int r,Factory f) : rate(r),factory(f)
{
    if ((r!=44100 && r!=48000) || !f) throw std::invalid_argument("Unsupported studio session");
    slots[0]=std::make_unique<Graph>(r,f);active=slots[0].get();
    slots[1]=std::make_unique<Graph>(r,f);ready.store(slots[1].get(),std::memory_order_release);
    builder=std::thread([this]{buildLoop();});
}
Session::~Session() { stop.store(true,std::memory_order_release);if (builder.joinable()) builder.join(); }
void Session::buildLoop() noexcept
{
    while (!stop.load(std::memory_order_acquire))
    {
        Graph* old=nullptr;
        while (retired.pop(old)) for (auto& slot:slots) if (slot.get()==old) { slot.reset();break; }
        if (!ready.load(std::memory_order_acquire) && !buildFailed.load(std::memory_order_relaxed))
        {
            try { for (auto& slot:slots) if (!slot) { slot=std::make_unique<Graph>(rate,factory);ready.store(slot.get(),std::memory_order_release);break; } }
            catch (...) { buildFailed.store(true,std::memory_order_release); }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}
void Session::begin(const HarmonyConfig& config,TrackerVariant variant,bool offline,bool midiMode) noexcept
{
    const bool suppressed=offline || midiMode;
    if (suppressed!=wasSuppressed || (active && active->configured && active->variant!=variant)) needsRestart=true;
    wasSuppressed=suppressed;
    if (needsRestart || !active)
    {
        auto* next=ready.exchange(nullptr,std::memory_order_acq_rel);auto* old=active;active=next;
        if (old && !retired.push(old)) { fail();return; }
        needsRestart=false;failed=false;current={};
    }
    if (offline) { current.status=Status::offlineUnsupported;current.active=0;return; }
    if (midiMode) { current.status=Status::midiUnsupported;current.active=0;return; }
    if (!active) { current.status=buildFailed.load(std::memory_order_acquire)?Status::failed:Status::preparing;return; }
    if (failed || !active->allHealthy()) { fail();return; }
    active->configure(config,variant);
    if (!active->allHealthy()) { fail();return; }
    current.status=Status::ready;
}
std::array<float,3> Session::push(float input) noexcept
{
    if (!active || failed || current.status!=Status::ready) return {};
    const auto result=active->push(input);
    if (!active->allHealthy()) { fail();return {}; }
    current.hz=static_cast<float>(active->pitch.hz);current.active=active->activeMask;return result;
}
bool Session::waitIdleForTest() const
{
    if (!active) return true;
    for (const auto& worker:active->workers) if (!worker->waitIdleForTest()) return false;
    return true;
}
}
