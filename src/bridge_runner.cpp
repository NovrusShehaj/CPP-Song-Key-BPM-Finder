#include "bridge_runner.hpp"

#include <array>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cstdint>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <filesystem>
#include <iostream>
#include <poll.h>
#include <spawn.h>
#include <stdexcept>
#include <string>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

#if defined(__APPLE__)
#include <mach-o/dyld.h>
#endif

extern char** environ;

namespace keybpm {
namespace {

constexpr int kDefaultTimeoutSec = 120;
constexpr std::uintmax_t kDefaultMaxBytes = 50ull * 1024ull * 1024ull;

class UniqueFd {
 public:
  UniqueFd() = default;
  explicit UniqueFd(int fd) : fd_(fd) {}
  UniqueFd(const UniqueFd&) = delete;
  UniqueFd& operator=(const UniqueFd&) = delete;

  UniqueFd(UniqueFd&& other) noexcept : fd_(other.fd_) { other.fd_ = -1; }
  UniqueFd& operator=(UniqueFd&& other) noexcept {
    if (this != &other) {
      close();
      fd_ = other.fd_;
      other.fd_ = -1;
    }
    return *this;
  }

  ~UniqueFd() { close(); }

  int get() const { return fd_; }

  void close() {
    if (fd_ >= 0) {
      ::close(fd_);
      fd_ = -1;
    }
  }

 private:
  int fd_ = -1;
};

struct SpawnFileActions {
  posix_spawn_file_actions_t actions{};
  bool initialized = false;

  SpawnFileActions() {
    const int rc = posix_spawn_file_actions_init(&actions);
    if (rc != 0) {
      throw std::runtime_error(std::string("Failed to init spawn file actions: ") +
                               std::strerror(rc));
    }
    initialized = true;
  }

  SpawnFileActions(const SpawnFileActions&) = delete;
  SpawnFileActions& operator=(const SpawnFileActions&) = delete;

  ~SpawnFileActions() {
    if (initialized) {
      posix_spawn_file_actions_destroy(&actions);
    }
  }
};

struct ChildGuard {
  pid_t pid = -1;
  bool reaped = false;

  ~ChildGuard() {
    if (pid > 0 && !reaped) {
      ::kill(pid, SIGKILL);
      int status = 0;
      while (::waitpid(pid, &status, 0) < 0 && errno == EINTR) {
      }
    }
  }
};

std::atomic<pid_t> g_child_pid{-1};

void forward_signal_to_child(int sig) {
  const pid_t pid = g_child_pid.load(std::memory_order_relaxed);
  if (pid > 0) {
    ::kill(pid, sig);
  }
}

void check_file_action(int rc, const char* what) {
  if (rc != 0) {
    throw std::runtime_error(std::string(what) + ": " + std::strerror(rc));
  }
}

void set_nonblocking(int fd) {
  const int flags = ::fcntl(fd, F_GETFL, 0);
  if (flags < 0 || ::fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) {
    throw std::runtime_error(std::string("Failed to set non-blocking pipe: ") +
                             std::strerror(errno));
  }
}

int env_positive_int(const char* name, int fallback) {
  const char* value = std::getenv(name);
  if (value == nullptr || value[0] == '\0') {
    return fallback;
  }
  try {
    const int parsed = std::stoi(value);
    if (parsed > 0) {
      return parsed;
    }
  } catch (...) {
  }
  return fallback;
}

std::uintmax_t env_positive_bytes(const char* name, std::uintmax_t fallback) {
  const char* value = std::getenv(name);
  if (value == nullptr || value[0] == '\0') {
    return fallback;
  }
  try {
    const unsigned long long parsed = std::stoull(value);
    if (parsed > 0) {
      return static_cast<std::uintmax_t>(parsed);
    }
  } catch (...) {
  }
  return fallback;
}

int default_timeout_sec() { return env_positive_int("KEY_BPM_TIMEOUT_SEC", kDefaultTimeoutSec); }

std::uintmax_t max_audio_bytes() {
  return env_positive_bytes("KEY_BPM_MAX_BYTES", kDefaultMaxBytes);
}

bool debug_enabled() {
  const char* value = std::getenv("KEYBPM_DEBUG");
  return value != nullptr && value[0] != '\0';
}

std::string trim_copy(std::string text) {
  const auto begin = text.find_first_not_of(" \t\r\n");
  if (begin == std::string::npos) {
    return {};
  }
  const auto end = text.find_last_not_of(" \t\r\n");
  return text.substr(begin, end - begin + 1);
}

std::string strip_error_prefix(std::string text) {
  text = trim_copy(std::move(text));
  const std::string prefix = "Error:";
  if (text.rfind(prefix, 0) == 0) {
    text = trim_copy(text.substr(prefix.size()));
  }
  return text;
}

std::filesystem::path executable_path(const char* argv0) {
#if defined(__linux__)
  std::error_code ec;
  const std::filesystem::path proc = std::filesystem::read_symlink("/proc/self/exe", ec);
  if (!ec && !proc.empty()) {
    return proc;
  }
#endif
#if defined(__APPLE__)
  char buffer[4096];
  uint32_t size = sizeof(buffer);
  if (_NSGetExecutablePath(buffer, &size) == 0) {
    std::error_code ec;
    std::filesystem::path resolved = std::filesystem::weakly_canonical(buffer, ec);
    if (!ec && !resolved.empty()) {
      return resolved;
    }
    return std::filesystem::absolute(buffer);
  }
#endif
  if (argv0 == nullptr || argv0[0] == '\0') {
    return std::filesystem::current_path();
  }
  return std::filesystem::absolute(std::filesystem::path(argv0));
}

bool is_bridge_script(const std::filesystem::path& candidate) {
  std::error_code ec;
  return std::filesystem::is_regular_file(candidate, ec);
}

std::filesystem::path find_bridge_script(const char* argv0) {
  if (const char* override_path = std::getenv("KEY_BPM_BRIDGE")) {
    if (override_path[0] != '\0') {
      const std::filesystem::path configured(override_path);
      if (is_bridge_script(configured)) {
        return configured;
      }
      throw std::runtime_error(std::string("KEY_BPM_BRIDGE is not a regular file: ") +
                               override_path);
    }
  }

  const std::filesystem::path exe = executable_path(argv0);
  const std::filesystem::path exe_dir = exe.parent_path();
  const std::vector<std::filesystem::path> candidates = {
      exe_dir / "PyBridge.py",
      exe_dir / "scripts" / "PyBridge.py",
      exe_dir.parent_path() / "share" / "keybpm" / "PyBridge.py",
      exe_dir.parent_path() / "scripts" / "PyBridge.py",
      std::filesystem::current_path() / "PyBridge.py",
      std::filesystem::current_path() / "scripts" / "PyBridge.py",
  };

  for (const auto& candidate : candidates) {
    if (is_bridge_script(candidate)) {
      return candidate;
    }
  }

  throw std::runtime_error(
      "Could not find PyBridge.py. Ensure scripts/PyBridge.py is available.");
}

struct ProcessResult {
  std::string stdout_text;
  std::string stderr_text;
  int exit_status = -1;
  int term_signal = 0;
  bool timed_out = false;
};

void read_available(int fd, std::string& dest, bool& eof) {
  std::array<char, 4096> buffer{};
  while (true) {
    const ssize_t nread = ::read(fd, buffer.data(), buffer.size());
    if (nread > 0) {
      dest.append(buffer.data(), static_cast<std::size_t>(nread));
      continue;
    }
    if (nread == 0) {
      eof = true;
      return;
    }
    if (errno == EINTR) {
      continue;
    }
    if (errno == EAGAIN || errno == EWOULDBLOCK) {
      return;
    }
    throw std::runtime_error(std::string("Failed to read child output: ") + std::strerror(errno));
  }
}

ProcessResult run_process_capture(const std::vector<std::string>& args, int timeout_sec) {
  if (args.empty()) {
    throw std::runtime_error("Internal error: empty process argument list.");
  }

  // posix_spawn requires mutable char* argv. The strings themselves are not modified.
  std::vector<char*> argv;
  argv.reserve(args.size() + 1);
  for (const auto& arg : args) {
    argv.push_back(const_cast<char*>(arg.c_str()));
  }
  argv.push_back(nullptr);

  int out_pipe[2];
  if (::pipe(out_pipe) != 0) {
    throw std::runtime_error("Failed to create stdout pipe for Python bridge process.");
  }
  UniqueFd out_read(out_pipe[0]);
  UniqueFd out_write(out_pipe[1]);

  int err_pipe[2];
  if (::pipe(err_pipe) != 0) {
    throw std::runtime_error("Failed to create stderr pipe for Python bridge process.");
  }
  UniqueFd err_read(err_pipe[0]);
  UniqueFd err_write(err_pipe[1]);
  set_nonblocking(out_read.get());
  set_nonblocking(err_read.get());

  SpawnFileActions file_actions;
  check_file_action(posix_spawn_file_actions_addclose(&file_actions.actions, out_read.get()),
                    "spawn addclose stdout read");
  check_file_action(posix_spawn_file_actions_addclose(&file_actions.actions, err_read.get()),
                    "spawn addclose stderr read");
  check_file_action(
      posix_spawn_file_actions_adddup2(&file_actions.actions, out_write.get(), STDOUT_FILENO),
      "spawn dup2 stdout");
  check_file_action(
      posix_spawn_file_actions_adddup2(&file_actions.actions, err_write.get(), STDERR_FILENO),
      "spawn dup2 stderr");
  check_file_action(posix_spawn_file_actions_addclose(&file_actions.actions, out_write.get()),
                    "spawn addclose stdout write");
  check_file_action(posix_spawn_file_actions_addclose(&file_actions.actions, err_write.get()),
                    "spawn addclose stderr write");

  pid_t pid = 0;
  const int spawn_result =
      posix_spawnp(&pid, argv[0], &file_actions.actions, nullptr, argv.data(), environ);

  out_write.close();
  err_write.close();

  if (spawn_result != 0) {
    throw std::runtime_error(std::string("Failed to start Python bridge process: ") +
                             std::strerror(spawn_result));
  }

  ChildGuard child;
  child.pid = pid;
  g_child_pid.store(pid, std::memory_order_relaxed);

  const auto previous_int = std::signal(SIGINT, forward_signal_to_child);
  const auto previous_term = std::signal(SIGTERM, forward_signal_to_child);

  ProcessResult result;
  bool out_eof = false;
  bool err_eof = false;
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(timeout_sec);

  try {
    while (!out_eof || !err_eof) {
      const auto now = std::chrono::steady_clock::now();
      if (now >= deadline) {
        result.timed_out = true;
        break;
      }
      const auto remain_ms =
          std::chrono::duration_cast<std::chrono::milliseconds>(deadline - now).count();

      pollfd fds[2];
      nfds_t count = 0;
      int out_index = -1;
      int err_index = -1;
      if (!out_eof) {
        fds[count] = pollfd{out_read.get(), POLLIN, 0};
        out_index = static_cast<int>(count);
        ++count;
      }
      if (!err_eof) {
        fds[count] = pollfd{err_read.get(), POLLIN, 0};
        err_index = static_cast<int>(count);
        ++count;
      }

      const int ready = ::poll(fds, count, static_cast<int>(remain_ms));
      if (ready < 0) {
        if (errno == EINTR) {
          continue;
        }
        throw std::runtime_error(std::string("Failed to poll Python bridge process: ") +
                                 std::strerror(errno));
      }
      if (ready == 0) {
        result.timed_out = true;
        break;
      }

      auto consume = [&](int index, UniqueFd& fd, std::string& dest, bool& eof) {
        if (index < 0) {
          return;
        }
        const short revents = fds[index].revents;
        if (revents & (POLLIN | POLLHUP | POLLERR | POLLNVAL)) {
          read_available(fd.get(), dest, eof);
          if (revents & (POLLHUP | POLLERR | POLLNVAL)) {
            eof = true;
          }
        }
      };
      consume(out_index, out_read, result.stdout_text, out_eof);
      consume(err_index, err_read, result.stderr_text, err_eof);
    }
  } catch (...) {
    std::signal(SIGINT, previous_int);
    std::signal(SIGTERM, previous_term);
    g_child_pid.store(-1, std::memory_order_relaxed);
    throw;
  }

  if (result.timed_out) {
    ::kill(pid, SIGKILL);
  }

  int status = 0;
  pid_t waited = -1;
  do {
    waited = ::waitpid(pid, &status, 0);
  } while (waited < 0 && errno == EINTR);
  child.reaped = waited == pid;
  g_child_pid.store(-1, std::memory_order_relaxed);
  std::signal(SIGINT, previous_int);
  std::signal(SIGTERM, previous_term);

  if (waited < 0) {
    throw std::runtime_error(std::string("Failed to wait for Python bridge process: ") +
                             std::strerror(errno));
  }

  if (WIFSIGNALED(status)) {
    result.term_signal = WTERMSIG(status);
    result.exit_status = -1;
  } else if (WIFEXITED(status)) {
    result.exit_status = WEXITSTATUS(status);
  } else {
    result.exit_status = -1;
  }
  return result;
}

void validate_audio_path(const std::filesystem::path& audio_path, const std::string& audio_file) {
  std::error_code ec;
  if (!std::filesystem::exists(audio_path, ec) || ec) {
    throw std::runtime_error("Audio file does not exist: " + audio_file);
  }
  if (std::filesystem::is_directory(audio_path, ec)) {
    throw std::runtime_error("Expected an audio file, but received a directory: " + audio_file);
  }
  if (!std::filesystem::is_regular_file(audio_path, ec)) {
    throw std::runtime_error("Expected a regular audio file: " + audio_file);
  }
  const auto size = std::filesystem::file_size(audio_path, ec);
  if (ec) {
    throw std::runtime_error("Unable to read audio file size: " + audio_file);
  }
  if (size == 0) {
    throw std::runtime_error("Audio file is empty: " + audio_file);
  }
  const auto limit = max_audio_bytes();
  if (size > limit) {
    throw std::runtime_error("Audio file exceeds size limit (" + std::to_string(limit) +
                             " bytes): " + audio_file);
  }
}

}  // namespace

std::string run_analysis(const char* argv0, const std::string& audio_file, bool json_output,
                         bool verbose) {
  const std::filesystem::path audio_path(audio_file);
  validate_audio_path(audio_path, audio_file);

  const std::filesystem::path bridge_script = find_bridge_script(argv0);
  const char* configured_python = std::getenv("KEY_BPM_PYTHON");
  const std::string python_command =
      (configured_python != nullptr && configured_python[0] != '\0') ? configured_python
                                                                      : "python3";
  const int timeout_sec = default_timeout_sec();

  if (verbose || debug_enabled()) {
    std::cerr << "Using Python: " << python_command << '\n';
    std::cerr << "Using bridge: " << bridge_script.string() << '\n';
    std::cerr << "Timeout seconds: " << timeout_sec << '\n';
  }

  std::vector<std::string> args = {python_command, bridge_script.string()};
  if (json_output) {
    args.emplace_back("--json");
  }
  if (verbose) {
    args.emplace_back("--verbose");
  }
  args.push_back(audio_file);

  const ProcessResult result = run_process_capture(args, timeout_sec);
  if (result.timed_out) {
    throw std::runtime_error("Audio analysis timed out after " + std::to_string(timeout_sec) +
                             " seconds.");
  }
  if (result.term_signal != 0) {
    throw std::runtime_error("Audio analysis failed: child terminated by signal " +
                             std::to_string(result.term_signal));
  }
  if (result.exit_status != 0) {
    const std::string message = strip_error_prefix(
        result.stderr_text.empty() ? result.stdout_text : result.stderr_text);
    throw std::runtime_error(message.empty() ? "Audio analysis failed." : message);
  }
  if (!result.stderr_text.empty()) {
    std::cerr << result.stderr_text;
    if (result.stderr_text.back() != '\n') {
      std::cerr << '\n';
    }
  }
  return result.stdout_text;
}

}  // namespace keybpm
