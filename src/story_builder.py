def build_story(cluster):
    """
    Turn a cluster of items into a podcast-style narrative,
    always mentioning the source(s) for each story (English only).
    """
    titles = [it.get("title") for it in cluster if it.get("title")]
    sources = [it.get("source", "Unknown source") for it in cluster]
    summaries = [it.get("summary", "") for it in cluster if it.get("summary")]

    source_text = ", ".join(sorted(set(sources))) if sources else "various sources"
    titles_text = "; ".join(titles) if titles else "untitled stories"
    joined_summary = " ".join(summaries)

    return (
        f"From {source_text}, today’s highlights include {titles_text}. "
        f"{joined_summary} "
        f"These updates were reported by {source_text}."
    )