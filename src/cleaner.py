# src/cleaner.py
import hashlib
import re
import requests
from bs4 import BeautifulSoup

def strip_html(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    for s in soup.select("script, style, noscript"):
        s.decompose()
    text = soup.get_text(" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def fetch_and_readable(url: str) -> str:
    """
    Best-effort: fetch URL and return readability-parsed text.
    If readability/lxml_html_clean aren't installed, or fetch fails,
    fall back to a simple BeautifulSoup text extraction.
    """
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "news-bot/1.0"})
        r.raise_for_status()
    except Exception:
        return ""

    html = r.text

    # Try readability if available
    try:
        # Import lazily so missing deps don't crash at module import time
        from readability import Document  # type: ignore
        try:
            doc = Document(html)
            html2 = doc.summary(html_partial=True)
            soup = BeautifulSoup(html2, "lxml")
            for s in soup.select("script, style, noscript"):
                s.decompose()
            return soup.get_text(" ")
        except Exception:
            pass
    except Exception:
        # readability (or its deps) not installed → fall back
        pass

    # Fallback: plain text
    soup = BeautifulSoup(html, "lxml")
    for s in soup.select("script, style, noscript"):
        s.decompose()
    return soup.get_text(" ")

def hash_key(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

def extract_links_from_html(html: str):
    """Optional helper if you need to collect <a href> links from an email."""
    soup = BeautifulSoup(html or "", "lxml")
    return [a.get("href") for a in soup.find_all("a", href=True)]