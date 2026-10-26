#pragma once
#include "PluginProcessor.h"

namespace voxide
{
class ProcessorTestAccess
{
public:
    // Render owner or stopped/joined reads, never UI access.
    static std::array<float,5> selection(const Processor& p)
    {
        const auto& s=p.renderedSettings;
        return {static_cast<float>(s.source),static_cast<float>(s.harmony.root),static_cast<float>(s.harmony.scale),s.originalGain,s.voiceGain[0]};
    }
    static unsigned generation(const Processor& p) { return p.stateGeneration.load(std::memory_order_acquire); }
    static const void* graph(const Processor& p) { return p.session?p.session->graphForTest():nullptr; }
    static bool rebuildFailed(const Processor& p) { return p.session && p.session->rebuildFailedForTest(); }
    static bool spareReady(const Processor& p) { return p.session && p.session->spareReadyForTest(); }
    static std::uint64_t spareWaitCalls(const Processor& p) { return p.session?p.session->spareWaitCallsForTest():0; }
};
}
