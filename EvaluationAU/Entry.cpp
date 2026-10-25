#include "Processor.h"
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new voxide::evaluation::Processor(); }
