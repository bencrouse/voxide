#pragma once
#include "EngineAdapter.h"
#include <string>
namespace voxide::interaction
{
// Generates only a fixed synthetic workload. No input files, private audio or playback.
int runEngineering(engines::Config, int callbackFrames, const std::string& prefix);
}
