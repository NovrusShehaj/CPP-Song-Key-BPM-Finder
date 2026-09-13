cmake_minimum_required(VERSION 3.16)
project(CPPSongKeyBPMFinder VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# The process runner uses posix_spawnp/poll/waitpid. Windows/MSVC is not supported.
if(WIN32)
  message(FATAL_ERROR "Key-BpmFinder is POSIX-only (Linux/macOS). Windows is not supported.")
endif()

option(KEYBPM_SANITIZE "Enable AddressSanitizer and UndefinedBehaviorSanitizer" OFF)

add_executable(Key-BpmFinder
  src/main.cpp
  src/bridge_runner.cpp)

target_include_directories(
  Key-BpmFinder
  PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/include")

target_compile_definitions(
  Key-BpmFinder
  PRIVATE
    "KEYBPM_VERSION=\"${PROJECT_VERSION}\"")

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(Key-BpmFinder PRIVATE -Wall -Wextra -Wpedantic)
  if(KEYBPM_SANITIZE)
    target_compile_options(
      Key-BpmFinder
      PRIVATE
        -fsanitize=address,undefined
        -fno-omit-frame-pointer)
    target_link_options(
      Key-BpmFinder
      PRIVATE
        -fsanitize=address,undefined)
  endif()
endif()

add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/PyBridge.py"
  COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${CMAKE_SOURCE_DIR}/scripts/PyBridge.py"
          "$<TARGET_FILE_DIR:Key-BpmFinder>/PyBridge.py"
  DEPENDS "${CMAKE_SOURCE_DIR}/scripts/PyBridge.py")

add_custom_target(
  copy_pybridge ALL
  DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/PyBridge.py")

include(GNUInstallDirs)
install(TARGETS Key-BpmFinder RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES scripts/PyBridge.py DESTINATION ${CMAKE_INSTALL_DATADIR}/keybpm)
