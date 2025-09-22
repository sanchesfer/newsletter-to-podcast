# Fintech Daily Briefing 🎙️

An automated podcast generator that turns daily fintech newsletters into a Spotify-ready audio show.

Each day:
1. Fetches recent fintech newsletters from Gmail.
2. Uses AI (Gemini or local fallback) to generate a podcast script.
3. Converts the script to audio with [Piper TTS](https://github.com/rhasspy/piper).
4. Builds an RSS feed so Spotify/Apple Podcasts can ingest the episodes.

---

## Features
- ✅ Pulls newsletters directly from Gmail  
- ✅ Deduplicates overlapping stories across sources  
- ✅ AI-generated script, tuned for fintech operators & investors  
- ✅ TTS with natural pauses between stories  
- ✅ Automated GitHub Action builds & publishes daily  
- ✅ RSS feed (`feed.xml`) served via GitHub Pages → publish to Spotify  

---

## Setup

Clone the repo and install dependencies:

```bash
git clone https://github.com/<your-username>/newsletter-to-podcast.git
cd newsletter-to-podcast
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure Gmail API credentials and Gemini API key in `.env` or GitHub secrets:
- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REFRESH_TOKEN`
- `GMAIL_LABEL` (e.g. `Fintech`)
- `PODCAST_TITLE`
- `HOST_PUBLIC_BASE`

Run locally:

```bash
PYTHONPATH=. python src/main.py \
  --piper "$(which piper)" \
  --voice voices/en_US-lessac-high.onnx \
  --prompt_file prompts/host_style.txt \
  --llm_full_text
```

This will:
- Fetch newsletters from the past day (`--since 1d` by default)  
- Generate `output/script.md` (the episode script)  
- Generate `output/episode.mp3` (the podcast audio)  
- Generate `output/notes.html` (episode description for Spotify)  

---

## GitHub Actions Automation

A workflow (`.github/workflows/podcast.yml`) is included.  
It runs daily on schedule (`cron`) or manually, then:

- Fetches Gmail newsletters  
- Generates script + audio  
- Uploads `episode.mp3` as a GitHub Release  
- Updates `feed.xml` for Spotify  

---

## Publishing to Spotify

1. Enable GitHub Pages on your repo (serve `feed.xml` from `/`).  
2. Copy the public feed URL:  
   ```
   https://<your-username>.github.io/newsletter-to-podcast/feed.xml
   ```
3. Go to [Spotify for Podcasters](https://podcasters.spotify.com/), add this RSS feed.  
4. Each GitHub Action run will publish a new episode automatically.

---

## Notes
- Episode names follow **“Month Day Year”** (e.g., *March 5 2025*).  
- Descriptions come from `output/notes.html`.  
- Entirely AI-generated — both the script and narration.  
