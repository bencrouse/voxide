#include "PluginProcessor.h"
#include "BuildInfo.h"

namespace voxide
{
namespace
{
juce::RangedAudioParameter& parameter(Processor& p,const juce::String& id)
{
    for (auto* base:p.getParameters())
        if (auto* ranged=dynamic_cast<juce::RangedAudioParameter*>(base);ranged && ranged->paramID==id) return *ranged;
    throw std::logic_error("Missing editor parameter");
}
class Choice final : public juce::Component
{
public:
    Choice(juce::AudioParameterChoice& p,const juce::String& name)
    {
        label.setText(name,juce::dontSendNotification);addAndMakeVisible(label);
        box.addItemList(p.choices,1);box.setTitle(name);box.setComponentID(p.paramID);
        box.setTooltip(name=="Vocal source"?"Select the bus explicitly. Channel 1 only; no silent-source fallback.":"Explicit selection; no automatic key detection.");
        addAndMakeVisible(box);
        attachment=std::make_unique<juce::ComboBoxParameterAttachment>(p,box);
    }
    void resized() override { auto r=getLocalBounds();label.setBounds(r.removeFromTop(22));box.setBounds(r.reduced(0,2)); }
private:
    juce::Label label;
    juce::ComboBox box;
    std::unique_ptr<juce::ComboBoxParameterAttachment> attachment;
};
class Level final : public juce::Component
{
public:
    Level(juce::RangedAudioParameter& p,const juce::String& name,const juce::String& help)
    {
        label.setText(name,juce::dontSendNotification);addAndMakeVisible(label);
        slider.setSliderStyle(juce::Slider::LinearHorizontal);slider.setTextBoxStyle(juce::Slider::TextBoxRight,false,72,26);
        slider.setTitle(name);slider.setComponentID(p.paramID);slider.setTooltip(help);slider.setWantsKeyboardFocus(true);
        addAndMakeVisible(slider);attachment=std::make_unique<juce::SliderParameterAttachment>(p,slider);
    }
    void resized() override { auto r=getLocalBounds();label.setBounds(r.removeFromTop(20));slider.setBounds(r); }
private:
    juce::Label label;
    juce::Slider slider;
    std::unique_ptr<juce::SliderParameterAttachment> attachment;
};
class Mix final : public juce::Component
{
public:
    explicit Mix(juce::RangedAudioParameter& p)
    {
        title.setText("Mix",juce::dontSendNotification);title.setFont(juce::FontOptions(18.f));
        hint.setText("Turn right for more harmony",juce::dontSendNotification);
        hint.setJustificationType(juce::Justification::centredRight);
        hint.setColour(juce::Label::textColourId,juce::Colour(0xffb5c4c9));
        dry.setText("Original",juce::dontSendNotification);wet.setText("Harmonies",juce::dontSendNotification);
        wet.setJustificationType(juce::Justification::centredRight);
        for (auto* label:{&title,&hint,&dry,&wet}) addAndMakeVisible(label);
        slider.setSliderStyle(juce::Slider::LinearHorizontal);slider.setTextBoxStyle(juce::Slider::TextBoxRight,false,76,28);
        slider.setTitle("Original / harmonies mix");slider.setComponentID(p.paramID);slider.setWantsKeyboardFocus(true);
        slider.setTooltip("0%: original only. 50%: existing blend. 100%: harmonies only.\nTurn right to reduce the original without changing voice trims. Smoothed over 10 ms; host bypass restores unity original.");
        slider.setColour(juce::Slider::thumbColourId,juce::Colour(0xff7bd5c4));
        slider.setColour(juce::Slider::trackColourId,juce::Colour(0xff7bd5c4));
        addAndMakeVisible(slider);attachment=std::make_unique<juce::SliderParameterAttachment>(p,slider);
    }
    void resized() override
    {
        const auto width=getWidth();title.setBounds(0,0,100,22);hint.setBounds(110,0,width-110,22);
        slider.setBounds(0,24,width,32);dry.setBounds(0,56,100,20);wet.setBounds(width-186,56,100,20);
    }
private:
    juce::Label title,hint,dry,wet;
    juce::Slider slider;
    std::unique_ptr<juce::SliderParameterAttachment> attachment;
};
class StudioEditor final : public juce::AudioProcessorEditor,private juce::Timer
{
public:
    explicit StudioEditor(Processor& p) : AudioProcessorEditor(p),owner(p)
    {
        setWantsKeyboardFocus(false);
        title.setText("voxide / studio",juce::dontSendNotification);title.setFont(juce::FontOptions(24.f));
        warning.setText("100 ms alignment | 44.1 / 48 kHz | playback + offline bounce\nFormal measured qualification deferred. MIDI synthesis unavailable.",juce::dontSendNotification);
        warning.setColour(juce::Label::textColourId,juce::Colours::orange);
        help.setText("Degree steps: 0 = unison; +2 = third in seven-note scales. Shifts beyond +/-12 semitones mute.",juce::dontSendNotification);
        for (auto* label:{&title,&warning,&help,&status}) addAndMakeVisible(label);
        mix=std::make_unique<Mix>(parameter(p,"harmonyMix"));addAndMakeVisible(mix.get());
        key=std::make_unique<Choice>(dynamic_cast<juce::AudioParameterChoice&>(parameter(p,"scaleRoot")),"Key");
        scale=std::make_unique<Choice>(dynamic_cast<juce::AudioParameterChoice&>(parameter(p,"scaleSet")),"Scale (12-TET)");
        source=std::make_unique<Choice>(p.sourceParameter(),"Vocal source");
        for (auto* control:{key.get(),scale.get(),source.get()}) addAndMakeVisible(control);
        for (std::size_t i=0;i<3;++i)
        {
            const auto suffix=juce::String(static_cast<int>(i+1));
            enabled[i].setButtonText("Voice "+suffix);enabled[i].setTitle("Voice "+suffix+" enabled");enabled[i].setComponentID("voiceEnabled"+suffix);
            enabled[i].setTooltip("Output-time enable, with a 10 ms gain ramp.");addAndMakeVisible(enabled[i]);
            buttons[i]=std::make_unique<juce::ButtonParameterAttachment>(parameter(p,"voiceEnabled"+suffix),enabled[i]);
            degree[i]=std::make_unique<Level>(parameter(p,"voiceDegree"+suffix),"Degree steps","Source-time scale steps; existing -11 to +11 range preserved. Out-of-range targets mute, never clamp musically.");
            octave[i]=std::make_unique<Level>(parameter(p,"voiceOctave"+suffix),"Octaves","Source-time octave offset; existing -2 to +2 range preserved. Final shifts must stay within +/-12 semitones.");
            level[i]=std::make_unique<Level>(parameter(p,"voiceLevel"+suffix),"Voice trim (dB)","Output-time voice trim, 10 ms ramp. The main Mix control sets the original/harmony balance. Each voice retains its one-third safety gain. -60 dB = silent.");
            for (auto* control:{degree[i].get(),octave[i].get(),level[i].get()}) addAndMakeVisible(control);
        }
        original=std::make_unique<Level>(parameter(p,"originalLevel"),"Original trim (dB)","Trim before the main Mix balance; no tuning. -60 dB = silent; host bypass restores unity original.");
        addAndMakeVisible(original.get());restart.setButtonText("Restart harmonies");restart.setTooltip("Recover harmony workers without clearing queued original audio.");
        restart.setComponentID("restartHarmonies");
        restart.onClick=[this]
        {
            auto& mode=parameter(owner,"harmonyMode");
            if (mode.getValue()>.5f) { mode.beginChangeGesture();mode.setValueNotifyingHost(0);mode.endChangeGesture(); }
            owner.requestRestart();
        };
        addAndMakeVisible(restart);
        capture.setComponentID("sessionCapture");capture.setButtonText("Log session metadata");
        capture.onClick=[this]
        {
            auto& log=owner.sessionLog();
            if (log.active()) log.stop();else log.start(juce::File(build::sessionDirectory),owner.instanceId());
            timerCallback();
        };
        addAndMakeVisible(capture);
        setResizable(true,true);setResizeLimits(720,680,1000,840);setSize(780,700);startTimerHz(10);timerCallback();
    }
    ~StudioEditor() override { stopTimer(); }
    void paint(juce::Graphics& g) override
    {
        g.fillAll(juce::Colour(0xff202329));g.setColour(juce::Colour(0xff3a3e46));
        for (int y:{268,346,424,502}) g.drawHorizontalLine(y,20.f,static_cast<float>(getWidth()-20));
    }
    void resized() override
    {
        const int width=getWidth()-40;
        title.setBounds(20,14,width-210,34);capture.setBounds(getWidth()-220,18,200,28);warning.setBounds(20,50,width,48);
        mix->setBounds(20,102,width,80);
        key->setBounds(20,194,110,62);scale->setBounds(142,194,width-342,62);source->setBounds(getWidth()-208,194,188,62);
        for (std::size_t i=0;i<3;++i)
        {
            const int y=278+static_cast<int>(i)*78;
            enabled[i].setBounds(20,y+22,92,32);
            const int available=width-104;
            degree[i]->setBounds(124,y,available/4,62);octave[i]->setBounds(134+available/4,y,available/4,62);
            level[i]->setBounds(144+available/2,y,available/2-20,62);
        }
        original->setBounds(20,514,width/2,62);help.setBounds(20,580,width,30);
        status.setBounds(20,614,width-202,56);restart.setBounds(getWidth()-202,626,182,32);
    }
private:
    void timerCallback() override
    {
        const auto snapshot=owner.studioStatus();juce::String text;
        switch (snapshot.status)
        {
            case studio::Status::ready:text="Ready";break;
            case studio::Status::preparing:text="Preparing workers - harmonies muted";break;
            case studio::Status::failed:text="Delivery fault - harmonies muted";break;
            case studio::Status::unsupportedRate:text="Unsupported rate - original only";break;
            case studio::Status::offlineUnsupported:text="Offline unsupported - original only";break;
            case studio::Status::midiUnsupported:text="Legacy MIDI mode - original only";break;
            case studio::Status::initializationFailed:text="Initialization failed - re-prepare plug-in";break;
        }
        const auto tick=owner.renderTick();
        const bool fresh=tick>0 && juce::Time::highResolutionTicksToSeconds(juce::Time::getHighResolutionTicks()-tick)<.5;
        text+=fresh?" | "+juce::String(snapshot.hz,1)+" Hz | "+juce::String(juce::countNumberOfBits(snapshot.active))+"/3 active":" | no current callback";
        auto& log=owner.sessionLog();
        capture.setButtonText(log.stopping()?"Finishing session log":log.active()?"Stop session log":"Log session metadata");capture.setEnabled(!log.stopping());
        capture.setTooltip("Explicit local metadata logging; no audio/MIDI recorded. Continues with editor closed. Stop before closing project.\n"+log.path()+"\n"+log.error());
        if (log.active()) text+=" | logging";else if (log.error().isNotEmpty()) text+=" | log failed";
        const auto peak=owner.inputPeak();text+="\nInput "+(peak>0?juce::String(juce::Decibels::gainToDecibels(peak),1):juce::String("-inf"))+" dBFS | provide headroom";
        status.setText(text,juce::dontSendNotification);
        const bool needsPreparation=snapshot.status==studio::Status::initializationFailed;
        restart.setEnabled(!needsPreparation);
        restart.setButtonText(needsPreparation?"Re-prepare required":snapshot.status==studio::Status::midiUnsupported?"Use scale harmonies":"Restart harmonies");
        restart.setTooltip(needsPreparation?"The recovery coordinator could not initialize. Stop rendering and re-prepare the plug-in in the host.":"Recover harmony workers without clearing queued original audio.");
    }
    Processor& owner;
    juce::Label title,warning,help,status;
    std::unique_ptr<Choice> key,scale,source;
    std::unique_ptr<Mix> mix;
    std::array<juce::ToggleButton,3> enabled;
    std::array<std::unique_ptr<Level>,3> degree,octave,level;
    std::unique_ptr<Level> original;
    juce::TextButton restart,capture;
    std::array<std::unique_ptr<juce::ButtonParameterAttachment>,3> buttons;
};
}
juce::AudioProcessorEditor* Processor::createEditor() { return new StudioEditor(*this); }
}
