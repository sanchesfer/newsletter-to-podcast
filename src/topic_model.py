from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans

_model = None

def get_model():
    """Load or reuse the embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/paraphrase-MiniLM-L6-v2")
    return _model

def cluster_items(items, n_clusters=3):
    """
    Cluster summarized items into groups of related news.
    Returns a list of clusters (each cluster is a list of items).
    """
    texts = [it.get("summary") or "" for it in items]
    if not texts:
        return []

    model = get_model()
    embeddings = model.encode(texts)

    k = min(n_clusters, len(texts))
    kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = kmeans.fit_predict(embeddings)

    clusters = {}
    for it, label in zip(items, labels):
        clusters.setdefault(label, []).append(it)

    return list(clusters.values())
