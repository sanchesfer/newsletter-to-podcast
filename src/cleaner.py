import hashlib
import re
import requests
from bs4 import BeautifulSoup
from readability import Document
from urllib.parse import urlparse

NOISE_PATTERNS = (
    "unsubscribe", "email preference", "manage subscription",
    "privacy", "terms", "feedback", "view in browser",
    "mailto:", "#", "javascript:"
)

def is_noise_link(href: str, text: str) -> bool:
    if not href:
        return True
    h = href.lower()
    t = (text or "").lower()
    return (
        any(x in h for x in NOISE_PATTERNS)
        or (t and any(x in t for x in NOISE_PATTERNS))
    )

def extract_links_from_html(html: str, max_links: int = 100):
    """Return a de-duplicated list of (title, url) from newsletter HTML."""
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    links = []
    seen = set()
    for a in soup.find_all("a"):
        href = a.get("href")
        text = (a.get_text(" ", strip=True) or "").strip()
        if not href or href.startswith(("cid:", "/")):
            continue
        if is_noise_link(href, text):
            continue
        # normalize + dedupe by URL without query string
        key = href.split("?", 1)[0].strip()
        if key in seen:
            continue
        seen.add(key)
        title = text or urlparse(href).netloc
        links.append((title, href))
        if len(links) >= max_links:
            break
    return links

def strip_html(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    for s in soup.select('script, style, noscript'): s.decompose()
    text = soup.get_text(" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def fetch_and_readable(url: str) -> str:
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"news-bot/1.0"})
        r.raise_for_status()
        doc = Document(r.text)
        html = doc.summary(html_partial=True)
        soup = BeautifulSoup(html, "lxml")
        for s in soup.select('script, style, noscript'): s.decompose()
        return soup.get_text(" ")
    except Exception:
        return ""

def hash_key(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()
