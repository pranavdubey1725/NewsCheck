import json
from pathlib import Path

from newscheck.search import SearchResult
from newscheck.sources import group_into_sources

CACHE = Path("experiments/data/kicking_out_articles.json")
articles = [SearchResult.model_validate(a) for a in json.loads(CACHE.read_text(encoding="utf-8"))]

groups = group_into_sources(articles)
print(f"{len(articles)} articles → {len(groups)} independent sources\n")
for n, group in enumerate(groups, start=1):
    print(f"Source {n}:")
    for a in group:
        print(f"   {a.url}")