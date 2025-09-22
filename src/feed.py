# src/feed.py
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from pathlib import Path
from html import escape
import os
import sys

FEED_PATH = Path("feed.xml")
OUT_DIR = Path("output")
AUDIO_NAME = "episode.mp3"


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _today_title() -> str:
    """Return 'Month Day Year' (e.g., 'September 22 2025') in UTC."""
    now = datetime.now(timezone.utc)
    return now.strftime("%B %-d %Y") if os.name != "nt" else now.strftime("%B %#d %Y")


def load_or_init() -> FeedGenerator:
    """
    Initialize or load feed.xml and set core channel metadata.
    Safe to call repeatedly.
    """
    fg = FeedGenerator()
    fg.load_extension("podcast")  # enables iTunes/Podcast tags

    # Try to parse existing feed to preserve history
    if FEED_PATH.exists():
        try:
            fg.parse(str(FEED_PATH))
            # Even when parsed, refresh channel-level values from env if present
        except Exception:
            pass

    # Channel metadata (idempotent / will set or overwrite)
    podcast_title = _env("PODCAST_TITLE", "Fintech Daily Briefing")
    podcast_desc = _env(
        "PODCAST_DESCRIPTION",
        "AI-generated daily fintech podcast built from trusted newsletters. Canada/Brazil/BNPL prioritized.",
    )
    podcast_lang = _env("PODCAST_LANG", "en-US")
    public_link = _env("HOST_PUBLIC_BASE", "")  # a public homepage for your show (e.g., Pages URL)

    fg.title(podcast_title)
    if public_link:
        fg.link(href=public_link, rel="alternate")
    fg.description(podcast_desc)
    fg.language(podcast_lang)

    # iTunes/Podcast channel tags
    # Owner & author
    owner_name = _env("PODCAST_OWNER_NAME")
    owner_email = _env("PODCAST_OWNER_EMAIL")
    author = _env("PODCAST_AUTHOR", owner_name or "Fintech Daily Briefing")

    if author:
        fg.podcast.itunes_author(author)
    if owner_name or owner_email:
        fg.podcast.itunes_owner(name=owner_name or "", email=owner_email or "")

    # Category (optional)
    category = _env("PODCAST_CATEGORY")  # e.g., "News"
    if category:
        fg.podcast.itunes_category(category)

    # Explicit flag
    explicit = _env("PODCAST_EXPLICIT", "no").lower()  # "yes"/"no"/"clean"
    fg.podcast.itunes_explicit(explicit)

    # Cover art
    cover_url = _env("PODCAST_COVER_URL")  # e.g., https://.../cover.jpg
    if cover_url:
        # Channel-level image (itunes:image)
        fg.podcast.itunes_image(cover_url)

    return fg


def episode_asset_url(tag: str) -> str:
    """
    Points to the GitHub Release asset for this episode by tag.
    """
    repo = _env("GITHUB_REPOSITORY")  # "owner/repo" provided by GitHub Actions
    return f"https://github.com/{repo}/releases/download/{tag}/{AUDIO_NAME}"


def _read_description_html() -> str:
    """
    Prefer notes.html for rich HTML; fallback to notes.md (escaped into <pre>).
    """
    notes_html = OUT_DIR / "notes.html"
    if notes_html.exists():
        return notes_html.read_text(encoding="utf-8")

    notes_md = OUT_DIR / "notes.md"
    if notes_md.exists():
        md = notes_md.read_text(encoding="utf-8")
        # Simple safe fallback: wrap MD in <pre> so it renders legibly
        return f"<pre>{escape(md)}</pre>"

    # Final fallback
    return "<p>Episode notes unavailable.</p>"


def update_feed_for_today(tag: str, *, title: str | None = None, summary_html: str | None = None) -> None:
    """
    Add a new episode item:
    - title: defaults to 'Month Day Year' (e.g., 'September 22 2025')
    - description: notes.html (or provided summary_html) for Spotify
    - enclosure: points to GitHub Release asset for this tag
    """
    fg = load_or_init()

    fe = fg.add_entry()
    fe.id(tag)

    # Title: Month Day Year (no comma), e.g., "September 22 2025"
    episode_title = title or _today_title()
    fe.title(episode_title)

    # Pub date now (UTC)
    fe.pubDate(datetime.now(timezone.utc))

    # Description HTML
    desc_html = summary_html if summary_html is not None else _read_description_html()
    fe.description(desc_html)

    # Enclosure (audio)
    audio_url = episode_asset_url(tag)
    # set a real byte length if local file exists; else 0 is acceptable
    audio_path = OUT_DIR / AUDIO_NAME
    enclosure_len = audio_path.stat().st_size if audio_path.exists() else 0
    fe.enclosure(audio_url, enclosure_len, "audio/mpeg")

    # Per-episode iTunes image (optional: fallback to channel cover if not set)
    episode_image = _env("EPISODE_IMAGE_URL") or _env("PODCAST_COVER_URL")
    if episode_image:
        fe.podcast.itunes_image(episode_image)

    # Save feed
    FEED_PATH.write_bytes(fg.rss_str(pretty=True))


if __name__ == "__main__":
    # Usage:
    #   python -m src.feed --update --tag <TAG> [--title "September 22 2025"]
    if "--update" in sys.argv and "--tag" in sys.argv:
        tag = sys.argv[sys.argv.index("--tag") + 1]
        # Optional title override
        t = None
        if "--title" in sys.argv:
            t = sys.argv[sys.argv.index("--title") + 1]
        update_feed_for_today(tag, title=t)