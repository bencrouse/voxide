#include "TraceAllocations.h"
#include "../Source/Tests/AllocationAudit.h"
#include <array>
#include <cstdint>
#include <dlfcn.h>
#include <execinfo.h>
#include <malloc/malloc.h>
#include <ostream>
namespace
{
thread_local bool active=false, tracing=false, inside=false;
thread_local std::size_t count=0, captured=0;
struct Stack { int n=0; void* frames[24]{}; };
thread_local std::array<Stack,256> stacks;
void record()
{
    if(!active || inside) return;
    ++count;
    if(!tracing || captured==stacks.size()) return;
    inside=true;
    auto& s=stacks[captured++]; s.n=backtrace(s.frames,24);
    inside=false;
}
#ifndef VOXIDE_SANITIZED
void* allocate(std::size_t n) { record(); return malloc(n); }
void* zero(std::size_t n,std::size_t s) { record(); return calloc(n,s); }
void* resize(void* p,std::size_t n) { record(); return realloc(p,n); }
int align(void** p,std::size_t a,std::size_t n) { record(); return posix_memalign(p,a,n); }
void* aligned(std::size_t a,std::size_t n) { record(); return aligned_alloc(a,n); }
void* zoneMalloc(malloc_zone_t* z,std::size_t n) { record(); return malloc_zone_malloc(z,n); }
void* zoneCalloc(malloc_zone_t* z,std::size_t n,std::size_t s) { record(); return malloc_zone_calloc(z,n,s); }
void* zoneRealloc(malloc_zone_t* z,void* p,std::size_t n) { record(); return malloc_zone_realloc(z,p,n); }
void* zoneAlign(malloc_zone_t* z,std::size_t a,std::size_t n) { record(); return malloc_zone_memalign(z,a,n); }
__attribute__((used,section("__DATA,__interpose"))) const struct Interpose { const void* replacement; const void* original; } interpose[]{
    {(void*)allocate,(void*)malloc},{(void*)zero,(void*)calloc},{(void*)resize,(void*)realloc},
    {(void*)align,(void*)posix_memalign},{(void*)aligned,(void*)aligned_alloc},
    {(void*)zoneMalloc,(void*)malloc_zone_malloc},{(void*)zoneCalloc,(void*)malloc_zone_calloc},
    {(void*)zoneRealloc,(void*)malloc_zone_realloc},{(void*)zoneAlign,(void*)malloc_zone_memalign}
};
#endif
}
namespace voxide::audit
{
void begin() noexcept { count=0; active=true; }
std::size_t end() noexcept { active=false; return count; }
}
namespace voxide::trace
{
void enable(bool value)
{
    active=false; captured=0; tracing=value;
    // Warm the diagnostic unwinder off render. Never count its nested allocations.
    void* frames[24]; backtrace(frames,24);
}
void write(std::ostream& out)
{
    out<<"stack,depth,image,symbol,image_offset,symbol_offset\n";
    for(std::size_t i=0;i<captured;++i) for(int d=0;d<stacks[i].n;++d)
    {
        auto* address=stacks[i].frames[d]; Dl_info info{}; dladdr(address,&info);
        out<<i<<','<<d<<','<<(info.dli_fname?info.dli_fname:"")<<','<<(info.dli_sname?info.dli_sname:"")<<','
           <<(reinterpret_cast<std::uintptr_t>(address)-reinterpret_cast<std::uintptr_t>(info.dli_fbase))<<','
           <<(info.dli_saddr?reinterpret_cast<std::uintptr_t>(address)-reinterpret_cast<std::uintptr_t>(info.dli_saddr):0)<<'\n';
    }
}
}
