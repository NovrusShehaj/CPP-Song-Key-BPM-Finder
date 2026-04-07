cmake_minimum_required(VERSION 3.16)
project(CPPSongKeyBPMFinder VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(Key-BpmFinder src/main.cpp)

target_include_directories(
  Key-BpmFinder
  PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/include")

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(Key-BpmFinder PRIVATE -Wall -Wextra -Wpedantic)
elseif(MSVC)
  target_compile_options(Key-BpmFinder PRIVATE /W4)
endif()

add_custom_command(
  TARGET Key-BpmFinder
  POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${CMAKE_SOURCE_DIR}/scripts/PyBridge.py"
          "$<TARGET_FILE_DIR:Key-BpmFinder>/PyBridge.py")
