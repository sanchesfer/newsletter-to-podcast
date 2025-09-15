import hashlib
import re
import requests
from bs4 import BeautifulSoup
from readability import Document

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
