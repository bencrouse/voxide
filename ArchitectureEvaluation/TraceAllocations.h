#pragma once
#include <iosfwd>
namespace voxide::trace
{
// Diagnostic only: bounded stack capture is deliberately NOT realtime evidence.
void enable(bool);
void write(std::ostream&);
}
