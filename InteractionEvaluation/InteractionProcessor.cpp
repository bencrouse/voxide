#include "InteractionProcessor.h"
#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace voxide::interaction
{
namespace
{
constexpr std::size_t capacity = 65536;
constexpr double low = 82.4068892282175, high = 1046.5022612023945;
double approach(double value, double target, double step) { return value + std::clamp(target-value,-step,step); }
template<class T> struct History
{
    std::array<T,capacity> data {};
    std::array<std::int64_t,capacity> tags;
    History() { tags.fill(-1); }
    void put(std::int64_t at, const T& value) { if (at >= 0) { data[static_cast<std::size_t>(at)%capacity]=value; tags[static_cast<std::size_t>(at)%capacity]=at; } }
    bool get(std::int64_t at, T& value) const
    {
        if (at < 0 || tags[static_cast<std::size_t>(at)%capacity] != at) return false;
        value=data[static_cast<std::size_t>(at)%capacity]; return true;
    }
};
struct MixState { std::array<float,3> gain {}; float voicedWeight = 0; };
struct PitchEvent { std::uint64_t source = 0; PitchFrame frame; };
bool validHarmony(const HarmonyConfig& h)
{
    if (h.root<0 || h.root>11 || h.scale<0 || h.scale>=static_cast<int>(scaleCatalog().size()) || h.customMask>4095) return false;
    for (std::size_t i=0;i<3;++i) if (h.degrees[i]<-11 || h.degrees[i]>11 || h.octaves[i]<-2 || h.octaves[i]>2) return false;
    return true;
}
void validate(const Settings& s)
{
    if ((s.engine.rate != 44100 && s.engine.rate != 48000)
        || static_cast<unsigned>(s.mode)>3 || static_cast<unsigned>(s.treatment)>1 || static_cast<unsigned>(s.profile)>1
        || (s.shiftLimit!=12 && s.shiftLimit!=24))
        throw std::invalid_argument("Unsupported interaction settings");
    if (!validHarmony(s.harmony)) throw std::invalid_argument("Invalid harmony settings");
}
}
bool Settings::operator==(const Settings& o) const noexcept
{
    return engine.rate==o.engine.rate && engine.window==o.engine.window && engine.hop==o.engine.hop
        && mode==o.mode && treatment==o.treatment && profile==o.profile && harmony==o.harmony
        && shiftLimit==o.shiftLimit && inactiveUncertain==o.inactiveUncertain;
}
struct Processor::State
{
    Settings config;
    std::atomic<bool> playing {false}, mailboxOverflow {false};
    Queue<Event,4096> mailbox;
    Queue<Telemetry,8192> telemetry;
    Queue<PitchEvent,512> pitches;
    Queue<Event,2048> music;
    History<float> source;
    History<MixState> mix;
    std::array<std::unique_ptr<engines::Engine>,3> engines;
    std::array<engines::Fifo<capacity>,3> audio;
    std::array<std::uint64_t,3> raw {}, trim {}, queuedBegin {};
    PitchTracker tracker;
    HarmonySelector selector;
    PitchFrame frame;
    std::array<double,3> targets {57,64,69}, shift {}, gains {};
    unsigned activeMask = 7;
    std::array<float,512> block {};
    std::array<float,1024> scratch {};
    std::uint64_t wall = 0, epoch = 0, lastAvailable = 0, lastPitchAnchor = 0, lastMusicSource = 0;
    std::uint64_t requested = 0, requestAvailable = 0;
    int requestKind = 0;
    int latency = 0, analysis = 0, quantum = 0, lag = 0, offset = 0, fill = 0;
    double voicedWeight = 0;
    bool failedClosed = false;
    bool finalized = false;
    Stats counts;

    State(Settings s, Factory factory) : config(s)
    {
        validate(s);
        config.harmony.midiMode = config.mode==Mode::midi;
        tracker.prepare(s.engine.rate);
        selector.configure(config.harmony);
        latency=static_cast<int>(std::floor(s.engine.rate*(s.profile==Profile::live?.015:.100)));
        analysis=s.mode==Mode::oraclePrescribed?0:tracker.supportSamples()/2+tracker.hopSamples();
        for (std::size_t v=0;v<3;++v)
        {
            engines[v]=factory(s.engine,1,200);
            const auto info=engines[v]->info();
            if (info.quantum<1 || info.quantum>512 || info.startPad<0 || info.startPad>32768 || info.startTrim<0 || info.startTrim>32768
                || info.nominalOffset()<0 || info.nominalOffset()>32768 || info.controlLag<0 || info.controlLag>32768)
                throw std::runtime_error("Engine metadata exceeds interaction capacities");
            if (v!=0 && (quantum!=info.quantum || lag!=info.controlLag || offset!=info.nominalOffset()))
                throw std::runtime_error("Independent engine clocks disagree");
            quantum=info.quantum; lag=info.controlLag; offset=info.nominalOffset(); trim[v]=static_cast<unsigned>(info.startTrim);
            for (int remaining=info.startPad;remaining>0;)
            {
                const int n=std::min(quantum,remaining); engines[v]->process(block.data(),n); drain(v); remaining-=n;
            }
        }
    }
    void log(Telemetry event)
    {
        event.epoch=epoch;
        if (!telemetry.push(event)) ++counts.telemetryDropped;
    }
    void panic()
    {
        selector.panic(); activeMask=0; failedClosed=true; ++counts.badEvents;
    }
    void drain(std::size_t v)
    {
        unsigned calls=0;
        while (engines[v]->available()>0)
        {
            if (++calls>64) throw std::runtime_error("Bounded interaction retrieval budget exceeded");
            const int requested=std::min(engines[v]->available(),static_cast<int>(scratch.size()));
            const int n=engines[v]->retrieve(scratch.data(),requested);
            if (n<1 || n>requested) throw std::runtime_error("Invalid native retrieval");
            const auto first=static_cast<std::int64_t>(raw[v])-offset;
            for (int i=0;i<n;++i)
            {
                const float value=scratch[static_cast<std::size_t>(i)];
                if (!std::isfinite(value)) throw std::runtime_error("Nonfinite native interaction output");
                if (trim[v]) { --trim[v]; continue; }
                const auto index=static_cast<std::int64_t>(raw[v]++)-offset;
                ++counts.nativeFrames[v];
                if (index<0) continue;
                const auto needed=wall>=static_cast<unsigned>(latency)?wall-static_cast<unsigned>(latency):0;
                if (static_cast<std::uint64_t>(index)<needed) { ++counts.lateSamples[v]; continue; }
                if (audio[v].size()==0) queuedBegin[v]=static_cast<std::uint64_t>(index);
                if (!audio[v].push(value)) ++counts.fifoOverflow;
            }
            Telemetry event; event.kind=Telemetry::Kind::output; event.wall=wall; event.voice=static_cast<int>(v);
            event.firstOutput=first; event.count=static_cast<int>(raw[v]-static_cast<std::uint64_t>(first+offset)); log(event);
        }
    }
    void enqueuePitch(PitchEvent event)
    {
        if (event.source<lastPitchAnchor || event.frame.available>wall+1 || event.frame.begin>event.frame.end || event.frame.end>event.frame.available
            || !std::isfinite(event.frame.hz) || event.frame.hz<0 || !std::isfinite(event.frame.confidence)
            || event.frame.confidence<0 || event.frame.confidence>1 || (event.frame.voiced && (!std::isfinite(event.frame.hz) || event.frame.hz<low*.997 || event.frame.hz>high*1.003)))
        { panic(); return; }
        lastPitchAnchor=event.source;
        if (!pitches.push(event)) panic();
    }
    void inputEvents()
    {
        if (mailboxOverflow.exchange(false)) panic();
        Event event;
        for (unsigned n=0;n<4096 && mailbox.peek(event) && event.available<=wall;++n)
        {
            mailbox.pop(event);
            if (event.available<lastAvailable || event.available<event.source) { panic(); continue; }
            lastAvailable=event.available;
            event.available=wall; // Actual render availability, including late producer delivery.
            Telemetry t; t.kind=Telemetry::Kind::request; t.wall=wall; t.requested=event.source; t.available=event.available;
            t.requestKind=static_cast<int>(event.kind); log(t);
            if (event.kind==Event::Kind::pitch)
            {
                if (config.mode==Mode::oraclePrescribed)
                {
                    event.pitch.available=event.available;
                    enqueuePitch({event.source,event.pitch});
                }
            }
            else
            {
                if (event.source<lastMusicSource) { panic(); continue; }
                lastMusicSource=event.source;
                if (!music.push(event)) panic();
            }
        }
    }
    void controls(std::int64_t processing)
    {
        if (processing<0) return;
        PitchEvent pitch;
        while (pitches.peek(pitch) && pitch.source<=static_cast<std::uint64_t>(processing))
        {
            pitches.pop(pitch); frame=pitch.frame;
            frame.midi=frame.hz>0?69+12*std::log2(frame.hz/440):0;
            selector.pitch(frame);
            if (pitch.source+static_cast<unsigned>(quantum)<=static_cast<std::uint64_t>(processing)) ++counts.lateControls;
        }
        Event event;
        while (music.peek(event) && event.source<=static_cast<std::uint64_t>(processing))
        {
            music.pop(event); requested=event.source; requestAvailable=event.available; requestKind=static_cast<int>(event.kind);
            if (event.source+static_cast<unsigned>(quantum)<=static_cast<std::uint64_t>(processing)) ++counts.lateControls;
            if (event.kind==Event::Kind::targets)
            {
                if (event.mask>7 || !std::all_of(event.targetMidi.begin(),event.targetMidi.end(),[](double value){return std::isfinite(value) && value>=0 && value<=127;})) { panic(); continue; }
                targets=event.targetMidi; activeMask=event.mask;
            }
            else if (event.kind==Event::Kind::midi) selector.midi(event.bytes.data(),3);
            else if (event.kind==Event::Kind::harmony)
            {
                if (!validHarmony(event.harmony)) { panic(); continue; }
                config.harmony=event.harmony; config.harmony.midiMode=config.mode==Mode::midi; selector.configure(config.harmony);
            }
        }
    }
    void processQuantum(std::int64_t begin)
    {
        const auto processing=begin-lag;
        controls(processing);
        const bool voiced=frame.voiced && frame.confidence>=.85 && frame.hz>0;
        std::array<bool,3> active {};
        std::array<double,3> desired {};
        for (std::size_t v=0;v<3;++v)
        {
            active[v]=(activeMask&(1u<<v))!=0;
            if (config.mode==Mode::midi) active[v]=selector.midiKnown() && selector.midiSlots()[v]>=0;
            if (config.mode==Mode::scale) active[v]=config.harmony.scale!=41 || config.harmony.customMask!=0;
            active[v]=active[v] && !failedClosed;
            desired[v]=shift[v];
            double target=targets[v];
            if (voiced)
            {
                if (config.mode==Mode::scale || config.mode==Mode::midi)
                {
                    const auto& selected=selector.targets()[v]; active[v]=selected.active && !failedClosed; target=selected.midi;
                }
                const double delta=target-frame.midi;
                if (delta < -config.shiftLimit-.000001 || delta > config.shiftLimit+.000001) { active[v]=false; ++counts.rejectedTargets; }
                else desired[v]=std::clamp(delta,-static_cast<double>(config.shiftLimit),static_cast<double>(config.shiftLimit));
            }
            if (config.inactiveUncertain && !voiced) active[v]=false;
            shift[v]=approach(shift[v],desired[v],2400.0*quantum/config.engine.rate);
            for (int i=0;i<quantum;++i) counts.inputHashes[v]=(counts.inputHashes[v]^std::bit_cast<std::uint32_t>(block[static_cast<std::size_t>(i)]))*1099511628211ull;
            for (double value : {shift[v],voiced?frame.hz:0.0}) counts.controlHashes[v]=(counts.controlHashes[v]^std::bit_cast<std::uint64_t>(value))*1099511628211ull;
            engines[v]->control(std::exp2(shift[v]/12),voiced?frame.hz:0);
            Telemetry t; t.wall=wall; t.source=processing; t.voice=static_cast<int>(v); t.hz=frame.hz; t.confidence=frame.confidence;
            t.frameBegin=frame.begin; t.frameEnd=frame.end; t.frameAvailable=frame.available; t.requested=requested; t.available=requestAvailable;
            t.requestKind=requestKind;
            t.targetMidi=target; t.requestedShift=desired[v]; t.appliedShift=shift[v]; t.voiced=voiced; t.active=active[v]; t.weight=voicedWeight; log(t);
            engines[v]->process(block.data(),quantum); drain(v);
        }
        // Post-engine policy is indexed by the SAME processing-source clock, not
        // by a later input/tracker frame or by the host callback's final sample.
        for (int i=0;i<quantum;++i)
        {
            voicedWeight=approach(voicedWeight,voiced?std::clamp((frame.confidence-.4)/.45,0.0,1.0):0.0,1.0/(.010*config.engine.rate));
            MixState weights; weights.voicedWeight=static_cast<float>(voicedWeight);
            for (std::size_t v=0;v<3;++v)
            {
                gains[v]=approach(gains[v],active[v]?1.0:0.0,1.0/(.010*config.engine.rate));
                weights.gain[v]=static_cast<float>(gains[v]);
            }
            mix.put(processing+i,weights);
        }
    }
    Output push(float input)
    {
        if (!playing.load(std::memory_order_acquire)) throw std::logic_error("Interaction render requires start");
        if (!std::isfinite(input)) { input=0; ++counts.invalidInput; }
        source.put(static_cast<std::int64_t>(wall),input); inputEvents();
        if (config.mode!=Mode::oraclePrescribed && tracker.push(input))
        {
            const auto f=tracker.frame(); enqueuePitch({(f.begin+f.end)/2,f});
        }
        if (wall>=static_cast<unsigned>(analysis))
        {
            float delayed=0;
            if (!source.get(static_cast<std::int64_t>(wall)-analysis,delayed)) throw std::runtime_error("Input history capacity exceeded");
            block[static_cast<std::size_t>(fill++)]=delayed;
            if (fill==quantum) { processQuantum(static_cast<std::int64_t>(wall)+1-analysis-quantum); fill=0; }
        }
        Output result; result.leadDirect=input;
        if (wall>=static_cast<unsigned>(latency))
        {
            const auto at=wall-static_cast<unsigned>(latency);
            if (!source.get(static_cast<std::int64_t>(at),result.leadAligned)) throw std::runtime_error("Lead history capacity exceeded");
            MixState weights;
            if (!mix.get(static_cast<std::int64_t>(at),weights)) ++counts.missingMetadata;
            for (std::size_t v=0;v<3;++v)
            {
                float discarded=0;
                while (audio[v].size()!=0 && queuedBegin[v]<at) { audio[v].pop(discarded); ++queuedBegin[v]; ++counts.lateSamples[v]; }
                if (audio[v].size()==0 || queuedBegin[v]!=at) ++counts.underflows[v];
                else { audio[v].pop(result.native[v]); ++queuedBegin[v]; }
                const float w=config.treatment==Treatment::shared?weights.voicedWeight:1.0f;
                result.voices[v]=weights.gain[v]*(w*result.native[v]+(1-w)*result.leadAligned/3.0f);
            }
        }
        const float wet=(result.voices[0]+result.voices[1]+result.voices[2])/3.0f;
        result.sumDirect=result.leadDirect+wet; result.sumAligned=result.leadAligned+wet;
        ++wall; return result;
    }
};
Processor::Processor(Settings s, Factory f) : factory(f), state(std::make_unique<State>(s,f)) {}
Processor::~Processor()=default;
bool Processor::configureStopped(Settings s)
{
    if (running()) return false;
    const auto epoch=state->epoch+1;
    auto next=std::make_unique<State>(s,factory); next->epoch=epoch; state=std::move(next); return true;
}
bool Processor::resetStopped()
{
    if (running()) return false;
    // Reconstruct a stopped graph rather than inheriting PR04's failed dynamic
    // native reset state. Allocation/cost belongs to stopped lifecycle, not render.
    return configureStopped(state->config);
}
void Processor::start()
{
    if (state->finalized) throw std::logic_error("Finalized graph requires stopped reset/reconfiguration before restart");
    state->playing.store(true,std::memory_order_release);
}
void Processor::stop()
{
    if (!running()) return;
    for (std::size_t v=0;v<3;++v)
    {
        state->engines[v]->finish(); state->drain(v);
        float value=0;
        while (state->audio[v].pop(value)) state->counts.unrenderedFinishPeak=std::max(state->counts.unrenderedFinishPeak,std::abs(value));
    }
    state->finalized=true;
    state->playing.store(false,std::memory_order_release);
}
Output Processor::push(float x) { return state->push(x); }
bool Processor::post(const Event& e) noexcept
{
    if (state->mailbox.push(e)) return true;
    state->mailboxOverflow.store(true,std::memory_order_release); return false;
}
bool Processor::readTelemetry(Telemetry& t) noexcept { return state->telemetry.pop(t); }
int Processor::latencySamples() const noexcept { return state->latency; }
int Processor::analysisDelaySamples() const noexcept { return state->analysis; }
bool Processor::running() const noexcept { return state->playing.load(std::memory_order_acquire); }
const Settings& Processor::settings() const noexcept { return state->config; }
const Stats& Processor::stats() const noexcept { return state->counts; }
}
