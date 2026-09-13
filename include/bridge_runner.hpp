#pragma once

#include <string>

#ifndef KEYBPM_VERSION
#define KEYBPM_VERSION "0.1.0"
#endif

namespace keybpm {

inline constexpr const char* kVersion = KEYBPM_VERSION;

// Spawn the Python analysis bridge. Child stdout is the payload; child stderr
// is forwarded to the parent stderr on success. Failures throw a single
// unprefixed message for main() to print as one "Error:" line.
std::string run_analysis(const char* argv0, const std::string& audio_file,
                         bool json_output, bool verbose = false);

}  // namespace keybpm
