# src/audio.py
import subprocess
from pathlib import Path

def make_silence_wav(path: Path, seconds: float = 0.5, rate: int = 22050):
    """Create a mono WAV file of silence using ffmpeg."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        f"-i", f"anullsrc=r={rate}:cl=mono",
        "-t", f"{seconds}",
        str(path),
    ], check=True)
    return path

def ffmpeg_join_and_normalize(wavs, out_mp3: Path):
    out_mp3.parent.mkdir(parents=True, exist_ok=True)

    # If there is only one WAV, skip concat and normalize directly
    if len(wavs) == 1:
        inp = Path(wavs[0]).resolve()
        subprocess.run([
            "ffmpeg", "-y", "-i", str(inp),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-b:a", "128k",
            str(out_mp3)
        ], check=True)
        return out_mp3

    # Otherwise, concat multiple WAVs using absolute paths
    list_file = out_mp3.parent / "concat.txt"
    with open(list_file, "w") as f:
        for w in wavs:
            f.write(f"file '{Path(w).resolve()}'\n")

    temp = out_mp3.parent / "temp_concat.wav"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy", str(temp)
    ], check=True)

    subprocess.run([
        "ffmpeg", "-y", "-i", str(temp),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-b:a", "128k",
        str(out_mp3)
    ], check=True)

    return out_mp3