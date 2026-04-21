from sentence_transformers import SentenceTransformer

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed_chunks(chunks: list[dict]) -> list[dict]:
    model = get_model()
    texts = [c["text"] for c in chunks]
    vectors = model.encode(texts, show_progress_bar=True)
    for i, chunk in enumerate(chunks):
        chunk["vector"] = vectors[i].tolist()
    return chunks

def embed_query(query: str) -> list[float]:
    return get_model().encode([query])[0].tolist()