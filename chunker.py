from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_markdown(markdown: str, source_url: str) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    texts = splitter.split_text(markdown)
    return [
        {"text": t, "source_url": source_url, "chunk_index": i}
        for i, t in enumerate(texts)
    ]