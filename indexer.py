"""
Run this script to build or update the Qdrant index.
Usage:
    python indexer.py                  # index ALL sites
    python indexer.py site1.md         # re-index ONE site only
"""
import sys
import os
from pathlib import Path
from cleaner import deduplicate_chunks, normalize_text
from chunker import chunk_markdown
from embedder import embed_chunks
from vector_store import store_chunks_for_site, clear_site, list_sites

MD_FOLDER = Path("md_files")

def index_one_file(filepath: Path):
    print(f"📄 Indexing: {filepath.name}")
    text = filepath.read_text(encoding="utf-8")
    cleaned = normalize_text(text)
    chunks = chunk_markdown(cleaned, source_url=filepath.stem)
    chunks = deduplicate_chunks(chunks)
    chunks = embed_chunks(chunks)
    clear_site(filepath.stem)
    count = store_chunks_for_site(chunks, site_name=filepath.stem)
    print(f"✅ Done — {count} chunks stored for {filepath.stem}")

def index_all():
    files = list(MD_FOLDER.glob("*.md"))
    if not files:
        print("❌ No .md files found in md_files/ folder")
        return
    for f in files:
        index_one_file(f)
    print(f"\n🎉 All {len(files)} sites indexed and ready.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = MD_FOLDER / sys.argv[1]
        if target.exists():
            index_one_file(target)
        else:
            print(f"❌ File not found: {target}")
    else:
        index_all()