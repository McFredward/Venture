# Focused integration fixture: real API/chain/image code and Vulkan GPU work,
# with a scripted OpenXR host and source-format transport. No APK/JVM/FFmpeg.
cmake_minimum_required(VERSION 3.28)
project(VenturePassthroughTests LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
get_filename_component(venture_root "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
include(FetchContent)
FetchContent_Declare(doctest
  URL https://github.com/doctest/doctest/archive/2d0a9359a60c51affe2a9bebb1be1dca47868151.tar.gz
  URL_HASH SHA256=e64542c4ea68e9f381ccf6eae924cfdd652567c87c142d76fe92644fb4608149)
FetchContent_Declare(nlohmann_json
  URL https://github.com/nlohmann/json/archive/55f93686c01528224f448c19128836e7df245f72.tar.gz
  URL_HASH SHA256=67f4cdd9ca930c9c1e130af4a437c7fc98fab77a2846fc2d2a14b4943831f8ef)
FetchContent_Declare(openxr_headers
  URL https://github.com/KhronosGroup/OpenXR-SDK/archive/f2448a8797c85814aa892efc1ab8707900fbcc78.tar.gz
  URL_HASH SHA256=1681e0f6c9633c73117c2fc376d1fe71cbd6fdd2aeb896ed5854ff022aa82eaa
  SOURCE_SUBDIR venture-headers-only)
FetchContent_MakeAvailable(doctest nlohmann_json openxr_headers)
find_package(Vulkan REQUIRED COMPONENTS glslangValidator)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(generated "${CMAKE_CURRENT_BINARY_DIR}/generated")
foreach(shader IN ITEMS vert frag ms_frag)
  if(shader STREQUAL "vert")
    set(source "${venture_root}/src/runtime/xr/shaders/color.vert")
  else()
    set(source "${venture_root}/src/runtime/xr/shaders/color.frag")
  endif()
  set(defines)
  if(shader STREQUAL "ms_frag")
    set(defines -DMULTISAMPLE=1)
  endif()
  add_custom_command(OUTPUT "${generated}/color_${shader}.inc"
    COMMAND ${CMAKE_COMMAND} -E make_directory "${generated}"
    COMMAND Vulkan::glslangValidator -V --target-env vulkan1.0 ${defines} "${source}" -o "${generated}/color_${shader}.spv"
    COMMAND Python3::Interpreter "${venture_root}/tools/codegen/vk_spirv.py"
      "${generated}/color_${shader}.spv" "${generated}/color_${shader}.inc"
    DEPENDS "${source}" "${venture_root}/tools/codegen/vk_spirv.py" VERBATIM)
  list(APPEND generated_sources "${generated}/color_${shader}.inc")
endforeach()
add_executable(venture_passthrough_tests
  tests.cpp support.cpp ../test_main.cpp ${generated_sources}
  ${venture_root}/src/common/environment.cpp
  ${venture_root}/src/runtime/hle/openxr/passthrough.cpp
  ${venture_root}/src/runtime/hle/openxr/passthrough_images.cpp
  ${venture_root}/src/runtime/hle/openxr/state.cpp
  ${venture_root}/src/runtime/xr/color_images.cpp
  ${venture_root}/src/runtime/xr/color_space.cpp
  ${venture_root}/src/runtime/xr/guest_images.cpp)
target_include_directories(venture_passthrough_tests PRIVATE
  "${venture_root}/src" "${venture_root}/src/runtime" "${openxr_headers_SOURCE_DIR}/include" "${generated}")
target_link_libraries(venture_passthrough_tests PRIVATE doctest::doctest nlohmann_json::nlohmann_json Vulkan::Vulkan)
if(NOT WIN32)
  target_compile_definitions(venture_passthrough_tests PRIVATE DOCTEST_CONFIG_NO_POSIX_SIGNALS)
endif()
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(venture_passthrough_tests PRIVATE -ffunction-sections -fdata-sections)
  target_link_options(venture_passthrough_tests PRIVATE -Wl,--gc-sections)
endif()
enable_testing()
add_test(NAME passthrough COMMAND venture_passthrough_tests)
add_test(NAME xr_codegen COMMAND Python3::Interpreter "${venture_root}/tools/codegen/xr_generate.py"
  --registry "${openxr_headers_SOURCE_DIR}/specification/registry/xr.xml" --check)
