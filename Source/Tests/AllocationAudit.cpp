#include "AllocationAudit.h"
#include <cstdlib>
#include <malloc/malloc.h>
#include <new>

namespace
{
thread_local bool active = false;
thread_local std::size_t allocations = 0;
#ifndef VOXIDE_SANITIZED
void count() noexcept { if (active) ++allocations; }
void* auditedMalloc(std::size_t n) { count(); return std::malloc(n); }
void* auditedCalloc(std::size_t n, std::size_t size) { count(); return std::calloc(n, size); }
void* auditedRealloc(void* p, std::size_t n) { count(); return std::realloc(p, n); }
int auditedAlign(void** p, std::size_t a, std::size_t n) { count(); return posix_memalign(p, a, n); }
void* auditedAligned(std::size_t a, std::size_t n) { count(); return aligned_alloc(a, n); }
void* auditedZoneMalloc(malloc_zone_t* z, std::size_t n) { count(); return malloc_zone_malloc(z, n); }
void* auditedZoneCalloc(malloc_zone_t* z, std::size_t n, std::size_t s) { count(); return malloc_zone_calloc(z, n, s); }
void* auditedZoneRealloc(malloc_zone_t* z, void* p, std::size_t n) { count(); return malloc_zone_realloc(z, p, n); }
void* auditedZoneAlign(malloc_zone_t* z, std::size_t a, std::size_t n) { count(); return malloc_zone_memalign(z, a, n); }
// dyld deliberately leaves references from this dylib to the original functions
// uninterposed. No symbol lookup or logging is performed while the audit is active.
__attribute__((used, section("__DATA,__interpose"))) const struct Interpose
{
    const void* replacement;
    const void* original;
} interposers[] {
    { reinterpret_cast<const void*>(auditedMalloc), reinterpret_cast<const void*>(malloc) },
    { reinterpret_cast<const void*>(auditedCalloc), reinterpret_cast<const void*>(calloc) },
    { reinterpret_cast<const void*>(auditedRealloc), reinterpret_cast<const void*>(realloc) },
    { reinterpret_cast<const void*>(auditedAlign), reinterpret_cast<const void*>(posix_memalign) },
    { reinterpret_cast<const void*>(auditedAligned), reinterpret_cast<const void*>(aligned_alloc) },
    { reinterpret_cast<const void*>(auditedZoneMalloc), reinterpret_cast<const void*>(malloc_zone_malloc) },
    { reinterpret_cast<const void*>(auditedZoneCalloc), reinterpret_cast<const void*>(malloc_zone_calloc) },
    { reinterpret_cast<const void*>(auditedZoneRealloc), reinterpret_cast<const void*>(malloc_zone_realloc) },
    { reinterpret_cast<const void*>(auditedZoneAlign), reinterpret_cast<const void*>(malloc_zone_memalign) }
};
#endif
}
namespace voxide::audit
{
void begin() noexcept { allocations = 0; active = true; }
std::size_t end() noexcept { active = false; return allocations; }
}
