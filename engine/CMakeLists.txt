cmake_minimum_required(VERSION 3.25)
project(NexusSim CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_POLICY_VERSION_MINIMUM 3.5)

option(ENABLE_TESTING "Build tests and benchmarks" ON)

if(WIN32 AND NOT MINGW)
  add_compile_definitions(PRTL_OSVERSIONINFOW=void*)
  add_compile_definitions(_WIN32_WINNT=0x0601)
  add_compile_definitions("NET_LUID=unsigned __int64")
  add_compile_definitions(IF_MAX_STRING_SIZE=256)
  add_compile_definitions(RRF_RT_REG_SZ=0x00000002)
  add_compile_definitions(IP_RECVTOS=40)
  add_compile_definitions(IPV6_RECVTCLASS=40)
  add_compile_options(-include winerror.h)
endif()







include(FetchContent)

# GoogleTest (only when testing enabled — MinGW Win32 threads lacks <mutex>)
if(ENABLE_TESTING)
  FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.15.2
  )
  set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
  FetchContent_MakeAvailable(googletest)
endif()

# nlohmann/json
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.2
)
FetchContent_MakeAvailable(json)

# ZLIB
find_package(ZLIB)
if(NOT ZLIB_FOUND)
  FetchContent_Declare(
    zlib
    GIT_REPOSITORY https://github.com/madler/zlib.git
    GIT_TAG v1.3.1
  )
  FetchContent_MakeAvailable(zlib)
  set(ZLIB_LIBRARIES zlibstatic)
  set(ZLIB_INCLUDE_DIRS ${zlib_SOURCE_DIR} ${zlib_BINARY_DIR})
endif()

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
  GIT_SUBMODULES ""
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
  GIT_SUBMODULES ""
)
FetchContent_GetProperties(uWebSockets)
if(NOT uwebsockets_POPULATED)
  FetchContent_Populate(uWebSockets)
endif()


# Build uSockets as a static C library from source
enable_language(C)

if(WIN32)
  find_library(LIBUV_LIBRARY uv)
  if(LIBUV_LIBRARY)
    message(STATUS "Using system libuv: ${LIBUV_LIBRARY}")
  else()
    FetchContent_Declare(
      libuv
      GIT_REPOSITORY https://github.com/libuv/libuv.git
      GIT_TAG v1.48.0
      GIT_SUBMODULES ""
    )
    set(libuv_BUILD_TESTING OFF CACHE BOOL "" FORCE)
    set(LIBUV_BUILD_TESTS OFF CACHE BOOL "" FORCE)
    set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(libuv)
    set(LIBUV_LIBRARY uv_a)
  endif()

  add_library(uSockets_lib STATIC
    ${usockets_SOURCE_DIR}/src/loop.c
    ${usockets_SOURCE_DIR}/src/context.c
    ${usockets_SOURCE_DIR}/src/socket.c
    ${usockets_SOURCE_DIR}/src/udp.c
    ${usockets_SOURCE_DIR}/src/bsd.c
    ${usockets_SOURCE_DIR}/src/eventing/libuv.c
  )
  target_link_libraries(uSockets_lib PUBLIC ${LIBUV_LIBRARY} ws2_32 iphlpapi userenv psapi)
  target_compile_definitions(uSockets_lib PUBLIC LIBUS_NO_SSL LIBUS_USE_LIBUV)
else()
  add_library(uSockets_lib STATIC
    ${usockets_SOURCE_DIR}/src/loop.c
    ${usockets_SOURCE_DIR}/src/context.c
    ${usockets_SOURCE_DIR}/src/socket.c
    ${usockets_SOURCE_DIR}/src/udp.c
    ${usockets_SOURCE_DIR}/src/bsd.c
    ${usockets_SOURCE_DIR}/src/eventing/epoll_kqueue.c
  )
  target_compile_definitions(uSockets_lib PUBLIC LIBUS_NO_SSL LIBUS_USE_EPOLL)
endif()

if(WIN32)
  find_path(LIBUV_INCLUDE_DIR uv.h)
  if(LIBUV_INCLUDE_DIR)
    target_include_directories(uSockets_lib PUBLIC ${usockets_SOURCE_DIR}/src ${LIBUV_INCLUDE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/src)
  else()
    target_include_directories(uSockets_lib PUBLIC ${usockets_SOURCE_DIR}/src ${libuv_SOURCE_DIR}/include ${CMAKE_CURRENT_SOURCE_DIR}/src)
  endif()
else()
  target_include_directories(uSockets_lib PUBLIC ${usockets_SOURCE_DIR}/src)
endif()



# Generate FlatBuffers C++ header
set(SCHEMA_DIR ${CMAKE_CURRENT_SOURCE_DIR}/schemas)
set(SCHEMA_FILE ${SCHEMA_DIR}/agent_delta.fbs)
set(SCHEMA_OUT_DIR ${CMAKE_CURRENT_BINARY_DIR}/generated)
file(MAKE_DIRECTORY ${SCHEMA_OUT_DIR})

add_custom_command(
    OUTPUT ${SCHEMA_OUT_DIR}/agent_delta_generated.h
    COMMAND $<TARGET_FILE:flatc> --cpp -o ${SCHEMA_OUT_DIR} ${SCHEMA_FILE}
    DEPENDS ${SCHEMA_FILE}
    COMMENT "Building C++ header for agent_delta.fbs"
)
add_custom_target(generate_fbs DEPENDS ${SCHEMA_OUT_DIR}/agent_delta_generated.h)

add_library(engine_lib 
    src/graph/GraphLoader.cpp
)
add_dependencies(engine_lib generate_fbs)
target_link_libraries(engine_lib PUBLIC nlohmann_json::nlohmann_json flatbuffers uSockets_lib)
target_include_directories(engine_lib PUBLIC src ${SCHEMA_OUT_DIR} ${uwebsockets_SOURCE_DIR}/src ${ZLIB_INCLUDE_DIRS})

add_executable(engine src/main.cpp)
target_link_libraries(engine PRIVATE engine_lib ${ZLIB_LIBRARIES})

# Testing
if(ENABLE_TESTING)
  enable_testing()
  add_executable(engine_test tests/test_engine.cpp tests/test_graph.cpp tests/test_agent.cpp tests/test_quadtree.cpp tests/test_signal.cpp tests/test_od_spawner.cpp)
  target_link_libraries(engine_test gtest_main engine_lib)

  include(GoogleTest)
  gtest_discover_tests(engine_test)

  # Benchmark
  add_executable(bench_quadtree bench/bench_quadtree.cpp)
  target_link_libraries(bench_quadtree PRIVATE engine_lib)
endif()
