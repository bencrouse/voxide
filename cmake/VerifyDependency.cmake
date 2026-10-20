include("${CMAKE_CURRENT_LIST_DIR}/JucePin.cmake")

function(voxide_verify_archive archive)
    if(NOT EXISTS "${archive}" OR IS_DIRECTORY "${archive}")
        message(FATAL_ERROR "Missing JUCE archive: ${archive}")
    endif()
    file(SHA256 "${archive}" actual_hash)
    if(NOT actual_hash STREQUAL VOXIDE_JUCE_SHA256)
        message(FATAL_ERROR "JUCE checksum mismatch: ${archive}")
    endif()
endfunction()

function(voxide_verify_checkout directory)
    find_package(Git REQUIRED)
    if(NOT EXISTS "${directory}/CMakeLists.txt")
        message(FATAL_ERROR "JUCE_DIR is not a JUCE checkout")
    endif()
    execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${directory}" rev-parse HEAD
        RESULT_VARIABLE revision_status OUTPUT_VARIABLE revision OUTPUT_STRIP_TRAILING_WHITESPACE)
    execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${directory}" status --porcelain --untracked-files=all
        RESULT_VARIABLE dirty_status OUTPUT_VARIABLE dirty OUTPUT_STRIP_TRAILING_WHITESPACE)
    execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${directory}" rev-parse --show-toplevel
        RESULT_VARIABLE root_status OUTPUT_VARIABLE git_root OUTPUT_STRIP_TRAILING_WHITESPACE)
    file(REAL_PATH "${directory}" expected_root)
    if(NOT revision_status EQUAL 0 OR NOT dirty_status EQUAL 0
       OR NOT root_status EQUAL 0 OR NOT git_root STREQUAL expected_root
       OR NOT revision STREQUAL VOXIDE_JUCE_REVISION OR NOT dirty STREQUAL "")
        message(FATAL_ERROR "JUCE_DIR must be a clean pinned checkout: ${VOXIDE_JUCE_REVISION}")
    endif()
endfunction()
