#pragma once

namespace voxide
{
// No latency or pitch processing. Copies a dry mono source to stereo.
// Exact input/output aliasing is supported; no allocations or persistent state.
void passThrough(const float* source, float* left, float* right, int samples) noexcept;
}
