import json
from pathlib import Path

from newscheck.chunks import chunk_sentences
from newscheck.index import Passage, PassageIndex
from newscheck.search import SearchResult
from newscheck.sources import group_into_sources


CLAIM = "Microsoft is kicking out 60,000 employees."
CACHE = Path("experiments/data/kicking_out_full_text.json")
articles = [SearchResult.model_validate(a) for a in json.loads(CACHE.read_text(encoding="utf-8"))]

index = PassageIndex()
for source_id, group in enumerate(group_into_sources(articles)):
    rep = max(group, key=lambda a: len(a.raw_content or a.content))
    text = rep.raw_content or rep.content
    chunks = chunk_sentences(text)
    index.add([Passage(text=c, url=rep.url, title=rep.title, source_id=source_id) for c in chunks])
    print(f"source {source_id}: {len(chunks):>2} chunks  {rep.url}")

print(f"\nTop passages for: {CLAIM}\n")
for r in index.search(CLAIM, k=6):
    print(f"{r.score:.3f}  [source {r.passage.source_id}]  {r.passage.text[:150]!r}\n")