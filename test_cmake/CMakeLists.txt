cmake_minimum_required(VERSION 3.25)

include(FetchContent)
FetchContent_Declare(
  uWebSockets
  GIT_REPOSITORY https://github.com/uNetworking/uWebSockets.git
  GIT_TAG v20.46.0
)
FetchContent_MakeAvailable(uWebSockets)
FetchContent_GetProperties(uWebSockets)
message(WARNING "uwebsockets_SOURCE_DIR = ${uwebsockets_SOURCE_DIR}")
project(test)
