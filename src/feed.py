# src/feed.py
from datetime import datetime, timezone
from pathlib import Path
from html import escape
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

FEED_PATH = Path("feed.xml")
OUT_DIR = Path("output")
AUDIO_NAME = "episode.mp3"

NS_ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", NS_ITUNES)  # ensure <itunes:...> stays namespaced


# ---------- helpers ----------
def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _today_title() -> str:
    """Return 'Mon Day Year' (e.g., 'Sep 22 2025') in UTC."""
    now = datetime.now(timezone.utc)
    day_fmt = "%#d" if os.name == "nt" else "%-d"
    try:
        return now.strftime(f"%b {day_fmt} %Y")
    except ValueError:
        return now.strftime("%b %d %Y")


def _public_base() -> str:
    """Public homepage for channel <link> and feed URL."""
    base = _env("HOST_PUBLIC_BASE")
    if base:
        return base.rstrip("/") + "/"
    repo = _env("GITHUB_REPOSITORY")  # e.g. "owner/repo"
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}/"
    return "https://example.com/"


def _feed_self_url() -> str:
    return _public_base() + "feed.xml"


def _rfc2822_now() -> str:
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")


def _read_description_html() -> str:
    """Prefer notes.html; fallback to notes.md (escaped)."""
    html = OUT_DIR / "notes.html"
    if html.exists():
        return html.read_text(encoding="utf-8")
    md = OUT_DIR / "notes.md"
    if md.exists():
        return f"<pre>{escape(md.read_text(encoding='utf-8'))}</pre>"
    return "<p>Episode notes unavailable.</p>"


def _try_restore_feed_from_pages():
    """If feed.xml is missing, try to fetch the live Pages feed."""
    if FEED_PATH.exists():
        return
    try:
        with urllib.request.urlopen(_feed_self_url(), timeout=10) as r:
            data = r.read()
        if data:
            FEED_PATH.write_bytes(data)
    except Exception:
        pass  # ok to start fresh


# ---------- channel setup / load ----------
def _ensure_text(parent, tag, text):
    el = parent.find(tag)
    if el is None:
        el = ET.SubElement(parent, tag)
    if text:
        el.text = text
    return el


def _set_itunes_channel_tags(channel):
    # itunes:author
    author = _env("PODCAST_AUTHOR") or _env("PODCAST_OWNER_NAME") or "Fintech Daily Briefing"
    it_author = channel.find(f"{{{NS_ITUNES}}}author")
    if it_author is None:
        it_author = ET.SubElement(channel, f"{{{NS_ITUNES}}}author")
    it_author.text = author

    # itunes:owner
    owner_name = _env("PODCAST_OWNER_NAME")
    owner_email = _env("PODCAST_OWNER_EMAIL")
    if owner_name or owner_email:
        it_owner = channel.find(f"{{{NS_ITUNES}}}owner")
        if it_owner is None:
            it_owner = ET.SubElement(channel, f"{{{NS_ITUNES}}}owner")
        _ensure_text(it_owner, f"{{{NS_ITUNES}}}name", owner_name or "")
        _ensure_text(it_owner, f"{{{NS_ITUNES}}}email", owner_email or "")

    # itunes:explicit
    explicit = (_env("PODCAST_EXPLICIT", "no") or "no").lower()
    it_explicit = channel.find(f"{{{NS_ITUNES}}}explicit")
    if it_explicit is None:
        it_explicit = ET.SubElement(channel, f"{{{NS_ITUNES}}}explicit")
    it_explicit.text = explicit

    # itunes:image
    cover_url = _env("PODCAST_COVER_URL")
    if cover_url:
        it_img = channel.find(f"{{{NS_ITUNES}}}image")
        if it_img is None:
            it_img = ET.SubElement(channel, f"{{{NS_ITUNES}}}image")
        it_img.set("href", cover_url)

    # itunes:category (support "Parent>Child")
    raw_cat = _env("PODCAST_CATEGORY")
    if raw_cat:
        # clear existing categories to avoid duplicates
        for old in list(channel.findall(f"{{{NS_ITUNES}}}category")):
            channel.remove(old)
        if ">" in raw_cat:
            parent, child = [c.strip() for c in raw_cat.split(">", 1)]
            it_parent = ET.SubElement(channel, f"{{{NS_ITUNES}}}category")
            it_parent.set("text", parent)
            it_child = ET.SubElement(it_parent, f"{{{NS_ITUNES}}}category")
            it_child.set("text", child)
        else:
            it_cat = ET.SubElement(channel, f"{{{NS_ITUNES}}}category")
            it_cat.set("text", raw_cat)


def _load_or_init_tree():
    _try_restore_feed_from_pages()

    if FEED_PATH.exists():
        try:
            tree = ET.parse(FEED_PATH)
            root = tree.getroot()
            channel = root.find("channel")
            if channel is None:
                raise ValueError("No <channel> in feed")
            # ensure channel basics exist/updated
            _ensure_text(channel, "title", _env("PODCAST_TITLE", "Fintech Daily Briefing"))
            _ensure_text(channel, "link", _public_base())
            _ensure_text(channel, "description", _env(
                "PODCAST_DESCRIPTION",
                "AI-generated daily fintech podcast built from trusted newsletters. Canada/Brazil/BNPL prioritized.",
            ))
            _ensure_text(channel, "language", _env("PODCAST_LANG", "en-US"))
            _ensure_text(channel, "lastBuildDate", _rfc2822_now())
            _set_itunes_channel_tags(channel)
            return tree, root, channel
        except Exception:
            pass  # fall through to new feed

    # brand new feed
    rss = ET.Element("rss", attrib={"version": "2.0", f"xmlns:itunes": NS_ITUNES})
    channel = ET.SubElement(rss, "channel")
    _ensure_text(channel, "title", _env("PODCAST_TITLE", "Fintech Daily Briefing"))
    _ensure_text(channel, "link", _public_base())
    _ensure_text(channel, "description", _env(
        "PODCAST_DESCRIPTION",
        "AI-generated daily fintech podcast built from trusted newsletters. Canada/Brazil/BNPL prioritized.",
    ))
    _ensure_text(channel, "language", _env("PODCAST_LANG", "en-US"))
    _ensure_text(channel, "lastBuildDate", _rfc2822_now())
    _set_itunes_channel_tags(channel)
    tree = ET.ElementTree(rss)
    return tree, rss, channel


# ---------- items / append ----------
def _existing_guids(channel) -> set[str]:
    s = set()
    for it in channel.findall("item"):
        g = it.findtext("guid")
        if g:
            s.add(g.strip())
    return s


def _add_item(channel, *, tag: str, title: str, description_html: str,
              enclosure_url: str, enclosure_len: int, episode_image: str | None):
    # <item>
    item = ET.Element("item")

    # <title>
    t = ET.SubElement(item, "title")
    t.text = title

    # <description> (HTML will be escaped automatically)
    d = ET.SubElement(item, "description")
    d.text = description_html

    # <guid isPermaLink="false">
    g = ET.SubElement(item, "guid")
    g.set("isPermaLink", "false")
    g.text = tag

    # <enclosure url=.. length=.. type="audio/mpeg" />
    enc = ET.SubElement(item, "enclosure")
    enc.set("url", enclosure_url)
    enc.set("length", str(enclosure_len))
    enc.set("type", "audio/mpeg")

    # <pubDate>
    pd = ET.SubElement(item, "pubDate")
    pd.text = _rfc2822_now()

    # itunes:image (per episode)
    if episode_image:
        it_img = ET.SubElement(item, f"{{{NS_ITUNES}}}image")
        it_img.set("href", episode_image)

    # append at end (most readers sort; appending is fine)
    channel.append(item)


def episode_asset_url(tag: str) -> str:
    repo = _env("GITHUB_REPOSITORY")  # "owner/repo"
    return f"https://github.com/{repo}/releases/download/{tag}/{AUDIO_NAME}"


def update_feed_for_today(tag: str, *, title: str | None = None, summary_html: str | None = None) -> None:
    tree, root, channel = _load_or_init_tree()

    # dedupe by guid
    if tag in _existing_guids(channel):
        # still bump channel lastBuildDate
        lb = channel.find("lastBuildDate")
        if lb is None:
            lb = ET.SubElement(channel, "lastBuildDate")
        lb.text = _rfc2822_now()
        tree.write(FEED_PATH, encoding="utf-8", xml_declaration=True)
        return

    ep_title = title or _today_title()
    desc_html = summary_html if summary_html is not None else _read_description_html()
    audio_url = episode_asset_url(tag)
    audio_path = OUT_DIR / AUDIO_NAME
    enclosure_len = audio_path.stat().st_size if audio_path.exists() else 0
    episode_image = _env("EPISODE_IMAGE_URL") or _env("PODCAST_COVER_URL")

    _add_item(
        channel,
        tag=tag,
        title=ep_title,
        description_html=desc_html,
        enclosure_url=audio_url,
        enclosure_len=enclosure_len,
        episode_image=episode_image,
    )

    # bump channel lastBuildDate
    lb = channel.find("lastBuildDate")
    if lb is None:
        lb = ET.SubElement(channel, "lastBuildDate")
    lb.text = _rfc2822_now()

    tree.write(FEED_PATH, encoding="utf-8", xml_declaration=True)


# ---------- CLI ----------
if __name__ == "__main__":
    # Usage:
    #   python -m src.feed --update --tag <TAG> [--title "Sep 22 2025"]
    if "--update" in sys.argv and "--tag" in sys.argv:
        tag = sys.argv[sys.argv.index("--tag") + 1]
        t = None
        if "--title" in sys.argv:
            t = sys.argv[sys.argv.index("--title") + 1]
        update_feed_for_today(tag, title=t)