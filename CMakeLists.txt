cmake_minimum_required(VERSION 3.24)
set(CMAKE_OSX_ARCHITECTURES arm64 CACHE STRING "Supported architecture")
set(CMAKE_OSX_DEPLOYMENT_TARGET "15.0" CACHE STRING "Minimum macOS")
project(voxide VERSION 0.1.0 LANGUAGES C CXX)

if(NOT APPLE OR NOT CMAKE_OSX_ARCHITECTURES STREQUAL "arm64"
   OR NOT CMAKE_OSX_DEPLOYMENT_TARGET STREQUAL "15.0")
    message(FATAL_ERROR "Voxide currently supports arm64 / macOS 15.0 deployment only")
endif()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(VOXIDE_SANITIZER "" CACHE STRING "Diagnostic profile: address or thread")
if(VOXIDE_SANITIZER)
    if(NOT VOXIDE_SANITIZER MATCHES "^(address|thread)$")
        message(FATAL_ERROR "Unknown sanitizer: ${VOXIDE_SANITIZER}")
    endif()
    add_compile_options(-fsanitize=${VOXIDE_SANITIZER} -fno-omit-frame-pointer)
    add_link_options(-fsanitize=${VOXIDE_SANITIZER})
endif()

include(cmake/JuceDependency.cmake)
find_package(Python3 3.9 REQUIRED COMPONENTS Interpreter)
execute_process(COMMAND git rev-parse --short=12 HEAD
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}" OUTPUT_VARIABLE VOXIDE_REVISION
    OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
if(NOT VOXIDE_REVISION)
    set(VOXIDE_REVISION "unversioned")
endif()
execute_process(COMMAND git status --porcelain
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}" OUTPUT_VARIABLE voxide_dirty ERROR_QUIET)
if(voxide_dirty)
    string(APPEND VOXIDE_REVISION "-dirty")
endif()
configure_file(Source/BuildInfo.h.in generated/BuildInfo.h @ONLY)

add_library(voxide_dsp STATIC Source/DSP/PassThrough.cpp Source/DSP/PitchTracker.cpp Source/DSP/HarmonySelector.cpp)
target_include_directories(voxide_dsp PUBLIC Source/DSP)
target_compile_options(voxide_dsp PRIVATE -Wall -Wextra -Wpedantic)

add_library(voxide_processor STATIC Source/PluginProcessor.cpp Source/DiagnosticLog.cpp)
target_include_directories(voxide_processor PUBLIC Source "${PROJECT_BINARY_DIR}/generated")
target_compile_definitions(voxide_processor PUBLIC
    JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0
    JUCE_USE_FLAC=0 JUCE_USE_OGGVORBIS=0 JUCE_USE_MP3AUDIOFORMAT=0
    JUCE_USE_LAME_AUDIO_FORMAT=0 JUCE_USE_WINDOWS_MEDIA_FORMAT=0)
target_link_libraries(voxide_processor PUBLIC voxide_dsp juce::juce_audio_utils
    juce::juce_recommended_config_flags juce::juce_recommended_warning_flags)

juce_add_plugin(voxide
    COMPANY_NAME "voxide"
    BUNDLE_ID "com.voxide.audio.voxide"
    PLUGIN_MANUFACTURER_CODE Vxid
    PLUGIN_CODE Vx00
    FORMATS AU Standalone
    PRODUCT_NAME "voxide"
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    AU_MAIN_TYPE kAudioUnitType_MusicEffect
    AU_SANDBOX_SAFE TRUE
    MICROPHONE_PERMISSION_ENABLED TRUE
    MICROPHONE_PERMISSION_TEXT "Voxide uses audio input only when you explicitly run the development standalone app."
    EDITOR_WANTS_KEYBOARD_FOCUS FALSE
    COPY_PLUGIN_AFTER_BUILD FALSE)
target_sources(voxide PRIVATE Source/PluginEntry.cpp)
target_link_libraries(voxide PRIVATE voxide_processor)

enable_testing()
add_library(voxide_allocation_audit SHARED Source/Tests/AllocationAudit.cpp)
if(VOXIDE_SANITIZER)
    # Sanitizer malloc interceptors take precedence over dyld interposition.
    # Audit in ordinary Debug/Release; do not interpose sanitizer internals.
    target_compile_definitions(voxide_allocation_audit PUBLIC VOXIDE_SANITIZED=1)
endif()
add_executable(voxide_dsp_tests Source/Tests/PassThroughTests.cpp Source/Tests/TrackingTests.cpp)
target_link_libraries(voxide_dsp_tests PRIVATE voxide_dsp voxide_allocation_audit)
add_test(NAME dsp COMMAND voxide_dsp_tests)
juce_add_console_app(voxide_processor_tests PRODUCT_NAME "voxide_processor_tests")
target_sources(voxide_processor_tests PRIVATE Source/Tests/ProcessorTests.cpp Source/Tests/DiagnosticsTests.cpp Source/Tests/TrackingProcessorTests.cpp)
target_compile_definitions(voxide_processor_tests PRIVATE VOXIDE_TEST_OUTPUT_DIR="${PROJECT_BINARY_DIR}/test-output/diagnostics")
target_link_libraries(voxide_processor_tests PRIVATE voxide_processor voxide_allocation_audit)
add_test(NAME processor COMMAND voxide_processor_tests)
add_executable(voxide_au_render_tests Source/Tests/AuRenderTests.cpp)
target_link_libraries(voxide_au_render_tests PRIVATE "-framework AudioToolbox" "-framework CoreFoundation")
add_dependencies(voxide_au_render_tests voxide_AU)
add_test(NAME au_render COMMAND voxide_au_render_tests "$<TARGET_BUNDLE_DIR:voxide_AU>"
    --report "${PROJECT_BINARY_DIR}/au-routing-report.json")
add_test(NAME tooling COMMAND "${Python3_EXECUTABLE}" -m unittest discover -s scripts/tests -v)
set_tests_properties(tooling PROPERTIES WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
add_test(NAME bundle_metadata COMMAND "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/scripts/verify_bundle.py" "$<TARGET_BUNDLE_DIR:voxide_Standalone>"
    "$<TARGET_BUNDLE_DIR:voxide_AU>")

add_executable(voxide_environment Source/Tools/EnvironmentProbe.cpp)
target_link_libraries(voxide_environment PRIVATE "-framework CoreAudio" "-framework CoreMIDI" "-framework CoreFoundation")
add_executable(voxide_tracking_probe Source/Tools/TrackingProbe.cpp)
target_link_libraries(voxide_tracking_probe PRIVATE voxide_dsp)
