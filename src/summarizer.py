
---

## 🧠 `src/summarizer.py`
```python
from transformers import pipeline

_SUM = None

def get_summarizer():
    global _SUM
    if _SUM is None:
        _SUM = pipeline(
            "summarization",
            model="sshleifer/distilbart-cnn-12-6",
            framework="pt",
            device=-1,
        )
    return _SUM


def summarize(text: str, max_tokens: int = 180) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    # Chunk long texts to avoid truncation
    chunks, size = [], 2000
    for i in range(0, len(text), size):
        chunks.append(text[i : i + size])
    parts = []
    for c in chunks:
        out = get_summarizer()(c, max_length=220, min_length=60, do_sample=False)[0]["summary_text"]
        parts.append(out)
    joined = "\n".join(parts)
    # Final pass to compress
    final = get_summarizer()(joined, max_length=250, min_length=80, do_sample=False)[0]["summary_text"]
    return final


def stitch_script(items, lang="en-US"):
    intro = {
        "pt-BR": "Bem-vindo ao seu resumo diário. Aqui estão as principais notícias de hoje:",
        "en-US": "Welcome to your daily roundup. Here are today’s top stories:",
    }.get(lang, "Welcome to your daily roundup. Here are today’s top stories:")

    lines = [intro, ""]
    for i, it in enumerate(items, 1):
        title = it.get("title") or "Untitled"
        src = it.get("source") or ""
        summ = it.get("summary") or ""
        lines.append(f"Story {i}: {title}. {summ} (source: {src}).")
        lines.append("")
    outro = {
        "pt-BR": "Obrigado por ouvir. Até amanhã.",
        "en-US": "Thanks for listening. See you tomorrow.",
    }.get(lang, "Thanks for listening. See you tomorrow.")

    lines.append(outro)
    return "\n".join(lines)
