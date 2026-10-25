#include "Processor.h"
#include <bit>
#include <cmath>
#include <cstring>
#include <limits>

namespace voxide::evaluation
{
Processor::Processor(Session::Factory f) : AudioProcessor(BusesProperties()
    .withInput("Vocal input",juce::AudioChannelSet::mono(),true)
    .withOutput("Output",juce::AudioChannelSet::stereo(),true)),factory(f)
{
    key=new juce::AudioParameterChoice(juce::ParameterID{"evalKey",1},"Key",
        juce::StringArray{"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"},0);
    juce::StringArray names;
    for (const auto& s:scaleCatalog()) if (std::strcmp(s.id,"custom")!=0) names.add(s.name);
    scale=new juce::AudioParameterChoice(juce::ParameterID{"evalScale",1},"Scale (12-TET)",names,0);
    enabled=new juce::AudioParameterBool(juce::ParameterID{"evalHarmonies",1},"Harmonies",true);
    level=new juce::AudioParameterFloat(juce::ParameterID{"evalHarmonyDb",1},"Harmony level (dB)",-60.f,0.f,0.f);
    for (auto* p:std::array<juce::AudioProcessorParameter*,4>{key,scale,enabled,level}) addParameter(p);
}
Processor::~Processor() { releaseResources(); }
bool Processor::isBusesLayoutSupported(const BusesLayout& layout) const
{
    return layout.inputBuses.size()==1 && layout.outputBuses.size()==1
        && (layout.getMainInputChannelSet()==juce::AudioChannelSet::mono() || layout.getMainInputChannelSet()==juce::AudioChannelSet::stereo())
        && layout.getMainOutputChannelSet()==juce::AudioChannelSet::stereo();
}
void Processor::prepareToPlay(double sampleRate,int)
{
    releaseResources(); rate=sampleRate;
    const bool valid=std::isfinite(rate) && rate>0 && rate<=384000;
    const int latency=valid?static_cast<int>(std::floor(rate*.1)):0;
    leadDelay.assign(static_cast<std::size_t>(latency),0.f); leadPosition=0;
    setLatencySamples(latency);
    wetGain=enabled->get()?juce::Decibels::decibelsToGain(level->get()):0.f;
    renderedGeneration=restartGeneration.load(std::memory_order_acquire);
    renderedReset=resetGeneration.load(std::memory_order_acquire);
    lastOffline=false; lastPlaying=false; lastPositionKnown=false; lastBypassed=false; lastFrames=0;
    if (rate!=44100. && rate!=48000.) { renderStatus.store(Session::Status::unsupportedRate); return; }
    try { session=std::make_unique<Session>(static_cast<int>(rate),factory); renderStatus.store(Session::Status::ready); }
    catch (...) { session.reset(); renderStatus.store(Session::Status::failed); }
}
void Processor::releaseResources()
{
    session.reset(); // Host must have stopped/joined the render owner.
    pitchHz.store(0); activeVoices.store(0); renderStatus.store(Session::Status::preparing);
}
float Processor::delayed(float input) noexcept
{
    if (leadDelay.empty()) return input;
    const float result=leadDelay[leadPosition]; leadDelay[leadPosition]=input;
    if (++leadPosition==leadDelay.size()) leadPosition=0;
    return result;
}
void Processor::processBlock(juce::AudioBuffer<float>& b,juce::MidiBuffer& m) { render(b,m,false); }
void Processor::processBlockBypassed(juce::AudioBuffer<float>& b,juce::MidiBuffer& m) { render(b,m,true); }
void Processor::render(juce::AudioBuffer<float>& buffer,juce::MidiBuffer& midi,bool bypassed)
{
    juce::ScopedNoDenormals noDenormals;
    const bool offline=isNonRealtime();
    const unsigned generation=restartGeneration.load(std::memory_order_acquire);
    const bool harmonyRestart=generation!=renderedGeneration;
    const unsigned reset=resetGeneration.load(std::memory_order_acquire);
    const bool hostReset=reset!=renderedReset;
    // Pinned JUCE calls reset() when entering AU bypass. That transition must
    // preserve the dry delay; ordinary host resets still discard source history.
    bool discontinuity=offline!=lastOffline || (hostReset && bypassed==lastBypassed);
    bool receivedPosition=false;
    if (auto* head=getPlayHead()) if (const auto position=head->getPosition())
    {
        receivedPosition=true;
        const bool playing=position->getIsPlaying();
        const auto sample=position->getTimeInSamples();
        if (sample && lastPositionKnown)
        {
            const bool overflow=lastPosition>std::numeric_limits<std::int64_t>::max()-lastFrames;
            if (*sample<lastPosition || (playing && lastPlaying && (overflow || *sample!=lastPosition+lastFrames))) discontinuity=true;
        }
        // Stopped callbacks are a separate stream, even at a fixed position.
        // Neither stop nor resume may replay that stream into playback.
        if (lastFrames>0 && lastPlaying!=playing) discontinuity=true;
        lastPlaying=playing; lastPositionKnown=sample.hasValue();
        if (sample) lastPosition=*sample;
    }
    if (!receivedPosition) lastPositionKnown=false;
    lastFrames=buffer.getNumSamples(); lastOffline=offline; renderedGeneration=generation;
    renderedReset=reset; lastBypassed=bypassed;
    if (discontinuity)
    {
        std::fill(leadDelay.begin(),leadDelay.end(),0.f); leadPosition=0;
    }
    if (session && (discontinuity || harmonyRestart || hostReset)) session->restart();
    if (session) session->begin(key->getIndex(),scale->getIndex(),offline);
    const auto input=getBusBuffer(buffer,true,0);
    auto output=getBusBuffer(buffer,false,0);
    const auto* source=input.getNumChannels()>0?input.getReadPointer(0):nullptr;
    const float target=enabled->get()?juce::Decibels::decibelsToGain(level->get()):0.f;
    const float step=rate>0?static_cast<float>(1./(.01*rate)):1.f;
    for (int i=0;i<buffer.getNumSamples();++i)
    {
        float sample=source?source[i]:0.f;
        if (!std::isfinite(sample)) sample=0;
        wetGain+=std::clamp(target-wetGain,-step,step);
        const float lead=delayed(sample);
        const float wet=session?session->push(sample,bypassed,wetGain):0.f;
        const double mixed=static_cast<double>(lead)+wet;
        const bool valid=std::isfinite(mixed) && std::abs(mixed)<=std::numeric_limits<float>::max();
        if (!valid && session) session->fail();
        const float value=valid?static_cast<float>(mixed):lead;
        for (int channel=0;channel<output.getNumChannels();++channel) output.setSample(channel,i,value);
    }
    if (session)
    {
        const auto snapshot=session->snapshot();
        renderStatus.store(snapshot.status,std::memory_order_relaxed);
        pitchHz.store(snapshot.hz,std::memory_order_relaxed);
        activeVoices.store((bypassed || !enabled->get())?0:snapshot.active,std::memory_order_relaxed);
    }
    midi.clear();
}
Session::Snapshot Processor::status() const noexcept
{ return {renderStatus.load(std::memory_order_relaxed),pitchHz.load(std::memory_order_relaxed),activeVoices.load(std::memory_order_relaxed)}; }
void Processor::getStateInformation(juce::MemoryBlock& destination)
{
    constexpr char prefix[]="voxide-studio-eval-v1";
    destination.setSize(sizeof(prefix)+4*sizeof(float));
    std::memcpy(destination.getData(),prefix,sizeof(prefix));
    auto* bytes=static_cast<unsigned char*>(destination.getData())+sizeof(prefix);
    for (const auto* p:getParameters())
    {
        const auto bits=std::bit_cast<std::uint32_t>(p->getValue());
        for (unsigned i=0;i<4;++i) *bytes++=static_cast<unsigned char>(bits>>(i*8));
    }
}
void Processor::setStateInformation(const void* data,int size)
{
    constexpr char prefix[]="voxide-studio-eval-v1";
    if (!data || size!=static_cast<int>(sizeof(prefix)+4*sizeof(float)) || std::memcmp(data,prefix,sizeof(prefix))!=0) return;
    const auto* bytes=static_cast<const unsigned char*>(data)+sizeof(prefix);
    std::array<float,4> values {};
    for (auto& value:values)
    {
        std::uint32_t bits=0;
        for (unsigned i=0;i<4;++i) bits|=static_cast<std::uint32_t>(*bytes++)<<(i*8);
        value=std::bit_cast<float>(bits);
        if (!std::isfinite(value) || value<0 || value>1) return;
    }
    for (int i=0;i<4;++i) getParameters()[i]->setValueNotifyingHost(values[static_cast<std::size_t>(i)]);
    requestRestart();
}
}
