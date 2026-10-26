#include "SessionLog.h"
#include "BuildInfo.h"
#include <CommonCrypto/CommonDigest.h>
#include <dlfcn.h>
#include <filesystem>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>

namespace voxide
{
namespace
{
void moduleAnchor() {}
juce::var object(std::initializer_list<std::pair<juce::Identifier,juce::var>> properties)
{
    auto result=std::make_unique<juce::DynamicObject>();
    for (const auto& [key,value]:properties) result->setProperty(key,value);
    return juce::var(result.release());
}
}
bool SessionLog::write(juce::var value)
{
    const auto text=juce::JSON::toString(value,true)+"\n";const auto* bytes=text.toRawUTF8();std::size_t at=0,size=text.getNumBytesAsUTF8();
    while (at<size)
    {
        const auto n=::write(file,bytes+at,size-at);
        if (n<0 && errno==EINTR) continue;
        if (n<=0) { fail("Session log write failed");return false; }
        at+=static_cast<std::size_t>(n);
    }
    return true;
}
void SessionLog::fail(const juce::String& why)
{
    failure=why;telemetry.stop();if (file>=0) ::close(file);file=-1;ending=false;
}
bool SessionLog::start(const juce::File& directory,const juce::String& instance)
{
    const std::lock_guard lock(mutex);
    if (active() || !telemetry.quiescent()) return false;
    failure.clear();
    try
    {
        const auto path=std::filesystem::path(directory.getFullPathName().toStdString());
        for (auto part=path;!part.empty();)
        {
            if (std::filesystem::is_symlink(part)) throw std::runtime_error("Refusing symlink log directory");
            const auto parent=part.parent_path();if (parent==part) break;part=parent;
        }
        std::filesystem::create_directories(path);
        destination=directory.getChildFile("session-"+juce::Uuid().toString()+".jsonl").getFullPathName();
        file=::open(destination.toRawUTF8(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
        if (file<0) throw std::runtime_error("Cannot create exclusive session log");
        // This module, not the host application's executable. Hash off render.
        Dl_info module {};if (!dladdr(reinterpret_cast<const void*>(&moduleAnchor),&module) || !module.dli_fname) throw std::runtime_error("Cannot identify loaded module");
        juce::MemoryBlock binary;const juce::File moduleFile(juce::String::fromUTF8(module.dli_fname));
        if (!moduleFile.loadFileAsData(binary) || binary.isEmpty() || binary.getSize()>std::numeric_limits<CC_LONG>::max()) throw std::runtime_error("Cannot hash loaded module file");
        unsigned char digest[CC_SHA256_DIGEST_LENGTH] {};CC_SHA256(binary.getData(),static_cast<CC_LONG>(binary.getSize()),digest);
        // Drain an aborted previous capture, but do not reuse it as new evidence.
        SessionSample old;while (telemetry.pop(old)) {}
        lostBefore=telemetry.dropped();count=last=0;ending=false;
        if (!write(object({{"kind","header"},{"schema","voxide.pr09-session.v1"},{"version",build::version},{"revision",build::revision},
            {"profile",build::profile},{"instance",instance},{"module_path",moduleFile.getFullPathName()},
            {"module_file_sha256",juce::String::toHexString(digest,CC_SHA256_DIGEST_LENGTH,0)},
            {"os",juce::SystemStats::getOperatingSystemName()},{"cpu",juce::SystemStats::getCpuModel()},
            {"unix_ms",juce::Time::currentTimeMillis()},{"tick_hz",juce::Time::getHighResolutionTicksPerSecond()},
            {"scope","processor render body only; excludes AU wrapper, telemetry collection and file IO"},
            {"pcm_recorded",false},{"allocation_audit_available",false}}))) return false;
        if (!telemetry.start()) throw std::runtime_error("Previous callback has not quiesced; retry capture");
        token=telemetry.capture();
        if (!worker.joinable()) worker=std::thread([this]
        {
            while (!exit.load(std::memory_order_acquire))
            {
                try { drain(); }
                catch (const std::exception& e) { const std::lock_guard stateLock(mutex);fail(e.what()); }
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
        });
        return true;
    }
    catch (const std::exception& e) { fail(e.what());return false; }
}
void SessionLog::stop() { const std::lock_guard lock(mutex);if (active()) { telemetry.stop();ending=true;drain(); } }
void SessionLog::drain()
{
    const std::lock_guard lock(mutex);
    if (!active()) return;
    SessionSample sample;
    for (std::uint64_t n=0;n<SessionTelemetry::capacity && telemetry.pop(sample);++n)
    {
        if (sample.capture!=token || sample.sequence<=last) { fail("Session log capture/sequence mismatch");return; }
        last=sample.sequence;++count;
        if (!write(object({{"kind","callback"},{"sequence",static_cast<juce::int64>(sample.sequence)},
            {"tick",static_cast<juce::int64>(sample.tick)},{"elapsed_ticks",static_cast<juce::int64>(sample.elapsed)},
            {"frames",sample.frames},{"rate",sample.rate},{"status",sample.status},{"active",sample.active},{"enabled",sample.enabled},
            {"root",sample.root},{"scale",sample.scale},{"epoch",static_cast<juce::int64>(sample.epoch)},
            {"offline",sample.offline},{"bypassed",sample.bypassed},{"transport_known",sample.transportKnown},{"playing",sample.playing},
            {"peak",sample.peak},{"nonfinite",static_cast<int>(sample.nonfinite)}}))) return;
    }
    if (ending && telemetry.quiescent())
    {
        // A writer could have published after the drain above but before becoming
        // quiescent. Finalize only after a subsequent drain sees that queue empty.
        if (!telemetry.empty()) return;
        if (!write(object({{"kind","end"},{"callbacks",static_cast<juce::int64>(count)},{"last_sequence",static_cast<juce::int64>(last)},
            {"dropped",static_cast<juce::int64>(telemetry.dropped()-lostBefore)},{"unix_ms",juce::Time::currentTimeMillis()}}))) return;
        const int result=::close(file);file=-1;ending=false;if (result) failure="Session log close failed";
    }
}
SessionLog::~SessionLog()
{
    exit.store(true,std::memory_order_release);if (worker.joinable()) worker.join();telemetry.stop();
    if (active()) { write(object({{"kind","aborted"},{"reason","processor destroyed before explicit capture stop"}}));if (file>=0) ::close(file); }
}
}
