# src/llm_writer.py
import os
import sys
from typing import List, Dict

DEFAULT_SYS_INSTRUCTIONS = """You are a senior podcast writer and editor.
Write a tight, insightful, human-sounding script for a daily fintech podcast.
Use clear section transitions, add brief context and 'why this matters' lines,
and keep a confident, concise host voice. ALWAYS credit sources inline.
Do not over-compress: retain names, figures, and short quotes where useful.
Output plain text (no markdown), ready to be spoken aloud.
Base EVERY statement ONLY on the provided newsletter corpus. Do NOT invent facts.
If the corpus contains advertising, promotions, or event signups, ignore them."""

# ------------------ Provider helpers ------------------

def _call_openai(model: str, api_key: str, system_instructions: str, user_message: str) -> str:
    try:
        from openai import OpenAI  # new SDK
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        import openai  # legacy fallback
        openai.api_key = api_key
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
        )
        return (resp["choices"][0]["message"]["content"] or "").strip()

def _call_gemini(model: str, api_key: str, system_instructions: str, user_message: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    gmodel = genai.GenerativeModel(model)
    resp = gmodel.generate_content([system_instructions, user_message])
    return (resp.text or "").strip()

def _provider_call(system_instructions: str, user_message: str) -> str:
    provider = (os.getenv("LLM_PROVIDER") or "").lower()
    if provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is missing")
        return _call_openai(model, key, system_instructions, user_message)
    if provider == "gemini":
        # model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is missing")
        return _call_gemini(model, key, system_instructions, user_message)
    raise RuntimeError("Set LLM_PROVIDER=openai or LLM_PROVIDER=gemini with API key.")

# ------------------ Formatting ------------------

def _bulletize_items(items: List[Dict], prefer_full_text: bool) -> str:
    """
    Turn ALL items into a single, long bullet list with FULL text.
    No truncation, no caps, no batching. (Mind your model's context window!)
    """
    bullets = []
    for it in items:
        title = (it.get("title") or "Untitled").strip()
        src = (it.get("source") or "Unknown source").strip()
        body = (it.get("text") if prefer_full_text else (it.get("summary") or it.get("text") or "")).strip()
        # collapse excessive whitespace but keep everything
        body = " ".join(body.split())
        bullets.append(f"- {title} — Source: {src}. {body}")
    return "Corpus of newsletter-derived items (full text, untrimmed):\n" + "\n".join(bullets)

def _build_user_message(user_prompt: str, bullets_block: str, language: str) -> str:
    lang_name = "English" if language.startswith("en") else language
    return (
        f"LANGUAGE: {lang_name}\n"
        f"STYLE GOAL (from user): {user_prompt}\n\n"
        + bullets_block
    )

# ------------------ Public entry ------------------

def generate_script_from_prompt(
    items: List[Dict],
    user_prompt: str,
    language: str = "en-US",
    system_instructions: str = DEFAULT_SYS_INSTRUCTIONS,
    prefer_full_text: bool = False,
) -> str:
    """
    One-shot: send EVERYTHING to the model in a single call.
    - prefer_full_text=True -> use full newsletter bodies.
    - No batching, no per-item/total limits here.
    WARNING: If the combined prompt exceeds your model's context window,
             the provider will error or drop content. Use at your own risk.
    """
    bullets_block = _bulletize_items(items, prefer_full_text=prefer_full_text)
    user_msg = _build_user_message(user_prompt, bullets_block, language)
    # 🔍 DEBUG LOG
    #print("\n[debug] ===== LLM SYSTEM INSTRUCTIONS =====", file=sys.stderr)
    #print(system_instructions, file=sys.stderr)
    #print("\n[debug] ===== LLM USER MESSAGE =====", file=sys.stderr)
    #print(user_msg[:500000], file=sys.stderr)  # show first ~5000 chars
    #if len(user_msg) > 500000:
    #    print(f"... [truncated, total length {len(user_msg)} chars]", file=sys.stderr)

    return _provider_call(system_instructions, user_msg).strip()
