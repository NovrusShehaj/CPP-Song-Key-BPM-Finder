#pragma once

#include <array>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <stdexcept>
#include <string>
#include <vector>

#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>

extern char** environ;

namespace keybpm {

inline std::filesystem::path find_bridge_script(const char* argv0) {
  const std::filesystem::path executable_path =
      std::filesystem::absolute(std::filesystem::path(argv0));
  const std::vector<std::filesystem::path> candidates = {
      std::filesystem::current_path() / "scripts" / "PyBridge.py",
      std::filesystem::current_path() / "PyBridge.py",
      executable_path.parent_path() / "scripts" / "PyBridge.py",
      executable_path.parent_path() / "PyBridge.py",
      executable_path.parent_path().parent_path() / "scripts" / "PyBridge.py",
      executable_path.parent_path().parent_path() / "PyBridge.py",
  };

  for (const auto& candidate : candidates) {
    if (std::filesystem::exists(candidate)) {
      return candidate;
    }
  }

  throw std::runtime_error(
      "Could not find PyBridge.py. Ensure scripts/PyBridge.py is available.");
}

// Runs `args[0]` with the remaining entries as argv, bypassing the shell entirely so
// audio file paths and script paths never need escaping or quoting. stderr is merged
// into stdout, matching the previous popen-based behavior.
inline std::string run_process_capture(const std::vector<std::string>& args, int& exit_status) {
  std::vector<char*> argv;
  argv.reserve(args.size() + 1);
  for (const auto& arg : args) {
    argv.push_back(const_cast<char*>(arg.c_str()));
  }
  argv.push_back(nullptr);

  int pipe_fds[2];
  if (pipe(pipe_fds) != 0) {
    throw std::runtime_error("Failed to create pipe for Python bridge process.");
  }

  posix_spawn_file_actions_t file_actions;
  posix_spawn_file_actions_init(&file_actions);
  posix_spawn_file_actions_addclose(&file_actions, pipe_fds[0]);
  posix_spawn_file_actions_adddup2(&file_actions, pipe_fds[1], STDOUT_FILENO);
  posix_spawn_file_actions_adddup2(&file_actions, pipe_fds[1], STDERR_FILENO);
  posix_spawn_file_actions_addclose(&file_actions, pipe_fds[1]);

  pid_t pid = 0;
  const int spawn_result =
      posix_spawnp(&pid, argv[0], &file_actions, nullptr, argv.data(), environ);
  posix_spawn_file_actions_destroy(&file_actions);
  close(pipe_fds[1]);

  if (spawn_result != 0) {
    close(pipe_fds[0]);
    throw std::runtime_error(std::string("Failed to start Python bridge process: ") +
                              std::strerror(spawn_result));
  }

  std::string output;
  std::array<char, 4096> buffer{};
  ssize_t bytes_read = 0;
  while ((bytes_read = read(pipe_fds[0], buffer.data(), buffer.size())) > 0) {
    output.append(buffer.data(), static_cast<std::size_t>(bytes_read));
  }
  close(pipe_fds[0]);

  int status = 0;
  waitpid(pid, &status, 0);
  exit_status = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
  return output;
}

inline std::string run_analysis(const char* argv0, const std::string& audio_file,
                                bool json_output) {
  const std::filesystem::path audio_path = std::filesystem::path(audio_file);
  if (!std::filesystem::exists(audio_path)) {
    throw std::runtime_error("Audio file does not exist: " + audio_file);
  }
  if (std::filesystem::is_directory(audio_path)) {
    throw std::runtime_error("Expected an audio file, but received a directory: " +
                             audio_file);
  }

  const std::filesystem::path bridge_script = find_bridge_script(argv0);
  const char* configured_python = std::getenv("KEY_BPM_PYTHON");
  const std::string python_command =
      (configured_python != nullptr && configured_python[0] != '\0')
          ? configured_python
          : "python3";

  std::vector<std::string> args = {python_command, bridge_script.string()};
  if (json_output) {
    args.push_back("--json");
  }
  args.push_back(audio_file);

  int status = 0;
  const std::string output = run_process_capture(args, status);
  if (status != 0) {
    throw std::runtime_error(output.empty() ? "Audio analysis failed." : output);
  }

  return output;
}

}  // namespace keybpm
