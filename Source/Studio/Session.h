#pragma once
#include "Worker.h"
#include "HarmonySelector.h"
#include "PitchTracker.h"

namespace voxide::studio
{
enum class Status { preparing,ready,failed,unsupportedRate,offlineUnsupported,midiUnsupported,initializationFailed };
struct Snapshot { Status status=Status::preparing;float hz=0;unsigned active=0; };
// One render owner. prepare/release/destruction require it stopped/joined.
class Session
{
public:
    Session(int,Factory);
    ~Session();
    void restart(bool recover=false) noexcept
    {
        needsRestart=true;
        if (recover) recoveryRequested.fetch_add(1,std::memory_order_release);
    }
    void fail() noexcept { failed=true;current.status=Status::failed;current.active=0; }
    void begin(const HarmonyConfig&,TrackerVariant,bool offline,bool midiMode) noexcept;
    std::array<float,3> push(float) noexcept;
    Snapshot snapshot() const noexcept { return current; }
    bool waitIdleForTest() const;
    const void* graphForTest() const noexcept { return active; }
    bool rebuildFailedForTest() const noexcept { return buildFailed.load(std::memory_order_acquire); }
private:
    struct Graph;
    int rate;
    Factory factory;
    std::array<std::unique_ptr<Graph>,3> slots;
    Graph* active=nullptr;
    std::atomic<Graph*> ready {nullptr};
    Queue<Graph*,8> retired;
    std::atomic<bool> stop {false},buildFailed {false};
    std::atomic<unsigned> recoveryRequested {0};
    std::thread builder;
    bool needsRestart=false,failed=false,wasSuppressed=false;
    Snapshot current;
    void buildLoop() noexcept;
};
}
