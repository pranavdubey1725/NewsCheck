"""Relevance-floor calibration: best passage scores for answerable vs unanswerable (cross-story) sources."""
import json
from pathlib import Path
from statistics import median

from newscheck.chunks import chunk_sentences
from newscheck.index import Passage, PassageIndex

K = 2
FLOORS = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]


def load(name: str) -> dict:
    return json.loads(Path(f"eval/data/{name}.json").read_text(encoding="utf-8"))


def build_index(articles: list[dict]) -> PassageIndex:
    index = PassageIndex()
    for source_id, a in enumerate(articles):
        text = a.get("raw_content") or a["content"]
        index.add([Passage(text=c, url=a["url"], title=a["title"], source_id=source_id) for c in chunk_sentences(text)])
    return index


def best_score(index: PassageIndex, claim: str, source_id: int) -> float | None:
    hits = index.search_source_hybrid(claim, source_id, k=K)
    return max(h.score for h in hits) if hits else None


cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8"))
datasets = {name: load(name) for name in {c["name"] for c in cases}}
indexes = {name: build_index(d["articles"]) for name, d in datasets.items()}

answerable, unanswerable = [], []
for case in cases:
    own = case["name"]
    claim = case.get("claim", datasets[own]["claim"])

    urls = [a["url"] for a in datasets[own]["articles"]]
    for url, gold in case["gold"].items():
        if gold is not None:
            s = best_score(indexes[own], claim, urls.index(url))
            if s is not None:
                answerable.append(s)

    for other, data in datasets.items():
        if other == own:
            continue
        for source_id in range(len(data["articles"])):
            s = best_score(indexes[other], claim, source_id)
            if s is not None:
                unanswerable.append(s)

print(f"answerable   n={len(answerable):>3}  min {min(answerable):.3f}  median {median(answerable):.3f}  max {max(answerable):.3f}")
print(f"unanswerable n={len(unanswerable):>3}  min {min(unanswerable):.3f}  median {median(unanswerable):.3f}  max {max(unanswerable):.3f}\n")

for floor in FLOORS:
    kept = sum(s >= floor for s in answerable) / len(answerable)
    silenced = sum(s < floor for s in unanswerable) / len(unanswerable)
    print(f"floor {floor:.2f}:  answerable kept {kept:>4.0%}   unanswerable silenced {silenced:>4.0%}")