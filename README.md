# Newsletter → Daily Podcast

Runs daily on GitHub Actions, converts your labeled newsletters + RSS into a short audio roundup, publishes an MP3 to GitHub Releases, and maintains `feed.xml` so your show is subscribe-able.

## Setup
1. Create Gmail label (e.g., `Newsletters`) and add filters so newsletters auto-label.
2. In this repo, add GitHub Secrets:
   - `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN` (OAuth for Gmail API)
   - `GMAIL_LABEL`
   - `PODCAST_TITLE`, `PODCAST_AUTHOR`, `PODCAST_LANG`
   - `HOST_PUBLIC_BASE` (optional, for show notes links)
3. (Optional) Put RSS URLs in `feeds.txt`.
4. Adjust voice in workflow to a Piper voice you like (pt-BR supported).
5. Enable GitHub Pages (optional) if you want to host `feed.xml` as a static URL.
6. Subscribe to your RSS in a podcast app (point it at the raw `feed.xml` link or a Pages URL).

## Local run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main --since 1d --max_items 12 --piper ./piper/piper --voice ./voices/en_US-lessac-high.onnx
