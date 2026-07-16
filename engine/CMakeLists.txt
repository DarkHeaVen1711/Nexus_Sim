cmake_minimum_required(VERSION 3.25)
project(NexusSim CXX)

set(CMAKE_CXX_STANDARD 20)

include(FetchContent)

# GoogleTest
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/03597a01ee50ed33e9dfd640b249b4be3799d395.zip
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

# nlohmann/json
FetchContent_Declare(
    json
    URL https://github.com/nlohmann/json/releases/download/v3.11.2/json.tar.xz
)
FetchContent_MakeAvailable(json)

# FlatBuffers
FetchContent_Declare(
  flatbuffers
  GIT_REPOSITORY https://github.com/google/flatbuffers.git
  GIT_TAG v23.5.26
)
set(FLATBUFFERS_BUILD_TESTS OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(flatbuffers)

# uSockets (no CMakeLists — must be built manually from source)
FetchContent_Declare(
  uSockets
  GIT_REPOSITORY https://github.com/uNetworking/uSockets.git
  GIT_TAG v0.8.6
)
FetchContent_GetProperties(uSockets)
if(NOT usockets_POPULATED)
  FetchContent_Populate(uSockets)
endif()

# uWebSockets (header-only)
FetchContent_Declare(
  uWebSockets
  GIT_REPOSITORY https://github.com/uNetworking/uWebSockets.git
  GIT_TAG v20.46.0
)
FetchContent_GetProperties(uWebSockets)
if(NOT uwebsockets_POPULATED)
  FetchContent_Populate(uWebSockets)
endif()

# Build uSockets as a static C library from source
enable_language(C)
add_library(uSockets_lib STATIC
  ${usockets_SOURCE_DIR}/src/loop.c
  ${usockets_SOURCE_DIR}/src/context.c
  ${usockets_SOURCE_DIR}/src/socket.c
  ${usockets_SOURCE_DIR}/src/udp.c
  ${usockets_SOURCE_DIR}/src/bsd.c
  ${usockets_SOURCE_DIR}/src/eventing/epoll_kqueue.c
)
target_include_directories(uSockets_lib PUBLIC ${usockets_SOURCE_DIR}/src)
target_compile_definitions(uSockets_lib PUBLIC LIBUS_NO_SSL LIBUS_USE_EPOLL)

# Generate FlatBuffers C++ header
set(SCHEMA_DIR ${CMAKE_CURRENT_SOURCE_DIR}/schemas)
set(SCHEMA_FILE ${SCHEMA_DIR}/agent_delta.fbs)
set(SCHEMA_OUT_DIR ${CMAKE_CURRENT_BINARY_DIR}/generated)
file(MAKE_DIRECTORY ${SCHEMA_OUT_DIR})

add_custom_command(
    OUTPUT ${SCHEMA_OUT_DIR}/agent_delta_generated.h
    COMMAND flatc --cpp -o ${SCHEMA_OUT_DIR} ${SCHEMA_FILE}
    DEPENDS ${SCHEMA_FILE}
    COMMENT "Building C++ header for agent_delta.fbs"
)
add_custom_target(generate_fbs DEPENDS ${SCHEMA_OUT_DIR}/agent_delta_generated.h)

add_library(engine_lib 
    src/graph/GraphLoader.cpp
)
add_dependencies(engine_lib generate_fbs)
target_link_libraries(engine_lib PUBLIC nlohmann_json::nlohmann_json flatbuffers uSockets_lib)
target_include_directories(engine_lib PUBLIC src ${SCHEMA_OUT_DIR} ${uwebsockets_SOURCE_DIR}/src)

add_executable(engine src/main.cpp)
target_link_libraries(engine PRIVATE engine_lib z)

# Testing
enable_testing()
add_executable(engine_test tests/test_engine.cpp tests/test_graph.cpp tests/test_agent.cpp tests/test_quadtree.cpp)
target_link_libraries(engine_test gtest_main engine_lib)

include(GoogleTest)
gtest_discover_tests(engine_test)

# Benchmark
add_executable(bench_quadtree bench/bench_quadtree.cpp)
target_link_libraries(bench_quadtree PRIVATE engine_lib)
