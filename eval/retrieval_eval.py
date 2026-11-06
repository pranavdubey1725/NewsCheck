"""Retrieval eval: for each article with a gold phrase, is that phrase in its top-k retrieved passages?"""
import json
from pathlib import Path

from newscheck.chunks import chunk_sentences
from newscheck.index import Passage, PassageIndex
from newscheck.judge import quote_in_text


def evaluate(chunker=chunk_sentences, k: int = 2, mode: str = "dense") -> float:
    cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8"))
    hits = total = 0
    print(f"--- {mode}, hit@{k} ---")
    for case in cases:
        data = json.loads(Path(f"eval/data/{case['name']}.json").read_text(encoding="utf-8"))
        claim = case.get("claim", data["claim"])

        index = PassageIndex()
        source_of = {}
        for source_id, a in enumerate(data["articles"]):
            text = a.get("raw_content") or a["content"]
            index.add([Passage(text=c, url=a["url"], title=a["title"], source_id=source_id) for c in chunker(text)])
            source_of[a["url"]] = source_id

        search = index.search_source if mode == "dense" else index.search_source_hybrid
        case_hits = case_total = 0
        for url, gold in case["gold"].items():
            if gold is None:
                continue
            retrieved = search(claim, source_of[url], k=k)
            case_hits += any(quote_in_text(gold, r.passage.text) for r in retrieved)
            case_total += 1

        print(f"  {case_hits}/{case_total}  {case['name']:<10} {claim[:60]}")
        hits += case_hits
        total += case_total

    score = hits / total if total else 0.0
    print(f"  TOTAL hit@{k}: {hits}/{total} = {score:.2f}\n")
    return score


if __name__ == "__main__":
    for mode in ("dense", "hybrid"):
        evaluate(k=1, mode=mode)
        evaluate(k=2, mode=mode)