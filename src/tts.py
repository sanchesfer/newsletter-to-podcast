# src/tts.py
import subprocess
from pathlib import Path
from typing import List
from .audio import make_silence_wav  # keep if you use synthesize_paragraphs

def _run_piper(
    text: str,
    out_wav: Path,
    piper_bin: str,
    voice_path: str,
    length_scale: float = 1.0,          # 1.0 normal; >1.0 slower; <1.0 faster
    sentence_silence_ms: int = 0,       # extra pause (ms) after sentences
):
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        piper_bin,
        "-m", str(voice_path),
        "-f", str(out_wav),
        "--length-scale", str(length_scale),
    ]
    if sentence_silence_ms and sentence_silence_ms > 0:
        cmd += ["--sentence-silence", str(int(sentence_silence_ms))]

    # IMPORTANT: do NOT pass "-s" here (that's SPEAKER index)
    subprocess.run(cmd, input=text.encode("utf-8"), check=True)

def synthesize_paragraphs(
    text: str,
    out_dir: Path,
    piper_bin: str,
    voice_path: str,
    pause_seconds: float = 2.0,
    length_scale: float = 1.0,
    sentence_silence_ms: int = 0,
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
        _run_piper(
            block,
            part_wav,
            piper_bin,
            voice_path,
            length_scale=length_scale,
            sentence_silence_ms=sentence_silence_ms,
        )
        wav_paths.append(part_wav)

        if i < len(blocks):
            sil = out_dir / f"sil_{i:03d}.wav"
            make_silence_wav(sil, seconds=pause_seconds)
            wav_paths.append(sil)

    return wav_paths