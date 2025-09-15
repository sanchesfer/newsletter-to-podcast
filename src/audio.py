import subprocess
from pathlib import Path

def ffmpeg_join_and_normalize(wavs, out_mp3: Path):
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    list_file = out_mp3.parent / "concat.txt"
    with open(list_file, "w") as f:
        for w in wavs:
            f.write(f"file '{w}'\n")
    temp = out_mp3.parent / "temp_concat.wav"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(temp)], check=True)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(temp),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-b:a", "128k",
        str(out_mp3)
    ], check=True)
    return out_mp3
