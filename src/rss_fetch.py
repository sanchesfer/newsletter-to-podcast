import requests
import feedparser

def fetch_rss_items(path="feeds.txt", limit_per_feed=5):
    items = []
    try:
        with open(path, "r") as f:
            feeds = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    except FileNotFoundError:
        return items
    for url in feeds:
        d = feedparser.parse(url)
        for e in d.entries[:limit_per_feed]:
            items.append({
                "title": e.get("title"),
                "link": e.get("link"),
                "source": d.feed.get("title", url)
            })
    return items
