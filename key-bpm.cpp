#include <pybind11/embed.h>
#include <pybind11/numpy.h>
#include <iostream>
#include <string>
#include <cstdlib>

using namespace std;

namespace py = pybind11;

void analyze_audio(const string& file_path) {
  // Set the PYTHONHOME enviroment variable to the path of your Python interpreter
  //setenv("PYTHONHOME", "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3", 1);

  // Initialize the interpreter with correct arguments
  //const char* argv[] = {"python3", "-c", "import sys; print(sys.executable)"};

  py::scoped_interpreter guard{}; // Start the interpreter and keep it alive

  try {
    py::module librosa = py::module::import("librosa");
    py::module numpy = py::module::import("numpy");

    py::tuple result = librosa.attr("load")(file_path);
    py::array y = result[0].cast<py::array>();
    auto sr = result[1].cast<int>();

    /*
    auto result = librosa.attr("load")(file_path);
    auto y = result[0];
    auto sr = result[1];
    */
    //auto y = librosa.attr("load")(file_path).attr("0");
    //auto sr = librosa.attr("load")(file_path).attr("1");

    auto tempo = librosa.attr("beat").attr("tempo")(py::arg("y")=y, py::arg("sr")=sr);
    auto key = librosa.attr("core").attr("estimate_tuning")(py::arg("y")=y, py::arg("sr")=sr);

    cout << "BPM: " << tempo.cast<double>() << endl;
    cout << "Key: " << key.cast<double>() << endl;

  } catch (const py::error_already_set& e){
    cerr << "Error: " << e.what() << endl;
  }
  /*catch (const exception& e) {
    cerr << "Error: " << e.what() << endl;
  }*/

  //py::finalize_interpreter(); // Finalize the interpreter 

}


int main(int argc, char* argv[]) {
  if (argc != 2) {
    cerr << "Usage: " << argv[0] << " <audio_file>" << endl;
    return 1;
  }

  string file_path = argv[1];
  analyze_audio(file_path);

  return 0;

}
