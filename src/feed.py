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
    # Windows uses %#d, others use %-d
    day_fmt = "%#d" if os.name == "nt" else "%-d"
    try:
        return now.strftime(f"%B {day_fmt} %Y")
    except ValueError:
        # Fallback if platform doesn't support the flag
        return now.strftime("%B %d %Y")


def _public_base() -> str:
    """
    Public homepage for the show (channel <link>).
    Priority:
      1) HOST_PUBLIC_BASE (env/secret)
      2) Derived GitHub Pages URL from GITHUB_REPOSITORY
      3) Final fallback to example.com (to satisfy feedgen requirement)
    """
    base = _env("HOST_PUBLIC_BASE")
    if base:
        return base.rstrip("/") + "/"

    repo = _env("GITHUB_REPOSITORY")  # e.g., "owner/repo"
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}/"

    return "https://example.com/"


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
        except Exception:
            pass

    # Channel metadata (idempotent / will set or overwrite)
    podcast_title = _env("PODCAST_TITLE", "Fintech Daily Briefing")
    podcast_desc = _env(
        "PODCAST_DESCRIPTION",
        "AI-generated daily fintech podcast built from trusted newsletters. Canada/Brazil/BNPL prioritized.",
    )
    podcast_lang = _env("PODCAST_LANG", "en-US")

    fg.title(podcast_title)
    fg.link(href=_public_base(), rel="alternate")  # <-- always set channel link
    fg.description(podcast_desc)
    fg.language(podcast_lang)

    # iTunes/Podcast channel tags
    owner_name = _env("PODCAST_OWNER_NAME")
    owner_email = _env("PODCAST_OWNER_EMAIL")
    author = _env("PODCAST_AUTHOR", owner_name or "Fintech Daily Briefing")

    if author:
        fg.podcast.itunes_author(author)
    if owner_name or owner_email:
        fg.podcast.itunes_owner(name=owner_name or "", email=owner_email or "")

    category = _env("PODCAST_CATEGORY")  # e.g., "News"
    if category:
        fg.podcast.itunes_category(category)

    explicit = _env("PODCAST_EXPLICIT", "no").lower()  # "yes"/"no"/"clean"
    fg.podcast.itunes_explicit(explicit)

    cover_url = _env("PODCAST_COVER_URL")  # e.g., https://.../cover.jpg
    if cover_url:
        fg.podcast.itunes_image(cover_url)

    return fg


def episode_asset_url(tag: str) -> str:
    """URL to the GitHub Release asset for this episode by tag."""
    repo = _env("GITHUB_REPOSITORY")  # "owner/repo" provided by GitHub Actions
    return f"https://github.com/{repo}/releases/download/{tag}/{AUDIO_NAME}"


def _read_description_html() -> str:
    """
    Prefer notes.html for rich HTML; fallback to notes.md (escaped).
    """
    notes_html = OUT_DIR / "notes.html"
    if notes_html.exists():
        return notes_html.read_text(encoding="utf-8")

    notes_md = OUT_DIR / "notes.md"
    if notes_md.exists():
        md = notes_md.read_text(encoding="utf-8")
        return f"<pre>{escape(md)}</pre>"

    return "<p>Episode notes unavailable.</p>"


def update_feed_for_today(tag: str, *, title: str | None = None, summary_html: str | None = None) -> None:
    """
    Add a new episode item:
    - title: defaults to 'Month Day Year'
    - description: notes.html (or provided summary_html) for Spotify
    - enclosure: GitHub Release asset for this tag
    """
    fg = load_or_init()

    fe = fg.add_entry()
    fe.id(tag)

    # Title like "September 22 2025"
    episode_title = title or _today_title()
    fe.title(episode_title)

    fe.pubDate(datetime.now(timezone.utc))

    desc_html = summary_html if summary_html is not None else _read_description_html()
    fe.description(desc_html)

    audio_url = episode_asset_url(tag)
    audio_path = OUT_DIR / AUDIO_NAME
    enclosure_len = audio_path.stat().st_size if audio_path.exists() else 0
    fe.enclosure(audio_url, enclosure_len, "audio/mpeg")

    # Optional per-episode image (falls back to channel cover)
    episode_image = _env("EPISODE_IMAGE_URL") or _env("PODCAST_COVER_URL")
    if episode_image:
        fe.podcast.itunes_image(episode_image)

    FEED_PATH.write_bytes(fg.rss_str(pretty=True))


if __name__ == "__main__":
    # Usage:
    #   python -m src.feed --update --tag <TAG> [--title "September 22 2025"]
    if "--update" in sys.argv and "--tag" in sys.argv:
        tag = sys.argv[sys.argv.index("--tag") + 1]
        t = None
        if "--title" in sys.argv:
            t = sys.argv[sys.argv.index("--title") + 1]
        update_feed_for_today(tag, title=t)