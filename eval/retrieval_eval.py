"""Retrieval eval: for each article with a gold phrase, is that phrase in its top-k retrieved passages?"""
import json
from functools import partial
from pathlib import Path

from newscheck.chunks import chunk_fixed, chunk_semantic, chunk_sentences
from newscheck.index import Passage, PassageIndex
from newscheck.judge import quote_in_text


def evaluate(chunker=chunk_sentences, k: int = 2, mode: str = "hybrid", verbose: bool = True) -> float:
    cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8"))
    hits = total = n_chunks = n_words = 0
    for case in cases:
        data = json.loads(Path(f"eval/data/{case['name']}.json").read_text(encoding="utf-8"))
        claim = case.get("claim", data["claim"])

        index = PassageIndex()
        source_of = {}
        for source_id, a in enumerate(data["articles"]):
            text = a.get("raw_content") or a["content"]
            chunks = chunker(text)
            n_chunks += len(chunks)
            n_words += sum(len(c.split()) for c in chunks)
            index.add([Passage(text=c, url=a["url"], title=a["title"], source_id=source_id) for c in chunks])
            source_of[a["url"]] = source_id

        search = index.search_source if mode == "dense" else index.search_source_hybrid
        case_hits = case_total = 0
        for url, gold in case["gold"].items():
            if gold is None:
                continue
            retrieved = search(claim, source_of[url], k=k)
            case_hits += any(quote_in_text(gold, r.passage.text) for r in retrieved)
            case_total += 1

        if verbose:
            print(f"  {case_hits}/{case_total}  {case['name']:<10} {claim[:60]}")
        hits += case_hits
        total += case_total

    score = hits / total if total else 0.0
    avg_words = n_words / n_chunks if n_chunks else 0
    print(f"  TOTAL {mode} hit@{k}: {hits}/{total} = {score:.2f}   (avg {avg_words:.0f} words/chunk)\n")
    return score


if __name__ == "__main__":
    chunkers = {
        "fixed (600 chars)": chunk_fixed,
        "sentence (150 words)": chunk_sentences,
        "semantic @0.45": partial(chunk_semantic, threshold=0.45),
        "semantic @0.55": partial(chunk_semantic, threshold=0.55),
        "semantic @0.65": partial(chunk_semantic, threshold=0.65),
    }
    for name, chunker in chunkers.items():
        print(f"===== {name} =====")
        evaluate(chunker=chunker, k=2, mode="hybrid")