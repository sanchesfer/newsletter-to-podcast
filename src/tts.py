# src/tts.py
from pathlib import Path
import subprocess
from typing import List
from src.audio import make_silence_wav  # this should already exist in audio.py

def synthesize(text: str, out_wav: Path, piper_bin: str, voice_path: str):
    """Legacy single-file synthesis used by main --resume fast path."""
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [piper_bin, "-m", str(voice_path), "-f", str(out_wav)]
    subprocess.run(cmd, input=text.encode("utf-8"), check=True)
    return out_wav

def _run_piper(text: str, out_wav: Path, piper_bin: str, voice_path: str):
    """Call Piper to synthesize `text` into `out_wav`."""
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        piper_bin,
        "-m", str(voice_path),
        "-f", str(out_wav),
    ]
    subprocess.run(cmd, input=text.encode("utf-8"), check=True)
    return out_wav

def synthesize_paragraphs(
    text: str,
    out_dir: Path,
    piper_bin: str,
    voice_path: str,
    pause_seconds: float = 2.0,
) -> List[Path]:
    """
    Split the script into paragraphs.
    - One WAV per paragraph.
    - Insert silence (pause_seconds) between paragraphs.
    - Return the list of WAV files.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    wav_paths: List[Path] = []

    for i, block in enumerate(blocks, 1):
        part_wav = out_dir / f"part_{i:03d}.wav"
        _run_piper(block, part_wav, piper_bin, voice_path)
        wav_paths.append(part_wav)

        # add silence between paragraphs
        if i < len(blocks):
            sil = out_dir / f"sil_{i:03d}.wav"
            make_silence_wav(sil, seconds=pause_seconds)
            wav_paths.append(sil)

    return wav_paths