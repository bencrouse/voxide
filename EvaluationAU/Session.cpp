#include "Session.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace voxide::evaluation
{
struct Session::Graph
{
    std::array<worker::Engine*,3> workers {};
    unsigned count=0;
    Factory nativeFactory;
    std::unique_ptr<interaction::Processor> processor;
    std::uint64_t frame=0;
    Graph(int rate,Factory factory) : nativeFactory(factory)
    {
        struct Scope
        {
            explicit Scope(Graph* graph) { constructing=graph; }
            ~Scope() { constructing=nullptr; }
        } scope(this);
        interaction::Settings settings;
        settings.engine={rate,1,128}; settings.mode=interaction::Mode::scale;
        settings.profile=interaction::Profile::mix; settings.shiftLimit=12; settings.inactiveUncertain=true;
        processor=std::make_unique<interaction::Processor>(settings,createWorker);
        processor->start();
    }
    bool healthy() const noexcept
    { return std::all_of(workers.begin(),workers.end(),[](auto* e) { return e && e->healthy(); }); }
};
thread_local Session::Graph* Session::constructing=nullptr;
std::unique_ptr<engines::Engine> Session::createWorker(engines::Config c,double ratio,double hz)
{
    if (!constructing || constructing->count>=3) throw std::logic_error("Worker factory outside setup");
    auto engine=std::make_unique<worker::Engine>(c,ratio,hz,constructing->nativeFactory,worker::Engine::Options{});
    constructing->workers[constructing->count++]=engine.get();
    return engine;
}
Session::Session(int rate,Factory f) : sampleRate(rate),factory(f)
{
    if ((rate!=44100 && rate!=48000) || !factory) throw std::invalid_argument("Unsupported evaluation session");
    // A pristine spare avoids construction/joining on ordinary transport resets.
    slots[0]=std::make_unique<Graph>(rate,factory); active=slots[0].get();
    slots[1]=std::make_unique<Graph>(rate,factory); ready.store(slots[1].get(),std::memory_order_release);
    current.status=Status::ready;
    builder=std::thread([this] { buildLoop(); });
}
Session::~Session()
{
    stop.store(true,std::memory_order_release);
    if (builder.joinable()) builder.join();
    // All Graph/worker destruction happens here or on builder, never in push().
}
void Session::buildLoop() noexcept
{
    while (!stop.load(std::memory_order_acquire))
    {
        Graph* graph=nullptr;
        while (retired.pop(graph))
            for (auto& slot:slots) if (slot.get()==graph) { slot.reset(); break; }
        if (ready.load(std::memory_order_acquire)==nullptr && !rebuildFailed.load(std::memory_order_relaxed))
        {
            try
            {
                for (auto& slot:slots) if (!slot)
                {
                    slot=std::make_unique<Graph>(sampleRate,factory);
                    ready.store(slot.get(),std::memory_order_release); break;
                }
            }
            catch (...) { rebuildFailed.store(true,std::memory_order_release); }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}
void Session::restart() noexcept { needsRestart=true; }
void Session::fail() noexcept { failedClosed=true; current.status=Status::failed; current.active=0; }
bool Session::waitIdleForTest() const
{
    if (!active) return true;
    for (auto* engine:active->workers) if (!engine->waitIdle()) return false;
    return true;
}
void Session::begin(int key,int scale,bool offline) noexcept
{
    if (offline!=wasOffline) needsRestart=true;
    wasOffline=offline;
    if (needsRestart || !active)
    {
        auto* next=ready.exchange(nullptr,std::memory_order_acq_rel);
        auto* old=active; active=next;
        // Only relinquish ownership after the callback has stopped using old.
        if (old && !retired.push(old)) { failedClosed=true; current.status=Status::failed; return; }
        needsRestart=false; failedClosed=false; lastKey=lastScale=-1; current.hz=0; current.active=0;
    }
    if (offline) { current.status=Status::offlineUnsupported; current.active=0; return; }
    if (!active) { current.status=rebuildFailed.load(std::memory_order_acquire)?Status::failed:Status::preparing; return; }
    if (failedClosed || !active->healthy()) { failedClosed=true; current.status=Status::failed; current.active=0; return; }
    current.status=Status::ready;
    if (key!=lastKey || scale!=lastScale)
    {
        interaction::Event event; event.kind=interaction::Event::Kind::harmony;
        event.source=event.available=active->frame; event.harmony.root=key; event.harmony.scale=scale;
        if (!active->processor->post(event)) { failedClosed=true; current.status=Status::failed; return; }
        lastKey=key; lastScale=scale;
    }
}
void Session::drainTelemetry() noexcept
{
    interaction::Telemetry t;
    for (int i=0;i<8192 && active->processor->readTelemetry(t);++i)
        if (t.kind==interaction::Telemetry::Kind::control)
        {
            current.hz=static_cast<float>(t.hz);
            const unsigned bit=1u<<static_cast<unsigned>(t.voice);
            current.active=t.active?(current.active|bit):(current.active&~bit);
        }
}
float Session::push(float input,bool bypassed,float wet) noexcept
{
    if (current.status!=Status::ready || !active || failedClosed) return 0;
    try
    {
        const auto output=active->processor->push(input);
        ++active->frame;
        if (active->frame%128==0) drainTelemetry();
        const auto& stats=active->processor->stats();
        if (!active->healthy() || stats.badEvents || stats.telemetryDropped || stats.fifoOverflow || stats.missingMetadata
            || std::any_of(stats.underflows.begin(),stats.underflows.end(),[](auto n) { return n!=0; })
            || std::any_of(stats.lateSamples.begin(),stats.lateSamples.end(),[](auto n) { return n!=0; }))
        { failedClosed=true; current.status=Status::failed; current.active=0; return 0; }
        double sum=0;
        for (float voice:output.voices)
        {
            if (!std::isfinite(voice)) { fail(); return 0; }
            sum+=static_cast<double>(voice);
        }
        const double mixed=static_cast<double>(wet)*(sum/3.0);
        if (!std::isfinite(mixed) || std::abs(mixed)>std::numeric_limits<float>::max()) { fail(); return 0; }
        if (bypassed) return 0;
        return static_cast<float>(mixed);
    }
    catch (...) { failedClosed=true; current.status=Status::failed; current.active=0; return 0; }
}
}
