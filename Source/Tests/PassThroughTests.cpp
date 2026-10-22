#include "PassThrough.h"
#include <array>
#include <cstdlib>
#include <iostream>
void runTrackingTests();

int main()
{
    runTrackingTests();
    const std::array<float, 5> source { 0.0f, 0.25f, -0.5f, 1.0f, -1.0f };
    std::array<float, 5> left {}, right {};
    voxide::passThrough(source.data(), left.data(), right.data(), 5);
    if (left != source || right != source) return EXIT_FAILURE;
    voxide::passThrough(left.data(), left.data(), right.data(), 5);
    if (left != source || right != source) return EXIT_FAILURE;
    voxide::passThrough(nullptr, left.data(), right.data(), 5);
    if (left != std::array<float, 5>{} || right != left) return EXIT_FAILURE;
    voxide::passThrough(nullptr, nullptr, nullptr, 0);
    std::cout << "Pass-through: copy, alias, silence, zero frames passed\n";
}
