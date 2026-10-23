#include "EngineAdapter.h"
#include "AllocationAudit.h"
#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <filesystem>

namespace
{
using namespace voxide::engines;
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
struct Control { std::uint64_t source = 0; std::array<double, 3> ratios {1, 1, 1}; double hz = 200; };
struct Application { int voice; std::uint64_t requested, input; std::int64_t processing; double ratio, hz; int queriedPad, queriedDelay; };
struct Chunk { int voice; std::size_t begin, count; std::uint64_t available, callbackAvailable; };
struct Callback { std::uint64_t begin, frames, ns; std::size_t allocations; };
struct Result
{
    std::array<std::vector<float>, 3> outputs;
    std::vector<Application> applications;
    std::vector<Chunk> chunks;
    std::vector<Callback> callbacks;
    std::array<Info, 3> info {};
    std::size_t zeroTail = 0, nativeCalls = 0, maximumFifo = 0;
    std::size_t setupAllocations = 0, finishAllocations = 0;
    std::array<std::uint64_t, 3> inputHashes {14695981039346656037ull,14695981039346656037ull,14695981039346656037ull};
};
struct Audit
{
    explicit Audit(std::size_t& result) : count(result) { voxide::audit::begin(); }
    ~Audit() { count = voxide::audit::end(); }
    std::size_t& count;
};

class Runner
{
public:
    using Factory = std::unique_ptr<Engine> (*)(Config, double, double);
    Runner(Config c, int count, const Control& initial, Factory factory = create) : config(c), voices(count)
    {
        require(voices == 1 || voices == 3, "Use one or three independent mono instances");
        for (int i = 0; i < voices; ++i) engines[static_cast<std::size_t>(i)] = factory(config, initial.ratios[static_cast<std::size_t>(i)], initial.hz);
    }
    std::size_t reset(const Control& initial)
    {
        std::size_t allocations = 0;
        {
            Audit audit(allocations);
            for (int i = 0; i < voices; ++i) engines[static_cast<std::size_t>(i)]->reset(initial.ratios[static_cast<std::size_t>(i)], initial.hz);
        }
        return allocations;
    }
    Result run(const std::vector<float>& input, const std::vector<Control>& controls, const std::vector<int>& partitions)
    {
        require(!input.empty() && !controls.empty() && controls.front().source == 0 && !partitions.empty(), "Missing input/initial control/partitions");
        Result result;
        int quantum = 0, maximumHistory = 0;
        for (int i = 0; i < voices; ++i)
        {
            const auto v = static_cast<std::size_t>(i);
            result.info[v] = engines[v]->info();
            const auto& info = result.info[v];
            require(info.inputLatency >= 0 && info.inputLatency < 65536 && info.outputLatency >= 0 && info.outputLatency < 65536
                && info.startPad >= 0 && info.startPad < 65536 && info.startTrim >= 0 && info.startTrim < 65536,
                "Invalid engine latency/padding description");
            quantum = result.info[v].quantum;
            maximumHistory = std::max(maximumHistory, result.info[v].startPad + result.info[v].startTrim + result.info[v].nominalOffset());
        }
        require((quantum == 128 || quantum == 256 || quantum == 512) && maximumHistory < 65536, "Engine description exceeds bounded capacities");
        const std::size_t tail = static_cast<std::size_t>(config.rate / 5 + 2 * maximumHistory + quantum);
        const std::size_t total = ((input.size() + tail + static_cast<std::size_t>(quantum) - 1) / static_cast<std::size_t>(quantum)) * static_cast<std::size_t>(quantum);
        result.zeroTail = total - input.size();
        for (int i = 0; i < voices; ++i) result.outputs[static_cast<std::size_t>(i)].resize(total + 131072);
        result.chunks.reserve((total / static_cast<std::size_t>(quantum) + 1024) * static_cast<std::size_t>(voices));
        result.applications.reserve(controls.size() * static_cast<std::size_t>(voices));
        const auto minimum = *std::min_element(partitions.begin(), partitions.end());
        require(minimum >= 1 && *std::max_element(partitions.begin(), partitions.end()) <= 4096, "Invalid host partition");
        result.callbacks.reserve(total / static_cast<std::size_t>(minimum) + 1);
        std::array<std::size_t, 3> written {}, next {}, discard {};
        std::array<Fifo<65536>, 3> fifo;
        std::array<float, 512> block {};
        std::array<float, 1024> scratch {};
        auto drain = [&](int voice, std::uint64_t available, std::uint64_t callbackAvailable)
        {
            const auto v = static_cast<std::size_t>(voice);
            auto& engine = *engines[v];
            unsigned iterations = 0;
            while (engine.available() > 0)
            {
                if (++iterations > 64) throw "Bounded engine retrieval budget exhausted";
                const int count = engine.retrieve(scratch.data(), static_cast<int>(scratch.size()));
                if (count <= 0 || count > static_cast<int>(scratch.size())) throw "Invalid engine retrieve count";
                for (int j = 0; j < count; ++j)
                {
                    if (discard[v] != 0) { --discard[v]; continue; }
                    if (!std::isfinite(scratch[static_cast<std::size_t>(j)])) throw "Non-finite engine output";
                    if (!fifo[v].push(scratch[static_cast<std::size_t>(j)])) throw "Output FIFO overflow";
                }
            }
            result.maximumFifo = std::max(result.maximumFifo, fifo[v].size());
            const auto begin = written[v];
            float value = 0;
            while (fifo[v].pop(value))
            {
                if (written[v] >= result.outputs[v].size()) throw "Bounded output capture exhausted";
                result.outputs[v][written[v]++] = value;
            }
            if (written[v] != begin) result.chunks.push_back({voice, begin, written[v] - begin, available, callbackAvailable});
        };
        {
            Audit audit(result.setupAllocations);
            for (int i = 0; i < voices; ++i)
            {
                const auto v = static_cast<std::size_t>(i);
                discard[v] = static_cast<std::size_t>(result.info[v].startTrim);
                int remaining = result.info[v].startPad;
                while (remaining > 0)
                {
                    const int count = std::min(remaining, quantum);
                    engines[v]->process(block.data(), count); drain(i, 0, 0); remaining -= count;
                }
                next[v] = 1;
                result.applications.push_back({i, 0, 0, -result.info[v].controlLag, controls.front().ratios[v], controls.front().hz,
                    result.info[v].startPad, result.info[v].startTrim});
            }
        }
        std::size_t position = 0, partition = 0;
        int fill = 0;
        while (position < total)
        {
            const auto frames = std::min(total - position, static_cast<std::size_t>(partitions[partition++ % partitions.size()]));
            Callback callback {position, frames, 0, 0};
            const auto started = std::chrono::steady_clock::now();
            {
                Audit audit(callback.allocations);
                for (std::size_t j = 0; j < frames; ++j)
                {
                    block[static_cast<std::size_t>(fill++)] = position + j < input.size() ? input[position + j] : 0.0f;
                    if (fill != quantum) continue;
                    const auto consumed = position + j + 1;
                    const auto begin = consumed - static_cast<std::size_t>(quantum);
                    for (int i = 0; i < voices; ++i)
                    {
                        const auto v = static_cast<std::size_t>(i);
                        const auto processing = static_cast<std::int64_t>(begin) - result.info[v].controlLag;
                        while (next[v] < controls.size() && static_cast<std::int64_t>(controls[next[v]].source) <= processing)
                        {
                            const auto& event = controls[next[v]++];
                            engines[v]->control(event.ratios[v], event.hz);
                            const auto queried = engines[v]->info();
                            result.applications.push_back({i, event.source, begin, processing, event.ratios[v], event.hz, queried.startPad, queried.startTrim});
                        }
                        for (int sample = 0; sample < quantum; ++sample)
                            result.inputHashes[v] = (result.inputHashes[v] ^ std::bit_cast<std::uint32_t>(block[static_cast<std::size_t>(sample)])) * 1099511628211ull;
                        engines[v]->process(block.data(), quantum);
                        ++result.nativeCalls;
                        drain(i, consumed, position + frames);
                    }
                    fill = 0;
                }
            }
            callback.ns = static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now() - started).count());
            result.callbacks.push_back(callback);
            position += frames;
        }
        {
            Audit audit(result.finishAllocations);
            for (int i = 0; i < voices; ++i) { engines[static_cast<std::size_t>(i)]->finish(); drain(i, total, total); }
        }
        for (int i = 0; i < voices; ++i)
        {
            const auto v = static_cast<std::size_t>(i);
            require(next[v] == controls.size(), "A prescribed control was never applied");
            require(discard[v] == 0, "Engine did not emit its start trim");
            require(written[v] > 0, "Engine emitted no captured output");
            result.outputs[v].resize(written[v]);
        }
        return result;
    }
private:
    Config config;
    int voices;
    std::array<std::unique_ptr<Engine>, 3> engines;
};

double difference(const std::vector<float>& a, const std::vector<float>& b)
{
    if (a.size() != b.size()) return std::numeric_limits<double>::infinity();
    double maximum = 0;
    for (std::size_t i = 0; i < a.size(); ++i) maximum = std::max(maximum, std::abs(static_cast<double>(a[i]) - b[i]));
    return maximum;
}
void writeExclusive(const std::string&, const char*, std::size_t);
struct ResetOverlap { double maximum = 0, rms = 0, unmatchedTailPeak = 0; };
void save(const std::string&, const Result&, Config, int, std::size_t, std::size_t, double, double, bool resetMeasured = true, double resetRms = 0, const ResetOverlap* overlap = nullptr);

class TransportControl final : public Engine
{
public:
    explicit TransportControl(bool leakAfterReset = false) : leakOnReset(leakAfterReset) {}
    Info info() const noexcept override { return {0,0,0,0,128,0,0}; }
    void control(double, double) override {}
    void process(const float* source, int count) override
    {
        require(pending == 0 && count > 0 && count <= 128, "Transport control capacity");
        std::copy_n(source,count,data.begin());
        if (leaking) data[0] += .25f; // Explicit negative-control engine, never a native render.
        pending=count; read=0;
    }
    int available() const override { return pending; }
    int retrieve(float* destination, int maximum) override { const int n=std::min(maximum,pending); std::copy_n(data.data()+read,n,destination); pending-=n; read+=n; return n; }
    void finish() override {}
    void reset(double, double) override { pending=read=0; leaking=leakOnReset; }
private:
    std::array<float,128> data {};
    int pending=0, read=0;
    bool leakOnReset=false, leaking=false;
};

void selfTest(const std::string& outputRoot, bool resetFailureControl = false)
{
    namespace fs = std::filesystem;
    fs::create_directories(outputRoot);
    const auto unique = std::string(engineName()) + "-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
    const auto evidence = fs::path(outputRoot) / unique;
    require(fs::create_directory(evidence), "Self-test evidence path exists");
    std::ostringstream observations;
    observations << "{\"schema\":\"voxide.engine-adapter-test.v1\",\"adapter_contract\":\"pass\",\"profile\":\"" << VOXIDE_ENGINE_PROFILE
        << "\",\"sanitizer\":\"" << VOXIDE_ENGINE_SANITIZER << "\",\"diagnostic_reset_failure_control\":" << (resetFailureControl ? "true" : "false")
        << ",\"native_repeat_observations\":[";
    std::size_t comparisons = 0, failures = 0;
    std::size_t resetFailures = 0;
    std::ostringstream resetObservations;
    if (voxide::audit::available) require(voxide::audit::selfTest(), "Allocation detector failed deliberate C/C++ controls");
    Fifo<7> fifo;
    for (int pass = 0; pass < 20000; ++pass)
    {
        for (int i = 0; i < 7; ++i) require(fifo.push(static_cast<float>(pass + i)), "FIFO early overflow");
        require(!fifo.push(0), "FIFO overflow unreported");
        for (int i = 0; i < 7; ++i) { float value = -1; require(fifo.pop(value) && value == pass + i, "FIFO wrap lost/repeated samples"); }
        float value = 0; require(!fifo.pop(value), "FIFO underflow unreported");
    }
    {
        // A deterministic, non-DSP transport control isolates OUR adapter from
        // engine-instance numerical variation. This must preserve exact PCM bits.
        auto factory = +[](Config, double, double) -> std::unique_ptr<Engine> { return std::make_unique<TransportControl>(); };
        std::vector<float> source(10000);
        for (std::size_t i = 0; i < source.size(); ++i) source[i] = static_cast<float>(static_cast<int>(i % 127) - 63) / 128;
        source[0] = -0.0f;
        const std::vector<Control> controls {{0,{1,.5,2},220},{123,{.25,4,1},220},{259,{1,1,1},220}};
        Runner first({48000,512,128},3,controls.front(),factory);
        const auto reference = first.run(source,controls,{128});
        for (auto blocks : {std::vector<int>{32},{64},{128},{257},{512},{1024},{32,64,128,257,512,1024}})
        {
            Runner other({48000,512,128},3,controls.front(),factory);
            const auto actual = other.run(source,controls,blocks);
            for (std::size_t voice = 0; voice < 3; ++voice)
            {
                require(difference(reference.outputs[voice],actual.outputs[voice]) == 0, "Transport control partition mismatch");
                for (std::size_t i = 0; i < source.size(); ++i)
                    require(std::bit_cast<std::uint32_t>(actual.outputs[voice][i]) == std::bit_cast<std::uint32_t>(source[i]), "Adapter dropped/repeated/changed source PCM");
                for (std::size_t i = source.size(); i < actual.outputs[voice].size(); ++i)
                    require(actual.outputs[voice][i] == 0, "Transport control generated an unexplained tail");
            }
        }
    }
#ifdef VOXIDE_ENGINE_signalsmith
    const std::array<Config, 3> configs {{ {48000,512,128}, {48000,1024,256}, {44100,2048,512} }};
#else
    const std::array<Config, 2> configs {{ {48000,1,128}, {44100,2,128} }};
#endif
    for (const auto config : configs)
    {
        std::vector<float> input(static_cast<std::size_t>(config.rate / 5));
        for (std::size_t i = 0; i < input.size(); ++i) input[i] = static_cast<float>(.1 * std::sin(6.283185307179586 * 220 * i / config.rate));
        std::vector<Control> controls {{0, {1, .5, 2}, 220}, {static_cast<std::uint64_t>(config.rate / 10 + 7), {.25,4,1}, 220}};
        const Runner::Factory factory = resetFailureControl
            ? +[](Config, double, double) -> std::unique_ptr<Engine> { return std::make_unique<TransportControl>(true); }
            : create;
        Runner referenceRunner(config, 3, controls.front(), factory);
        const auto reference = referenceRunner.run(input, controls, {128});
        save((evidence / ("reference-" + std::to_string(config.window))).string(), reference, config, 3, input.size(), 0, 0, 0, false);
        writeExclusive((evidence / ("input-" + std::to_string(config.window) + ".f32")).string(), reinterpret_cast<const char*>(input.data()), input.size()*sizeof(float));
        int partitionIndex = 0;
        for (auto blocks : {std::vector<int>{128}, {32}, {64}, {257}, {512}, {1024}, {32,64,128,257,512,1024}})
        {
            Runner other(config, 3, controls.front(), factory);
            const auto rendered = other.run(input, controls, blocks);
            require(reference.inputHashes == rendered.inputHashes, "Host partition changed native input sequence");
            bool retain = false;
            for (std::size_t voice = 0; voice < 3; ++voice)
            {
                const auto delta = difference(reference.outputs[voice], rendered.outputs[voice]);
                double sum = 0;
                if (std::isfinite(delta)) for (std::size_t s = 0; s < reference.outputs[voice].size(); ++s)
                {
                    const auto d = static_cast<double>(reference.outputs[voice][s]) - rendered.outputs[voice][s]; sum += d*d;
                }
                const double rms = std::isfinite(delta) ? std::sqrt(sum / reference.outputs[voice].size()) : std::numeric_limits<double>::infinity();
                const bool passed = delta <= 1e-6 && rms <= 1e-7;
                if (comparisons++) observations << ',';
                observations << "{\"window\":" << config.window << ",\"rate\":" << config.rate << ",\"voice\":" << voice
                    << ",\"partition_case\":" << partitionIndex << ",\"fresh_same_partition_control\":" << (partitionIndex == 0 ? "true" : "false")
                    << ",\"within_frozen_tolerance\":" << (passed ? "true" : "false") << ",\"max_abs\":";
                if (std::isfinite(delta)) observations << std::setprecision(17) << delta; else observations << "null";
                observations << ",\"rms\":"; if (std::isfinite(rms)) observations << rms; else observations << "null";
                observations << '}';
                if (!passed) { ++failures; retain = true; }
            }
            require(reference.applications.size() == rendered.applications.size(), "Host partition lost controls");
            for (std::size_t i = 0; i < reference.applications.size(); ++i)
                require(reference.applications[i].input == rendered.applications[i].input
                    && reference.applications[i].ratio == rendered.applications[i].ratio
                    && reference.applications[i].hz == rendered.applications[i].hz, "Host partition changed control arrival");
            if (retain) save((evidence / ("native-variation-" + std::to_string(config.window) + "-" + std::to_string(partitionIndex))).string(), rendered, config, 3, input.size(), 0, 0, 0, false);
            ++partitionIndex;
        }
        referenceRunner.reset(controls.front());
        const std::vector<float> silence(input.size(), 0);
        const auto resetSilence = referenceRunner.run(silence, {controls.front()}, {257});
        double resetPeak = 0;
        for (const auto& output : resetSilence.outputs)
            for (float value : output) resetPeak = std::max(resetPeak,std::abs(static_cast<double>(value)));
        const bool resetPassed = resetPeak < 1e-6;
        if (resetObservations.tellp() > 0) resetObservations << ',';
        resetObservations << "{\"window\":" << config.window << ",\"rate\":" << config.rate
            << ",\"peak\":" << std::setprecision(17) << resetPeak << ",\"within_tolerance\":" << (resetPassed ? "true" : "false") << '}';
        if (!resetPassed)
        {
            ++resetFailures;
            save((evidence / ("reset-silence-failure-" + std::to_string(config.window))).string(), resetSilence, config, 3, input.size(), 0, 0, resetPeak, false);
        }
    }
    observations << "],\"native_repeat_failures\":" << failures << ",\"native_determinism_gate\":\"" << (failures ? "fail" : "pass")
        << "\",\"native_reset_silence_observations\":[" << resetObservations.str() << "],\"native_reset_silence_gate\":\"" << (resetFailures ? "fail" : "pass")
        << "\",\"scope\":\"Adapter correctness is separate from native waveform repeatability and reset-silence gates; failures are retained, not counted as engine passes\"}\n";
    const auto json = observations.str(); writeExclusive((evidence / "report.json").string(),json.data(),json.size());
    std::cout << engineName() << ": FIFO/native-input/control checks passed; native reset-silence failures=" << resetFailures
              << "; native repeatability failures=" << failures << "; allocation audit "
              << (voxide::audit::available ? "self-verified" : "disabled under sanitizer (separate Debug/Release audit required)") << '\n';
    std::cout << "Self-test evidence: " << (evidence / "report.json").string() << '\n';
    require(resetFailures == 0, "Native reset-silence gate failed; raw output/timelines and complete report retained");
}

std::vector<int> parsePartitions(const std::string& text)
{
    std::vector<int> values;
    std::istringstream stream(text); std::string token;
    while (std::getline(stream, token, ',')) { std::size_t used = 0; const int value = std::stoi(token, &used); require(used == token.size() && value >= 1 && value <= 4096, "Invalid partition"); values.push_back(value); }
    require(!values.empty(), "Empty partition sequence"); return values;
}
int integerArgument(const std::string& text)
{
    std::size_t used = 0;
    const int value = std::stoi(text,&used);
    require(used == text.size(), "Invalid integer argument");
    return value;
}
std::vector<Control> readControls(const std::string& path, std::size_t frames, int rate)
{
    std::ifstream stream(path); require(stream.good(), "Cannot read oracle controls");
    std::vector<Control> controls; std::string line;
    while (std::getline(stream, line))
    {
        std::istringstream row(line); Control control; std::string extra;
        require(static_cast<bool>(row >> control.source >> control.ratios[0] >> control.ratios[1] >> control.ratios[2] >> control.hz) && !(row >> extra), "Invalid control row");
        require(control.source < frames && (controls.empty() ? control.source == 0 : control.source > controls.back().source), "Unsorted/out-of-range control timestamp");
        for (double ratio : control.ratios) require(std::isfinite(ratio) && ratio >= .25 && ratio <= 4, "Shift outside +/-24 semitones");
        require(std::isfinite(control.hz) && control.hz >= 0 && control.hz < rate / 2 && controls.size() < 1000000, "Invalid oracle F0/control count");
        controls.push_back(control);
    }
    require(!controls.empty(), "No initial oracle control"); return controls;
}
void writeExclusive(const std::string& path, const char* data, std::size_t bytes)
{
    const int fd = ::open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0600);
    require(fd >= 0, "Cannot create exclusive evidence output");
    while (bytes != 0)
    {
        const auto count = ::write(fd, data, bytes);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) { ::close(fd); throw std::runtime_error("Evidence output write failed"); }
        data += count; bytes -= static_cast<std::size_t>(count);
    }
    require(::close(fd) == 0, "Evidence output close failed");
}
void save(const std::string& prefix, const Result& result, Config config, int voices, std::size_t inputFrames,
          std::size_t resetAllocations, double resetDifference, double resetSilence, bool resetMeasured, double resetRms, const ResetOverlap* overlap)
{
    for (int i = 0; i < voices; ++i)
    {
        const auto& samples = result.outputs[static_cast<std::size_t>(i)];
        writeExclusive(prefix + "-voice" + std::to_string(i + 1) + ".f32", reinterpret_cast<const char*>(samples.data()), samples.size() * sizeof(float));
    }
    std::ostringstream chunks, applications, callbacks;
    chunks << "voice,output_begin,count,available_source_samples,callback_available_source_samples\n";
    for (const auto& chunk : result.chunks) chunks << chunk.voice << ',' << chunk.begin << ',' << chunk.count << ',' << chunk.available << ',' << chunk.callbackAvailable << '\n';
    applications << std::setprecision(17) << "voice,requested_source_sample,applied_input_begin,processing_source_sample,ratio,source_hz,queried_start_pad,queried_start_delay\n";
    for (const auto& event : result.applications) applications << event.voice << ',' << event.requested << ',' << event.input << ',' << event.processing << ',' << event.ratio << ',' << event.hz << ',' << event.queriedPad << ',' << event.queriedDelay << '\n';
    callbacks << "begin,frames,ns,allocations\n";
    for (const auto& callback : result.callbacks) callbacks << callback.begin << ',' << callback.frames << ',' << callback.ns << ',' << callback.allocations << '\n';
    const auto chunkData = chunks.str(), controlData = applications.str(), callbackData = callbacks.str();
    writeExclusive(prefix + "-availability.csv", chunkData.data(), chunkData.size());
    writeExclusive(prefix + "-controls.csv", controlData.data(), controlData.size());
    writeExclusive(prefix + "-callbacks.csv", callbackData.data(), callbackData.size());
    std::ostringstream report;
    report << std::setprecision(17) << "{\"schema\":\"voxide.engine-render.v1\",\"status\":\"rendered\",\"engine\":\"" << engineName()
        << "\",\"profile\":\"" << VOXIDE_ENGINE_PROFILE << "\",\"sample_rate\":" << config.rate << ",\"source_frames\":" << inputFrames
        << ",\"sanitizer\":\"" << VOXIDE_ENGINE_SANITIZER << "\""
        << ",\"configured_window\":" << config.window << ",\"configured_hop\":" << config.hop
        << ",\"compiled_source_identity\":\"" << VOXIDE_ENGINE_SOURCE_IDENTITY << "\""
        << ",\"voices\":" << voices << ",\"zero_tail_supplied\":" << result.zeroTail << ",\"native_calls\":" << result.nativeCalls
        << ",\"maximum_fifo_occupancy\":" << result.maximumFifo << ",\"formant_preservation\":true,\"time_ratio\":1,\"audit_available\":" << (voxide::audit::available ? "true" : "false")
        << ",\"setup_allocations\":" << result.setupAllocations << ",\"finish_allocations\":" << result.finishAllocations
        << ",\"setup_audit_scope\":\"zero-padding only; constructor/configuration happens before audit\""
        << ",\"reset_allocations\":" << resetAllocations << ",\"reset_silence_peak\":" << resetSilence << ",\"reset_vs_fresh_max_abs\":";
    if (std::isfinite(resetDifference)) report << resetDifference; else report << "null";
    report << ",\"reset_vs_fresh_rms\":";
    if (std::isfinite(resetRms)) report << resetRms; else report << "null";
    report << ",\"reset_rms_scope\":\"maximum per-voice RMS, not pooled\"";
    report << ",\"reset_overlap\":";
    if (overlap) report << "{\"max_abs\":" << overlap->maximum << ",\"rms\":" << overlap->rms << ",\"unmatched_tail_peak\":" << overlap->unmatchedTailPeak << '}';
    else report << "null";
    report << ",\"reset_measurement_performed\":" << (resetMeasured ? "true" : "false") << ",\"instances\":[";
    for (int i = 0; i < voices; ++i)
    {
        if (i) report << ',';
        const auto v = static_cast<std::size_t>(i); const auto& info = result.info[v];
        report << "{\"input_latency\":" << info.inputLatency << ",\"output_latency\":" << info.outputLatency
            << ",\"preferred_start_pad\":" << info.startPad << ",\"discarded_start_delay\":" << info.startTrim << ",\"control_lag\":" << info.controlLag
            << ",\"quantum\":" << info.quantum << ",\"native_version\":" << info.nativeVersion << ",\"nominal_output_offset\":" << info.nominalOffset()
            << ",\"native_input_hash\":\"" << result.inputHashes[v] << "\""
            << ",\"output_frames\":" << result.outputs[v].size() << '}';
    }
    report << "]}\n";
    const auto reportData = report.str(); writeExclusive(prefix + "-native.json", reportData.data(), reportData.size());
}
}

int main(int argc, char** argv)
{
    try
    {
        if ((argc == 2 || argc == 3) && std::string(argv[1]) == "--self-test") { selfTest(argc == 3 ? argv[2] : VOXIDE_ENGINE_SELFTEST_DIRECTORY); return 0; }
        if (argc == 3 && std::string(argv[1]) == "--self-test-reset-failure-control") { selfTest(argv[2], true); return 0; }
        require(argc == 8, "Usage: evaluator <rate> <window> <hop> <voices> <controls.txt> <output-prefix> <host-block-csv> < mono-f32");
        require(std::endian::native == std::endian::little && sizeof(float) == 4, "Requires little-endian float32");
        const Config config {integerArgument(argv[1]), integerArgument(argv[2]), integerArgument(argv[3])}; const int voices = integerArgument(argv[4]);
        const auto partitions = parsePartitions(argv[7]);
        std::vector<float> input; std::array<float,4096> buffer {};
        while (std::cin.read(reinterpret_cast<char*>(buffer.data()), sizeof(buffer)) || std::cin.gcount() > 0)
        {
            require(std::cin.gcount() % sizeof(float) == 0, "Partial input float");
            input.insert(input.end(), buffer.begin(), buffer.begin() + std::cin.gcount() / static_cast<std::streamsize>(sizeof(float)));
            require(input.size() <= 48000 * 120, "Offline input exceeds two-minute bound");
        }
        require(!std::cin.bad() && !input.empty() && std::all_of(input.begin(), input.end(), [](float x) { return std::isfinite(x); }), "Invalid source PCM");
        const auto controls = readControls(argv[5], input.size(), config.rate);
        if (voxide::audit::available) require(voxide::audit::selfTest(), "Allocation audit self-test failed");
        Runner runner(config, voices, controls.front()); const auto result = runner.run(input, controls, partitions);
        const auto resetAllocations = runner.reset(controls.front()); const auto repeated = runner.run(input, controls, partitions);
        double resetDifference = 0, resetRms = 0;
        ResetOverlap overlap;
        for (int i = 0; i < voices; ++i)
        {
            const auto& before = result.outputs[static_cast<std::size_t>(i)]; const auto& after = repeated.outputs[static_cast<std::size_t>(i)];
            resetDifference = std::max(resetDifference,difference(before,after));
            const auto common = std::min(before.size(),after.size());
            double overlapSquares = 0;
            for (std::size_t sample = 0; sample < common; ++sample)
            {
                const double delta = static_cast<double>(before[sample])-after[sample];
                overlap.maximum = std::max(overlap.maximum,std::abs(delta)); overlapSquares += delta*delta;
            }
            if (common > 0) overlap.rms = std::max(overlap.rms,std::sqrt(overlapSquares/common));
            for (std::size_t sample = common; sample < before.size(); ++sample) overlap.unmatchedTailPeak = std::max(overlap.unmatchedTailPeak,std::abs(static_cast<double>(before[sample])));
            for (std::size_t sample = common; sample < after.size(); ++sample) overlap.unmatchedTailPeak = std::max(overlap.unmatchedTailPeak,std::abs(static_cast<double>(after[sample])));
            double squared = 0;
            if (before.size() == after.size() && !before.empty())
            {
                for (std::size_t sample = 0; sample < before.size(); ++sample)
                {
                    const double delta = static_cast<double>(before[sample]) - after[sample]; squared += delta*delta;
                }
                resetRms = std::max(resetRms,std::sqrt(squared/before.size()));
            }
            else resetRms = std::numeric_limits<double>::infinity();
        }
        runner.reset(controls.front()); const auto silence = runner.run(std::vector<float>(input.size(), 0), {controls.front()}, partitions);
        double peak = 0;
        for (const auto& output : silence.outputs) for (float x : output) peak = std::max(peak, std::abs(static_cast<double>(x)));
        save(argv[6], result, config, voices, input.size(), resetAllocations, resetDifference, peak, true, resetRms, &overlap);
        if (!std::isfinite(resetDifference) || resetDifference > 1e-6 || resetRms > 1e-7)
        {
            save(std::string(argv[6]) + "-after-reset", repeated, config, voices, input.size(), 0, 0, 0, false);
            std::cout << "Retained reset comparison: " << argv[6] << "-after-reset\n";
        }
        if (peak > 1e-6)
        {
            save(std::string(argv[6]) + "-reset-silence", silence, config, voices, input.size(), 0, 0, 0, false);
            std::cout << "Retained reset silence failure: " << argv[6] << "-reset-silence\n";
        }
        return 0;
    }
    catch (const char* message) { std::cerr << message << '\n'; return 1; }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
