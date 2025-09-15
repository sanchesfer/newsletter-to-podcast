import subprocess
from pathlib import Path

def synthesize(text: str, out_wav: Path, piper_bin: str, voice_path: str, speaking_rate: float = 1.0):
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        piper_bin,
        "-m", voice_path,
        "-f", str(out_wav),
    ]
    subprocess.run(cmd, input=text.encode("utf-8"), check=True)
    return out_wav
