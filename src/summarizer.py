from transformers import pipeline

_SUM = None

def get_summarizer():
    global _SUM
    if _SUM is None:
        _SUM = pipeline(
            task="summarization",
            model="sshleifer/distilbart-cnn-12-6",
            framework="pt",
            device=-1,  # CPU
        )
    return _SUM

def _token_len(text: str, tok) -> int:
    return len(tok.encode(text, add_special_tokens=False))

def _chunk_by_tokens(text: str, tok, max_tokens: int = 900):
    # Greedy sentence-ish split; falls back to words if no punctuation
    seps = [". ", "! ", "? ", "\n"]
    parts = [text]
    for sep in seps:
        parts = sum((p.split(sep) for p in parts), [])  # flatten
    if len(parts) == 1:  # no separators found, fall back to words
        parts = text.split()

    chunks, cur, cur_len = [], [], 0
    for piece in parts:
        piece_txt = piece if isinstance(parts, list) and " " in text else (piece + " ")
        tlen = _token_len(piece_txt, tok)
        if cur_len + tlen > max_tokens and cur:
            chunks.append("".join(cur))
            cur, cur_len = [piece_txt], tlen
        else:
            cur.append(piece_txt); cur_len += tlen
    if cur:
        chunks.append("".join(cur))
    return chunks

def summarize(text: str, max_tokens: int = 180) -> str:
    text = (text or "").strip()
    if not text:
        return ""

    summ = get_summarizer()
    tok = summ.tokenizer

    # 1) Chunk long inputs safely under model limit
    chunks = _chunk_by_tokens(text, tok, max_tokens=900)

    # 2) Summarize each chunk (hard cap lengths; truncation ON)
    first_pass = []
    for c in chunks:
        out = summ(
            c,
            max_length=min(250, max_tokens + 70),
            min_length=max(60, max_tokens // 2),
            do_sample=False,
            truncation=True,
        )[0]["summary_text"]
        first_pass.append(out)

    joined = "\n".join(first_pass)

    # 3) If joined is still long, trim tokens before final pass
    if _token_len(joined, tok) > 900:
        # keep only the last ~900 tokens worth of text (simple char trim proxy)
        # you can tune the 4000 char heuristic as needed
        joined = joined[-4000:]

    final = summ(
        joined,
        max_length=min(260, max_tokens + 80),
        min_length=max(60, max_tokens // 2),
        do_sample=False,
        truncation=True,
    )[0]["summary_text"]

    return final