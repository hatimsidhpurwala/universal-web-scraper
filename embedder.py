import os

USE_FASTEMBED = os.getenv("USE_FASTEMBED", "false").lower() == "true"

_model = None

def get_model():
    global _model
    if _model is None:
        if USE_FASTEMBED:
            from fastembed import TextEmbedding
            _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        else:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed_chunks(chunks: list[dict]) -> list[dict]:
    model = get_model()
    texts = [c["text"] for c in chunks]

    if USE_FASTEMBED:
        embeddings = list(model.embed(texts))
        for i, chunk in enumerate(chunks):
            chunk["vector"] = embeddings[i].tolist()
    else:
        embeddings = model.encode(texts, show_progress_bar=True)
        for i, chunk in enumerate(chunks):
            chunk["vector"] = embeddings[i].tolist()

    return chunks

def embed_query(query: str) -> list[float]:
    model = get_model()

    if USE_FASTEMBED:
        embeddings = list(model.embed([query]))
        return embeddings[0].tolist()
    else:
        return model.encode([query])[0].tolist()