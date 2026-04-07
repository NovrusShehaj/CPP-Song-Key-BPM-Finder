#pragma once

#include <array>
#include <cstdlib>
#include <cstdio>
#include <filesystem>
#include <stdexcept>
#include <string>
#include <vector>

namespace keybpm {

inline std::string shell_escape(const std::string& input) {
  std::string escaped = "'";
  for (char ch : input) {
    if (ch == '\'') {
      escaped += "'\\''";
    } else {
      escaped += ch;
    }
  }
  escaped += "'";
  return escaped;
}

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

inline std::string run_command_capture(const std::string& command, int& exit_status) {
  std::array<char, 512> buffer{};
  std::string output;

  FILE* pipe = popen(command.c_str(), "r");
  if (pipe == nullptr) {
    throw std::runtime_error("Failed to start Python bridge process.");
  }

  while (fgets(buffer.data(), static_cast<int>(buffer.size()), pipe) != nullptr) {
    output += buffer.data();
  }

  exit_status = pclose(pipe);
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

  std::string command = shell_escape(python_command) + " " + shell_escape(bridge_script.string());
  if (json_output) {
    command += " --json";
  }
  command += " " + shell_escape(audio_file) + " 2>&1";

  int status = 0;
  const std::string output = run_command_capture(command, status);
  if (status != 0) {
    throw std::runtime_error(output.empty() ? "Audio analysis failed." : output);
  }

  return output;
}

}  // namespace keybpm
