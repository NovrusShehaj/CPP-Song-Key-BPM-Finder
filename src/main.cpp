#include "bridge_runner.hpp"

#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
  bool json_output = false;
  std::string audio_file;

  if (argc == 2) {
    audio_file = argv[1];
  } else if (argc == 3 && std::string(argv[1]) == "--json") {
    json_output = true;
    audio_file = argv[2];
  } else {
    std::cerr << "Usage: " << argv[0] << " [--json] <audio_file>\n";
    return 1;
  }

  try {
    const std::string output = keybpm::run_analysis(argv[0], audio_file, json_output);
    std::cout << output;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Error: " << error.what() << '\n';
    return 1;
  }
}
