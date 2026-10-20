#include "PassThrough.h"

namespace voxide
{
void passThrough(const float* source, float* left, float* right, int samples) noexcept
{
    for (int i = 0; i < samples; ++i)
    {
        const auto sample = source != nullptr ? source[i] : 0.0f;
        left[i] = sample;
        right[i] = sample;
    }
}
}
