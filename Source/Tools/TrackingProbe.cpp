#include "PitchTracker.h"
#include "HarmonySelector.h"
#include <array>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <string>

int main(int argc, char** argv)
{
    if (argc == 3 && std::string(argv[1]) == "--describe"
        && (std::string(argv[2]) == "44100" || std::string(argv[2]) == "48000"))
    {
        voxide::PitchTracker tracker;
        tracker.prepare(std::stod(argv[2]));
        const int support = tracker.supportSamples(), hop = tracker.hopSamples();
        std::cout << "{\"support_samples\":" << support << ",\"hop_samples\":" << hop
                  << ",\"first_available\":" << ((support + hop - 1) / hop) * hop << "}\n";
        return 0;
    }
    if (argc == 2 && std::string(argv[1]) == "--scales")
    {
        std::cout << "[";
        bool first = true;
        for (const auto& scale : voxide::scaleCatalog())
        {
            if (!first) std::cout << ',';
            first = false;
            std::cout << "{\"id\":\"" << scale.id << "\",\"name\":\"" << scale.name << "\",\"mask\":" << scale.mask << '}';
        }
        std::cout << "]\n"; return 0;
    }
    if (argc != 3 || (std::string(argv[1]) != "44100" && std::string(argv[1]) != "48000")
        || (std::string(argv[2]) != "yin" && std::string(argv[2]) != "multi"))
    {
        std::cerr << "Usage: voxide_tracking_probe <44100|48000> <yin|multi> < mono-float32-native > frames.csv\n";
        return 1;
    }
    voxide::PitchTracker tracker;
    tracker.prepare(std::stod(argv[1]), std::string(argv[2]) == "yin" ? voxide::TrackerVariant::yin : voxide::TrackerVariant::multiCandidate);
    voxide::HarmonySelector selector;
    std::array<float, 128> input {};
    std::uint64_t at = 0;
    std::cout << std::setprecision(17) << "begin,end,available,hz,confidence,voiced,rms,block_end,block_ns\n";
    while (std::cin.read(reinterpret_cast<char*>(input.data()), sizeof(input)) || std::cin.gcount() > 0)
    {
        const auto bytes = std::cin.gcount();
        if (bytes % sizeof(float) != 0) { std::cerr << "Partial float sample\n"; return 1; }
        const auto length = static_cast<int>(bytes / sizeof(float));
        std::array<voxide::PitchFrame, 2> frames {};
        int count = 0;
        const auto start = std::chrono::steady_clock::now();
        for (int i = 0; i < length; ++i)
            if (tracker.push(input[static_cast<std::size_t>(i)]))
            {
                frames[static_cast<std::size_t>(count++)] = tracker.frame();
                selector.pitch(tracker.frame());
            }
        const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now() - start).count();
        at += static_cast<std::uint64_t>(length);
        for (int i = 0; i < count; ++i)
        {
            const auto& f = frames[static_cast<std::size_t>(i)];
            std::cout << f.begin << ',' << f.end << ',' << f.available << ',' << f.hz << ',' << f.confidence << ',' << f.voiced << ','
                      << f.rms << ',' << at << ',' << ns << '\n';
        }
    }
    return std::cin.bad() ? 1 : 0;
}
