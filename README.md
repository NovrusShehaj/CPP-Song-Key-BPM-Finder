# C++ Song Key & BPM Finder

CPP-Song-Key-BPM-Finder is a C++ project that utilizes Python libraries to analyze audio files and determine their key and beats per minute (BPM). This project leverages the `librosa` library in Python for audio analysis and `pybind11` for embedding Python in C++.

## Project Structure
|- /
| |- /.vscode/ 
|   |- /c_cpp_properties.json 
|   |- /launch.json 
|   |- /settings.json 
|- /appmap.yml 
|- /key-bpm.cpp 
|- /key-bpm2.cpp
|- /PyBridge.py
|- /Key-BpmFinder 
|- /Key-BpmFinder2

## Prerequisites

- C++ compiler (e.g., `clang++`)
- Python 3.x
- `librosa` library
- `pybind11` library

## Setup

1. **Install Python dependencies:**

    ```sh
    pip install librosa pybind11
    ```

2. **Configure your C++ environment:**

    Ensure that your `.vscode/settings.json` is properly configured for your C++ compiler. Here is an example configuration:

    ```json
    {
      "C_Cpp_Runner.cCompilerPath": "clang",
      "C_Cpp_Runner.cppCompilerPath": "clang++",
      "C_Cpp_Runner.debuggerPath": "lldb",
      "C_Cpp_Runner.cStandard": "",
      "C_Cpp_Runner.cppStandard": "",
      "C_Cpp_Runner.msvcBatchPath": "",
      "C_Cpp_Runner.useMsvc": false,
      "C_Cpp_Runner.warnings": [
        "-Wall",
        "-Wextra",
        "-Wpedantic",
        "-Wshadow",
        "-Wformat=2",
        "-Wcast-align",
        "-Wconversion",
        "-Wsign-conversion",
        "-Wnull-dereference"
      ],
      "C_Cpp_Runner.msvcWarnings": [
        "/W4",
        "/permissive-",
        "/w14242",
        "/w14287",
        "/w14296",
        "/w14311",
        "/w14826",
        "/w44062",
        "/w44242",
        "/w14905",
        "/w14906",
        "/w14263",
        "/w44265",
        "/w14928"
      ],
      "C_Cpp_Runner.enableWarnings": true,
      "C_Cpp_Runner.warningsAsError": false,
      "C_Cpp_Runner.compilerArgs": [],
      "C_Cpp_Runner.linkerArgs": [],
      "C_Cpp_Runner.includePaths": [],
      "C_Cpp_Runner.includeSearch": [
        "*",
        "**/*"
      ],
      "C_Cpp_Runner.excludeSearch": [
        "**/build",
        "**/build/**",
        "**/.*",
        "**/.*/**",
        "**/.vscode",
        "**/.vscode/**"
      ],
      "C_Cpp_Runner.useAddressSanitizer": false,
      "C_Cpp_Runner.useUndefinedSanitizer": false,
      "C_Cpp_Runner.useLeakSanitizer": false,
      "C_Cpp_Runner.showCompilationTime": false,
      "C_Cpp_Runner.useLinkTimeOptimization": false,
      "C_Cpp_Runner.msvcSecureNoWarnings": false
    }
    ```

3. **Build the project:**

    Use the following command to compile the C++ files:

    ```sh
    clang++ -o Key-BpmFinder key-bpm.cpp -I/usr/include/python3.8 -lpython3.8
    clang++ -o Key-BpmFinder2 key-bpm2.cpp -I/usr/include/python3.8 -lpython3.8
    ```

## Usage

To analyze an audio file and determine its key and BPM, run the compiled executable with the path to the audio file as an argument:

```sh
./Key-BpmFinder <audio_file>

or

./Key-BpmFinder2 <audio_file>
```

## Files
- key-bpm.cpp: Contains the main logic for analyzing audio files using librosa and pybind11.
- key-bpm2.cpp: An alternative implementation that includes a function to convert the key value to a musical key.
- PyBridge.py: A Python script that defines the analyze_audio function used in the C++ code.

## Example
```sh
./Key-BpmFinder example.wav
```

## Output
```sh
BPM: 120.0
Key: 0.5
```

## License
This project is licensed under the MIT License.

This `README.md` file provides a comprehensive overview of the project, including setup instructions, usage examples, and a brief description of each file in the project.
