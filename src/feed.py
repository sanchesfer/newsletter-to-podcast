# src/feed.py
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from pathlib import Path
from html import escape
import urllib.request
import xml.etree.ElementTree as ET
import os
import sys

FEED_PATH = Path("feed.xml")
OUT_DIR = Path("output")
AUDIO_NAME = "episode.mp3"


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _today_title() -> str:
    """Return 'Mon Day Year' (e.g., 'Sep 22 2025') in UTC."""
    now = datetime.now(timezone.utc)
    # Windows uses %#d, others use %-d; fall back to %d if not supported
    day_fmt = "%#d" if os.name == "nt" else "%-d"
    try:
        return now.strftime(f"%b {day_fmt} %Y")
    except ValueError:
        return now.strftime("%b %d %Y")


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


def _feed_self_url() -> str:
    return _public_base() + "feed.xml"


def _bootstrap_existing_feed_if_missing():
    """
    If feed.xml isn't in the workspace, try to fetch the live Pages feed and save it,
    so we append instead of overwriting when possible.
    """
    if FEED_PATH.exists():
        return
    try:
        with urllib.request.urlopen(_feed_self_url(), timeout=10) as r:
            data = r.read()
        if data:
            FEED_PATH.write_bytes(data)
    except Exception:
        # ok to start fresh if not reachable
        pass


def load_or_init() -> FeedGenerator:
    """
    Initialize or load feed.xml and set core channel metadata.
    Safe to call repeatedly.
    """
    _bootstrap_existing_feed_if_missing()

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
    fg.link(href=_public_base(), rel="alternate")  # required channel link
    # (Atom self-link removed; not needed for Spotify/Apple)
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

    # Category: support "Parent>Child" or just Parent; default to Technology/News
    raw_cat = _env("PODCAST_CATEGORY", "")
    if ">" in raw_cat:
        parent, child = [c.strip() for c in raw_cat.split(">", 1)]
        fg.podcast.itunes_category(parent, child)
    elif raw_cat:
        fg.podcast.itunes_category(raw_cat)
    else:
        fg.podcast.itunes_category("Technology", "News")

    # Explicit flag
    explicit = _env("PODCAST_EXPLICIT", "no").lower()  # "yes"/"no"/"clean"
    fg.podcast.itunes_explicit(explicit)

    # Cover art
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


def _existing_guids() -> set[str]:
    """Collect GUIDs already present to avoid duplicates on re-runs."""
    s: set[str] = set()
    if FEED_PATH.exists():
        try:
            root = ET.fromstring(FEED_PATH.read_bytes())
            for it in root.findall(".//item"):
                g = it.findtext("guid")
                if g:
                    s.add(g.strip())
        except Exception:
            pass
    return s


def update_feed_for_today(tag: str, *, title: str | None = None, summary_html: str | None = None) -> None:
    """
    Add a new episode item:
    - title: defaults to 'Mon Day Year' (e.g., 'Sep 22 2025')
    - description: notes.html (or provided summary_html) for Spotify
    - enclosure: GitHub Release asset for this tag
    """
    fg = load_or_init()

    # DEDUPE: skip adding if this GUID already exists (e.g., re-run of same tag)
    if tag in _existing_guids():
        FEED_PATH.write_bytes(fg.rss_str(pretty=True))
        return

    fe = fg.add_entry()
    fe.id(tag)

    # Title like "Sep 22 2025"
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
    #   python -m src.feed --update --tag <TAG> [--title "Sep 22 2025"]
    if "--update" in sys.argv and "--tag" in sys.argv:
        tag = sys.argv[sys.argv.index("--tag") + 1]
        t = None
        if "--title" in sys.argv:
            t = sys.argv[sys.argv.index("--title") + 1]
        update_feed_for_today(tag, title=t)