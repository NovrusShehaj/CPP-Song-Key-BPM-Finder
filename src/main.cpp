#include "bridge_runner.hpp"

#include <iostream>
#include <string>
#include <vector>

namespace {

void print_usage(const char* argv0, std::ostream& out) {
  out << "Usage: " << argv0 << " [options] <audio_file>\n"
      << "\n"
      << "Estimate tempo (BPM) and musical key of a regular audio file.\n"
      << "\n"
      << "Options:\n"
      << "  --json              Print a single JSON object on stdout\n"
      << "  -v, --verbose       Diagnostics and progress on stderr\n"
      << "  -h, --help          Show this help and exit\n"
      << "  --version           Print the program version and exit\n"
      << "\n"
      << "Environment:\n"
      << "  KEY_BPM_PYTHON        Python interpreter (default: python3)\n"
      << "  KEY_BPM_BRIDGE        Override path to PyBridge.py\n"
      << "  KEY_BPM_TIMEOUT_SEC   Child timeout in seconds (default: 120)\n"
      << "  KEY_BPM_MAX_BYTES     Maximum audio file size (default: 52428800)\n"
      << "  KEYBPM_DEBUG          If set, print runner diagnostics on stderr\n"
      << "\n"
      << "Formats: WAV/FLAC/OGG via soundfile; MP3 and others if ffmpeg is installed.\n"
      << "Platform: POSIX only (Linux CI-supported; macOS best-effort). Windows is not supported.\n";
}

}  // namespace

int main(int argc, char* argv[]) {
  bool json_output = false;
  bool verbose = false;
  std::vector<std::string> positionals;

  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--help" || arg == "-h") {
      print_usage(argv[0], std::cout);
      return 0;
    }
    if (arg == "--version") {
      std::cout << "Key-BpmFinder " << keybpm::kVersion << '\n';
      return 0;
    }
    if (arg == "--json") {
      json_output = true;
      continue;
    }
    if (arg == "-v" || arg == "--verbose") {
      verbose = true;
      continue;
    }
    if (arg == "--") {
      for (++i; i < argc; ++i) {
        positionals.emplace_back(argv[i]);
      }
      break;
    }
    if (!arg.empty() && arg[0] == '-') {
      std::cerr << "Unknown option: " << arg << '\n';
      print_usage(argv[0], std::cerr);
      return 2;
    }
    positionals.push_back(arg);
  }

  if (positionals.size() != 1) {
    print_usage(argv[0], std::cerr);
    return 2;
  }

  try {
    const std::string output =
        keybpm::run_analysis(argv[0], positionals[0], json_output, verbose);
    std::cout << output;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Error: " << error.what() << '\n';
    return 1;
  }
}
