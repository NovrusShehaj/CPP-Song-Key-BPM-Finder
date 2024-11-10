#include <pybind11/embed.h>
#include <pybind11/numpy.h>
#include <iostream>
#include <string>
#include <map>
#include <cmath>

namespace py = pybind11;
using namespace std;

std::string get_musical_key(double key_value) {
  std::map<int, std::string> key_map = {
    {0, "C major"},
    {1, "C# major"},
    {2, "D major"},
    {3, "D# major"},
    {4, "E major"},
    {5, "F major"},
    {6, "F# major"},
    {7, "G major"},
    {8, "G# major"},
    {9, "A major"},
    {10, "A# major"},
    {11, "B major"},
    {-1, "C minor"},
    {-2, "C# minor"},
    {-3, "D minor"},
    {-4, "D# minor"},
    {-5, "E minor"},
    {-6, "F minor"},
    {-7, "F# minor"},
    {-8, "G minor"},
    {-9, "G# minor"},
    {-10, "A minor"},
    {-11, "A# minor"},
    {-12, "B minor"}

  };

  int key_index = static_cast<int>(round(key_value * 12));
  return key_map[key_index];

}

int main(int argc, char *argv[]) {
  if (argc < 2) {
    cerr << "Usage: " << argv[0] << " <audio_file>" << endl;
    return 1;
  }

  const char* file_path = argv[1];

  py::scoped_interpreter guard{}; // Start the interpreter & keep it alive

  try {
    py::module librosa = py::module::import("librosa");
    py::module numpy = py::module::import("numpy");

    py::tuple result = librosa.attr("load")(file_path);
    py::array_t<float> y = result[0].cast<py::array_t<float>>();
    auto sr = result[1].cast<int>();

    auto tempo_result = librosa.attr("beat").attr("beat_track")(py::arg("y")=y, py::arg("sr")=sr);
    auto tempo = tempo_result.cast<double>();

    auto key = librosa.attr("core").attr("estimate_tuning")(py::arg("y")=y, py::arg("sr")=sr);

    cout << "BPM: " << tempo << endl;
    cout << "Key: " << get_musical_key(key.cast<double>()) << endl;

  } catch (const py::error_already_set& e) {
    cerr << "Error: " << e.what() << endl;
  }

  return 0;

}
