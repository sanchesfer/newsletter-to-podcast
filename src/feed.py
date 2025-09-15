from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from pathlib import Path
import os
import sys

FEED_PATH = Path("feed.xml")
OUT_DIR = Path("output")

def load_or_init():
    fg = FeedGenerator()
    fg.load_extension('podcast')
    if FEED_PATH.exists():
        try:
            fg.parse(str(FEED_PATH))
            return fg
        except Exception:
            pass
    fg.title(os.getenv("PODCAST_TITLE", "Daily Roundup"))
    fg.link(href=os.getenv("HOST_PUBLIC_BASE", ""), rel='alternate')
    fg.description("Automated daily podcast from newsletters and RSS")
    fg.language(os.getenv("PODCAST_LANG", "en-US"))
    return fg

def episode_asset_url(tag: str) -> str:
    repo = os.getenv("GITHUB_REPOSITORY")
    return f"https://github.com/{repo}/releases/download/{tag}/episode.mp3"

def update_feed_for_today(tag: str):
    fg = load_or_init()
    fe = fg.add_entry()
    fe.id(tag)
    fe.title(f"Episode {tag}")
    fe.pubDate(datetime.now(timezone.utc))
    fe.enclosure(episode_asset_url(tag), 0, 'audio/mpeg')
    notes_path = OUT_DIR / "notes.md"
    if notes_path.exists():
        fe.description(notes_path.read_text(encoding='utf-8'))
    FEED_PATH.write_bytes(fg.rss_str(pretty=True))

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--update":
        tag = sys.argv[sys.argv.index("--tag") + 1]
        update_feed_for_today(tag)
