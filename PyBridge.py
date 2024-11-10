import librosa

def analyze_audio(file_path):
    y, sr = librosa.load(file_path)
    tempo, _ = librosa.beat.beat_track(y, sr=sr)
    key = librosa.core.estimate_tuning(y, sr=sr)
    return tempo, key


