import argparse
from pathlib import Path
import os

from src.gmail_fetch import gmail_service, list_messages, get_message, extract_email_html, guess_source
from src.cleaner import strip_html, fetch_and_readable, hash_key
from src.rss_fetch import fetch_rss_items
from src.summarizer import summarize, stitch_script
from src.tts import synthesize
from src.audio import ffmpeg_join_and_normalize

OUT_DIR = Path("output")


def build_items(gmail_label: str, since_days: int, max_items: int):
    items = []
    # Gmail
    svc = gmail_service(
        os.getenv("GMAIL_CLIENT_ID"),
        os.getenv("GMAIL_CLIENT_SECRET"),
        os.getenv("GMAIL_REFRESH_TOKEN"),
    )
    msgs = list_messages(svc, gmail_label, since_days=since_days)
    print(f"[info] Gmail returned {len(msgs)} messages for label={gmail_label} in last {since_days}d")
    for m in msgs[: max_items * 2]:
        full = get_message(svc, m["id"])  # id only
        headers = full.get("payload", {}).get("headers", [])
        src = guess_source(headers)
        html = extract_email_html(full)
        text = strip_html(html)
        title = next((h["value"] for h in headers if h.get("name", "").lower() == "subject"), "")
        items.append({"title": title, "text": text, "source": src, "link": ""})

    # (Optional) RSS — skip if you don’t want feeds
    # items.extend(fetch_rss_items())

    # Fetch article bodies for RSS links (no-op if RSS skipped)
    for it in items:
        if it.get("link") and not it.get("text"):
            it["text"] = fetch_and_readable(it["link"]) or it.get("text", "")

    # Deduplicate by title+source hash
    seen = set()
    dedup = []
    for it in items:
        h = hash_key((it.get("title") or "") + (it.get("source") or ""))
        if h in seen:
            continue
        seen.add(h)
        dedup.append(it)

    return dedup[:max_items]


def write_notes(items):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "notes.md", "w", encoding="utf-8") as f:
        f.write("# Sources\n\n")
        for i, it in enumerate(items, 1):
            f.write(f"{i}. {it.get('title','Untitled')} — {it.get('source','')}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="1d")  # NOTE: currently ignored in build_items (always 1 day)
    ap.add_argument("--max_items", type=int, default=12)
    ap.add_argument("--piper", required=True)
    ap.add_argument("--voice", required=True)
    args = ap.parse_args()

    label = os.getenv("GMAIL_LABEL", "Newsletters")
    lang = os.getenv("PODCAST_LANG", "en-US")

    items = build_items(label, since_days=1, max_items=args.max_items)
    print(f"[info] Items after dedupe: {len(items)}")

    for it in items:
        it["summary"] = summarize(it.get("text", ""))

    script = stitch_script(items, lang=lang) if items else "Welcome to your daily roundup. No new items today, see you tomorrow."
    (OUT_DIR / "script.md").write_text(script, encoding="utf-8")

    # TTS
    wav = OUT_DIR / "episode.wav"
    synthesize(script, wav, args.piper, args.voice)

    # Convert to MP3
    mp3 = OUT_DIR / "episode.mp3"
    ffmpeg_join_and_normalize([wav], mp3)

    # Write notes
    write_notes(items)


if __name__ == "__main__":
    main()
