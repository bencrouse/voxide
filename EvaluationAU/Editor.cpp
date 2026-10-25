#include "Processor.h"

namespace voxide::evaluation
{
namespace
{
class Editor final : public juce::AudioProcessorEditor,private juce::Timer
{
public:
    explicit Editor(Processor& p) : AudioProcessorEditor(p),owner(p),parameters(p)
    {
        setWantsKeyboardFocus(false);
        title.setText("voxide Studio Eval — experimental",juce::dontSendNotification);
        info.setText("100 ms • main input channel 1 • real-time playback only\nThree voices: +2 / +4 scale steps / octave. Provide headroom.",juce::dontSendNotification);
        warning.setText("Unqualified pitch/timing. Offline bounce outputs delayed lead only.",juce::dontSendNotification);
        restart.setButtonText("Restart harmonies"); restart.onClick=[this] { owner.requestRestart(); };
        for (auto* c:std::array<juce::Component*,6>{&title,&info,&warning,&statusLabel,&restart,&parameters}) addAndMakeVisible(c);
        title.setFont(juce::FontOptions(18.f));
        warning.setColour(juce::Label::textColourId,juce::Colours::orange);
        setSize(540,410); startTimerHz(10); timerCallback();
    }
    ~Editor() override { stopTimer(); }
    void paint(juce::Graphics& g) override { g.fillAll(findColour(juce::ResizableWindow::backgroundColourId)); }
    void resized() override
    {
        title.setBounds(12,8,getWidth()-24,28); info.setBounds(12,38,getWidth()-24,46);
        warning.setBounds(12,88,getWidth()-24,34); parameters.setBounds(12,128,getWidth()-24,182);
        statusLabel.setBounds(12,316,getWidth()-24,44); restart.setBounds(12,366,180,28);
    }
private:
    void timerCallback() override
    {
        const auto s=owner.status(); juce::String text;
        switch (s.status)
        {
            case Session::Status::ready:text="Running — "+juce::String(s.hz,1)+" Hz; active voices "+juce::String(juce::countNumberOfBits(s.active))+"/3";break;
            case Session::Status::preparing:text="Preparing fresh workers — harmonies muted";break;
            case Session::Status::failed:text="Delivery fault — harmonies muted. Restart or re-prepare.";break;
            case Session::Status::unsupportedRate:text="Unsupported sample rate — use 44.1 or 48 kHz; lead only";break;
            case Session::Status::offlineUnsupported:text="Offline bounce unsupported — delayed lead only; use real-time playback";break;
        }
        statusLabel.setText(text,juce::dontSendNotification);
    }
    Processor& owner;
    juce::Label title,info,warning,statusLabel;
    juce::TextButton restart;
    juce::GenericAudioProcessorEditor parameters;
};
}
juce::AudioProcessorEditor* Processor::createEditor() { return new Editor(*this); }
}
