import json
from pathlib import Path

from newscheck.chunks import chunk_sentences
from newscheck.search import SearchResult

CACHE = Path("experiments/data/kicking_out_full_text.json")
articles = [SearchResult.model_validate(a) for a in json.loads(CACHE.read_text(encoding="utf-8"))]

article = next(a for a in articles if "kotaku" in a.url)
chunks = chunk_sentences(article.raw_content or "")
print(f"{article.url}\n{len(chunks)} chunks\n")
for i, c in enumerate(chunks[:4]):
    print(f"--- chunk {i} ({len(c.split())} words) ---")
    print(f"START: {c[:80]!r}")
    print(f"END:   {c[-80:]!r}\n")