cmake_minimum_required(VERSION 3.25)
project(NexusSim CXX)

set(CMAKE_CXX_STANDARD 20)

add_executable(engine src/main.cpp)

# Testing
include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/03597a01ee50ed33e9dfd640b249b4be3799d395.zip
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

enable_testing()
add_executable(engine_test tests/test_engine.cpp)
target_link_libraries(engine_test gtest_main)

include(GoogleTest)
gtest_discover_tests(engine_test)
