Fintech Daily Briefing 🎙️

An automated pipeline that turns your daily fintech newsletters into a podcast episode, published via RSS (Spotify, Apple Podcasts, etc).

Each episode is generated with AI narration using Piper TTS and script drafting from an LLM (e.g., Gemini or ChatGPT).

⸻

Features
	•	📧 Fetches newsletters from Gmail (by label).
	•	🧠 Uses an LLM with your custom prompt to turn raw text into a podcast script.
	•	🗣️ Converts script to natural speech (Piper TTS).
	•	🎵 Produces normalized .mp3 episodes.
	•	📰 Creates HTML notes for Spotify/Apple descriptions.
	•	📡 Updates an RSS feed (feed.xml) automatically.
	•	⚙️ Runs daily via GitHub Actions.

⸻
<pre>
```bash
# 1. Clone your repo
git clone https://github.com/<your-username>/newsletter-to-podcast.git
cd newsletter-to-podcast

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Download a Piper voice (example: Ryan, male US English)
mkdir -p voices
python -m piper.download_voices en_US-ryan-high --download-dir voices

# 5. Export environment variables (replace with your real values)
export GMAIL_CLIENT_ID="xxx"
export GMAIL_CLIENT_SECRET="xxx"
export GMAIL_REFRESH_TOKEN="xxx"
export GMAIL_LABEL="Fintech"
export PODCAST_TITLE="Fintech Daily Briefing"
export HOST_PUBLIC_BASE="https://yourdomain.com/podcast"

# 6. Run locally (generate script + audio)
PYTHONPATH=. python src/main.py \
  --piper "$(which piper)" \
  --voice "$(pwd)/voices/en_US-ryan-high.onnx" \
  --prompt_file prompts/host_style.txt \
  --llm_full_text

# 7. Resume audio only (skip fetching & LLM, reuse last script)
PYTHONPATH=. python src/main.py \
  --piper "$(which piper)" \
  --voice "$(pwd)/voices/en_US-ryan-high.onnx" \
  --resume
```
</pre>
⸻

GitHub Actions (Automation)
	•	A workflow (.github/workflows/podcast.yml) runs daily on schedule.
	•	It builds the episode, uploads episode.mp3 to Releases, and updates the RSS feed.
	•	Spotify/Apple pull from your hosted feed.xml.

⸻

Notes
	•	Secrets (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, HOST_PUBLIC_BASE, etc.) must be set in GitHub repo → Settings → Secrets.
	•	Output files are stored in /output:
	•	episode.mp3 → Final podcast audio.
	•	script.md → Full LLM script for the episode.
	•	notes.html → Episode description (Spotify/Apple).
	•	feed.xml → Podcast RSS feed.

⸻

👉 Do you want me to also include a section with Spotify integration steps (how to take feed.xml and register it in Spotify for Podcasters)?
