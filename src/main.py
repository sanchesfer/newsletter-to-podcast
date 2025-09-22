# src/main.py
import argparse
import os
import re
import sys
import time
from pathlib import Path
from html import escape

from src.gmail_fetch import (
    gmail_service,
    list_messages,
    get_message,
    extract_email_html,
    guess_source,
)
from src.cleaner import (
    strip_html,
    fetch_and_readable,
    hash_key,
    extract_links_from_html,  # ensure this exists; if not, remove this import
)
from src.tts import synthesize, synthesize_paragraphs
from src.audio import ffmpeg_join_and_normalize, make_silence_wav
from src.llm_writer import generate_script_from_prompt  # prompt-oriented LLM script

OUT_DIR = Path("output")

# ---------------- Progress helpers ----------------
T0 = time.time()
def log(msg: str):
    dt = time.time() - T0
    print(f"[{dt:6.1f}s] {msg}")
# --------------------------------------------------


def parse_since(s: str) -> int:
    """
    Accepts '7d', '3', etc. Returns integer days. Defaults to 1 on parse issues.
    """
    if not s:
        return 1
    m = re.match(r"^\s*(\d+)\s*[dD]?\s*$", s)
    return int(m.group(1)) if m else 1


def build_items(gmail_label: str, since_days: int):
    """
    Build a list of items directly from Gmail newsletters only.
    No link expansion – just use the email subject + body text.
    """
    items = []
    svc = gmail_service(
        os.getenv("GMAIL_CLIENT_ID"),
        os.getenv("GMAIL_CLIENT_SECRET"),
        os.getenv("GMAIL_REFRESH_TOKEN"),
    )
    msgs = list_messages(svc, gmail_label, since_days=since_days)
    log(f"Gmail returned {len(msgs)} messages for label={gmail_label} in last {since_days}d")

    for idx, m in enumerate(msgs, 1):
        log(f"[{idx}/{len(msgs)}] Fetching message …")
        full = get_message(svc, m["id"])
        headers = full.get("payload", {}).get("headers", [])
        newsletter = (guess_source(headers) or "Newsletter").strip()
        html = extract_email_html(full)
        text = strip_html(html)
        title = next(
            (h["value"] for h in headers if h.get("name", "").lower() == "subject"),
            "",
        ) or "Untitled"
        if text.strip():
            items.append(
                {
                    "title": title.strip(),
                    "text": text.strip(),
                    "source": newsletter,
                    "link": "",  # no external links anymore
                }
            )
            log(f"[{idx}/{len(msgs)}] {newsletter}: added email body as item")

    log(f"Collected {len(items)} raw items")
    # Deduplicate by title+source hash
    seen, dedup = set(), []
    for it in items:
        h = hash_key((it.get("title") or "") + (it.get("source") or ""))
        if h in seen:
            continue
        seen.add(h)
        dedup.append(it)
    log(f"De-duplicated to {len(dedup)} items")
    return dedup


def write_notes_html(items, script_text=None):
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # First non-empty line of the script as overview
    overview = ""
    if script_text:
        for line in script_text.splitlines():
            if line.strip():
                overview = line.strip()
                break

    html = []
    html.append("<!doctype html>")
    html.append("<meta charset='utf-8'>")
    html.append("<div style='font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.45;font-size:16px;color:#111;'>")
    html.append("<h2 style='margin:0 0 12px'>Episode Notes</h2>")

    if overview:
        html.append(f"<p><strong>Overview:</strong> {escape(overview)}</p>")

    html.append("<p><strong>Stories covered today:</strong></p>")
    html.append("<ul style='margin:0 0 12px 20px'>")
    for it in items:
        title = escape(it.get("title", "Untitled"))
        src = escape(it.get("source", ""))
        html.append(f"<li>{title} <em>(via {src})</em></li>")
    html.append("</ul>")

    html.append("<hr style='border:none;border-top:1px solid #e5e7eb;margin:16px 0'>")
    html.append("<p>🎧 This episode was generated with AI from fintech newsletters.</p>")
    html.append("</div>")

    (OUT_DIR / "notes.html").write_text("\n".join(html), encoding="utf-8")


def split_script_into_blocks(script: str):
    """
    Split the script into logical blocks. Default: paragraphs separated by blank lines.
    """
    return [b.strip() for b in script.split("\n\n") if b.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="1d", help="How far back to fetch (e.g., 1d, 7d).")
    ap.add_argument("--piper", required=True, help="Path to piper binary (e.g., `which piper`).")
    ap.add_argument("--voice", required=True, help="Path to a Piper .onnx voice model.")
    ap.add_argument(
        "--prompt_file",
        default=None,
        help="Path to a text file with your prompt to steer the script (LLM_PROVIDER required).",
    )
    ap.add_argument(
        "--dry_run",
        action="store_true",
        help="Generate the script only (no TTS/audio), useful for iterating on prompts.",
    )
    ap.add_argument(
        "--llm_full_text",
        action="store_true",
        help="If set (with --prompt_file), send full newsletter bodies to the LLM and skip local summarization.",
    )
    ap.add_argument(
        "--pause_ms",
        type=int,
        default=700,
        help="Silence duration (milliseconds) inserted between paragraphs/items.",
    )
    ap.add_argument(
        "--extra_pause_after_open_ms",
        type=int,
        default=300,
        help="Additional silence after the first paragraph (the cold open), in milliseconds.",
    )
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Reuse output/script.md and render audio only (skip Gmail/LLM).",
    )
    args = ap.parse_args()

    # ---------- Fast path: resume from existing script ----------
    if args.resume:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        script_path = OUT_DIR / "script.md"
        if not script_path.exists():
            print("[resume] output/script.md not found. Run without --resume to generate the script first.", file=sys.stderr)
            sys.exit(1)

        script = script_path.read_text(encoding="utf-8").strip()
        log(f"[resume] Using existing script ({len(script)} chars)")
        blocks = split_script_into_blocks(script)

        # Synthesize per paragraph with pauses (longer pause after opener)
        log("Synthesizing TTS (Piper) per paragraph …")
        wav_paths = []
        for i, block in enumerate(blocks, 1):
            part_wav = OUT_DIR / f"part_{i:03d}.wav"
            synthesize(block, part_wav, args.piper, args.voice)
            wav_paths.append(part_wav)
            if i < len(blocks):
                sil = OUT_DIR / f"sil_{i:03d}.wav"
                extra = args.extra_pause_after_open_ms if i == 1 else 0
                seconds = max(0, args.pause_ms + extra) / 1000.0
                make_silence_wav(sil, seconds=seconds)
                wav_paths.append(sil)

        mp3 = OUT_DIR / "episode.mp3"
        log("Normalizing & encoding → MP3 …")
        ffmpeg_join_and_normalize(wav_paths, mp3)
        log(f"MP3 done: {mp3}")
        log("All done ✅")
        sys.exit(0)
    # -----------------------------------------------------------

    label = os.getenv("GMAIL_LABEL", "Newsletters")
    lang = os.getenv("PODCAST_LANG", "en-US")
    days = parse_since(args.since)

    # 1) Gather ALL items from Gmail
    items = build_items(label, since_days=days)
    log(f"Items ready for summarization: {len(items)}")

    if not items:
        script = "Welcome back to your daily fintech podcast. No new items today. See you tomorrow."
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "script.md").write_text(script, encoding="utf-8")
        log("Wrote script.md (no items)")
        if args.dry_run:
            log("Dry run complete (no items).")
            return
        # TTS single block
        log("Synthesizing TTS (Piper) per paragraph …")
        wav_paths = synthesize_paragraphs(
            script, OUT_DIR, args.piper, args.voice,
            pause_seconds=max(0, args.pause_ms) / 1000.0
        )
        mp3 = OUT_DIR / "episode.mp3"
        log("Normalizing & encoding → MP3 …")
        ffmpeg_join_and_normalize(wav_paths, mp3)
        log(f"MP3 done: {mp3}")
        write_notes_html(items, script)
        log("Wrote notes.html")
        return

    # 2) Summarize every item locally (unless LLM full-text mode is on)
    if args.prompt_file and args.llm_full_text:
        log("LLM full-text mode: skipping local summarization.")
    else:
        log("Summarizing items …")
        for i, it in enumerate(items, 1):
            it["summary"] = summarize(it.get("text", ""))
            if i % 5 == 0 or i == len(items):
                log(f"  summarized {i}/{len(items)}")

    # 3) Build the script: LLM-driven (prompt) if configured, else smart local fallback
    script = None
    if args.prompt_file:
        try:
            user_prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
            if user_prompt:
                log("Calling LLM to draft script …")
                script = generate_script_from_prompt(
                    items,
                    user_prompt=user_prompt,
                    language=lang,
                    prefer_full_text=args.llm_full_text,
                )
                log("LLM finished script.")
        except Exception as e:
            print(f"[warn] LLM script generation failed: {e}. Falling back to local builder.", file=sys.stderr)

    if not script:
        log("Falling back to naive concatenation …")
        body = []
        body.append("Welcome back to your fintech daily briefing.")  # simple intro
        for it in items:
            body.append(it.get("summary") or it.get("text") or it.get("title", ""))
        body.append("That’s all for today. See you tomorrow!")  # simple outro
        script = "\n\n".join(body)

    # 4) Write script and notes
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "script.md").write_text(script, encoding="utf-8")
    log(f"Wrote script.md ({len(script)} chars)")
    write_notes_html(items, script)
    log("Wrote notes.md")

    if args.dry_run:
        log("Dry run complete (script only).")
        return

    # 5) TTS → wav parts with pauses → mp3
    log("Synthesizing TTS (Piper) per paragraph …")
    # We want slightly longer pause after the opener
    blocks = split_script_into_blocks(script)
    wav_paths = []
    for i, block in enumerate(blocks, 1):
        part_wav = OUT_DIR / f"part_{i:03d}.wav"
        synthesize(block, part_wav, args.piper, args.voice)
        wav_paths.append(part_wav)
        if i < len(blocks):
            sil = OUT_DIR / f"sil_{i:03d}.wav"
            extra = args.extra_pause_after_open_ms if i == 1 else 0
            seconds = max(0, args.pause_ms + extra) / 1000.0
            make_silence_wav(sil, seconds=seconds)
            wav_paths.append(sil)

    mp3 = OUT_DIR / "episode.mp3"
    log("Normalizing & encoding → MP3 …")
    ffmpeg_join_and_normalize(wav_paths, mp3)
    log(f"MP3 done: {mp3}")

    log("All done ✅")


if __name__ == "__main__":
    main()