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

add_library(engine_lib 
    src/graph/GraphLoader.cpp
)
target_link_libraries(engine_lib PRIVATE nlohmann_json::nlohmann_json)
target_include_directories(engine_lib PUBLIC src)

add_executable(engine src/main.cpp)
target_link_libraries(engine PRIVATE engine_lib)

# Testing
enable_testing()
add_executable(engine_test tests/test_engine.cpp tests/test_graph.cpp)
target_link_libraries(engine_test gtest_main engine_lib)

include(GoogleTest)
gtest_discover_tests(engine_test)
