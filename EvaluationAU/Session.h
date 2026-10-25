#pragma once
#include "../WorkerEvaluation/WorkerEngine.h"
#include <memory>

namespace voxide::evaluation
{
class SessionTestAccess;
// DSP-session ownership is restricted to one render owner. prepare/destruction
// require rendering stopped; reset requests are handled at callback boundaries.
class Session
{
public:
    using Factory=interaction::Processor::Factory;
    enum class Status { ready, preparing, failed, unsupportedRate, offlineUnsupported };
    struct Snapshot { Status status=Status::preparing; float hz=0; unsigned active=0; };
    Session(int rate,Factory);
    ~Session();
    Session(const Session&)=delete;
    Session& operator=(const Session&)=delete;
    void restart() noexcept;
    void begin(int key,int scale,bool offline) noexcept;
    float push(float input,bool bypassed,float wet) noexcept;
    Snapshot snapshot() const noexcept { return current; } // Render owner only.
private:
    struct Graph;
    static std::unique_ptr<engines::Engine> createWorker(engines::Config,double,double);
    static thread_local Graph* constructing;
    const int sampleRate;
    Factory factory;
    std::array<std::unique_ptr<Graph>,3> slots;
    Graph* active=nullptr; // Only the callback touches this pointer.
    std::atomic<Graph*> ready {nullptr};
    interaction::Queue<Graph*,8> retired;
    std::atomic<bool> stop {false}, rebuildFailed {false};
    std::thread builder;
    Snapshot current;
    bool needsRestart=false, wasOffline=false, failedClosed=false;
    int lastKey=-1,lastScale=-1;
    void buildLoop() noexcept;
    void drainTelemetry() noexcept;
    bool waitIdleForTest() const;
    friend class SessionTestAccess;
};
}
