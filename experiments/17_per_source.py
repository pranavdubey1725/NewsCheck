import json
from pathlib import Path

from newscheck.chunks import chunk_sentences
from newscheck.index import RELEVANCE_FLOOR, Passage, PassageIndex
from newscheck.search import SearchResult
from newscheck.sources import group_into_sources

CLAIM = "Microsoft is kicking out 60,000 employees."
CACHE = Path("experiments/data/kicking_out_full_text.json")
articles = [SearchResult.model_validate(a) for a in json.loads(CACHE.read_text(encoding="utf-8"))]

index = PassageIndex()
reps = []
for source_id, group in enumerate(group_into_sources(articles)):
    rep = max(group, key=lambda a: len(a.raw_content or a.content))
    reps.append(rep)
    chunks = chunk_sentences(rep.raw_content or rep.content)
    index.add([Passage(text=c, url=rep.url, title=rep.title, source_id=source_id) for c in chunks])

for source_id, rep in enumerate(reps):
    hits = index.search_source(CLAIM, source_id, k=2)
    kept = [h for h in hits if h.score >= RELEVANCE_FLOOR]
    print(f"\nsource {source_id}  {rep.url}")
    print(f"  {len(kept)} of {len(hits)} passages above floor {RELEVANCE_FLOOR}")
    for h in hits:
        mark = "✓" if h.score >= RELEVANCE_FLOOR else "✗"
        print(f"  {mark} {h.score:.3f}  {h.passage.text[:120]!r}")