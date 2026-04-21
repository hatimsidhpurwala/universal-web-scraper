import re
from bs4 import BeautifulSoup

def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["header","footer","nav","aside",
                               "script","style","noscript"]):
        tag.decompose()
    for tag in soup.find_all(True):
        classes = tag.get("class", [])
        id_attr = tag.get("id", "")
        bad = ["cookie","banner","popup","modal","menu",
               "sidebar","advertisement","overlay"]
        if any(b in " ".join(classes).lower() or b in id_attr.lower()
               for b in bad):
            tag.decompose()
    return str(soup)

def normalize_text(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\[.*?\]\(http\S+\)', '', text)
    text = re.sub(r'http\S+', '', text)
    text = text.encode("ascii", "ignore").decode()
    return text.strip()

def deduplicate_chunks(chunks: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for chunk in chunks:
        h = hash(chunk["text"][:200])
        if h not in seen:
            seen.add(h)
            unique.append(chunk)
    return unique