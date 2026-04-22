from fastembed import TextEmbedding

_model = None

def get_model():
    global _model
    if _model is None:
        _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _model

def embed_chunks(chunks: list[dict]) -> list[dict]:
    model = get_model()
    texts = [c["text"] for c in chunks]
    embeddings = list(model.embed(texts))
    for i, chunk in enumerate(chunks):
        chunk["vector"] = list(embeddings[i])
    return chunks

def embed_query(query: str) -> list[float]:
    model = get_model()
    result = list(model.embed([query]))
    return list(result[0])