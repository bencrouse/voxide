# No evaluator subdirectories or alternative engines enter product linkage.
execute_process(COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/scripts/product_dependencies.py"
    --destination "${PROJECT_BINARY_DIR}/_deps" --cache "${VOXIDE_DEPENDENCY_CACHE}"
    OUTPUT_VARIABLE rubberband_source OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
add_library(voxide_rubberband STATIC "${rubberband_source}/single/RubberBandSingle.cpp")
target_include_directories(voxide_rubberband SYSTEM PUBLIC "${rubberband_source}")
target_link_libraries(voxide_rubberband PRIVATE "-framework Accelerate")
