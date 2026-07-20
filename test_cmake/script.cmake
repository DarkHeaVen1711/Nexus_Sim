include(FetchContent)
FetchContent_Declare(
  uWebSockets
  GIT_REPOSITORY https://github.com/uNetworking/uWebSockets.git
  GIT_TAG v20.46.0
)
FetchContent_GetProperties(uWebSockets)
message(STATUS "uwebsockets_SOURCE_DIR = ${uwebsockets_SOURCE_DIR}")
FetchContent_Populate(uWebSockets)
message(STATUS "uwebsockets_SOURCE_DIR after populate = ${uwebsockets_SOURCE_DIR}")
