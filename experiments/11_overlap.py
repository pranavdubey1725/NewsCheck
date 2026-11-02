import json
from itertools import combinations
from pathlib import Path
from urllib.parse import urlparse

from newscheck.overlap import jaccard, shingles
from newscheck.search import SearchResult

CACHE = Path("experiments/data/kicking_out_articles.json")
articles = [SearchResult.model_validate(a) for a in json.loads(CACHE.read_text(encoding="utf-8"))]


def outlet(url: str) -> str:
    return urlparse(url).netloc.removeprefix("www.")


sets = {a.url: shingles(f"{a.title} {a.content}") for a in articles}
pairs = sorted(
    ((jaccard(sets[a.url], sets[b.url]), outlet(a.url), outlet(b.url)) for a, b in combinations(articles, 2)),
    reverse=True,
)

from newscheck.overlap import containment, jaccard, shingles   # update the import at the top

pairs = sorted(
    (
        (jaccard(sets[a.url], sets[b.url]), containment(sets[a.url], sets[b.url]), outlet(a.url), outlet(b.url))
        for a, b in combinations(articles, 2)
    ),
    reverse=True,
)

print("jacc   cont")
for j, c, x, y in pairs:
    print(f"{j:.2f}   {c:.2f}   {x:<28} ↔  {y}")