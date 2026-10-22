#pragma once
#include <cstddef>
#include <cstdlib>
#include <new>
namespace voxide::audit
{
#ifdef VOXIDE_SANITIZED
inline constexpr bool available = false;
#else
inline constexpr bool available = true;
#endif
void begin() noexcept;
std::size_t end() noexcept;
inline bool selfTest()
{
    void* (*volatile allocate)(std::size_t) = std::malloc;
    begin();
    void* p = allocate(37);
    const auto cCount = end();
    std::free(p);
    void* (*volatile cppAllocate)(std::size_t) = ::operator new;
    begin(); p = cppAllocate(61);
    const auto cppCount = end();
    ::operator delete(p);
    return cCount != 0 && cppCount != 0;
}
}
