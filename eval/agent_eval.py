"""Agent eval (live): does the search agent beat a single search? Costs ~70 Tavily credits."""
import json
import time
from datetime import datetime
from itertools import combinations
from pathlib import Path
from statistics import mean
from urllib.parse import urlparse

from newscheck.agent import gather_coverage
from newscheck.search import is_excluded, search_news
from newscheck.sources import group_into_sources

RUNS = 3
CLAIMS = {
    "microsoft": "Microsoft is kicking out 60,000 employees.",
    "rbi": "RBI announced that ₹10, ₹20 and ₹50 currency notes would be in short supply before Diwali 2026.",
    "tamil_nadu": "Tamil Nadu declared November 9, 2026, a public holiday for schools, colleges and educational institutions because Diwali falls on November 8.",
    "infosys": "Infosys fired 20,000 people last week.",
}
FACT_CHECK_WORDS = ("fake", "fact check", "fact-check", "debunk", "false", "clarif", "dismiss", "misleading", "denies", "hoax")


def outlet(url: str) -> str:
    return urlparse(url).netloc.removeprefix("www.").removeprefix("m.")


def is_fact_check(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in FACT_CHECK_WORDS)


def baseline(claim: str):
    return search_news(claim), [claim]


def agent(claim: str):
    articles, queries, _ = gather_coverage(claim)
    return articles, queries


def stability(outlet_sets: list[set[str]]) -> float:
    """Mean Jaccard overlap of outlet sets across runs. 1.0 = the same outlets every time."""
    pairs = list(combinations(outlet_sets, 2))
    if not pairs:
        return 1.0
    return mean(len(a & b) / len(a | b) if a | b else 1.0 for a, b in pairs)


def main() -> None:
    results = []
    for name, claim in CLAIMS.items():
        print(f"\n=== {name}: {claim}")
        for mode, run in (("baseline", baseline), ("agent", agent)):
            runs = []
            for _ in range(RUNS):
                start = time.perf_counter()
                articles, queries = run(claim)
                runs.append({
                    "sources": len(group_into_sources(articles)),
                    "fact_checks": sum(is_fact_check(a.title) for a in articles),
                    "searches": len(queries),
                    "seconds": round(time.perf_counter() - start, 1),
                    "excluded": sum(is_excluded(a.url) for a in articles),
                    "outlets": sorted({outlet(a.url) for a in articles}),
                    "queries": queries,
                })
            summary = {
                "claim": name,
                "mode": mode,
                "sources": mean(r["sources"] for r in runs),
                "fact_checks": mean(r["fact_checks"] for r in runs),
                "searches": mean(r["searches"] for r in runs),
                "seconds": mean(r["seconds"] for r in runs),
                "excluded": sum(r["excluded"] for r in runs),
                "stability": round(stability([set(r["outlets"]) for r in runs]), 2),
                "runs": runs,
            }
            results.append(summary)
            print(
                f"  {mode:<8}  sources {summary['sources']:4.1f}   fact-checks {summary['fact_checks']:4.1f}   "
                f"searches {summary['searches']:3.1f}   {summary['seconds']:5.1f}s   "
                f"stability {summary['stability']:.2f}   excluded {summary['excluded']}"
            )

    out = Path("eval/results") / f"agent_eval_{datetime.now():%Y%m%d_%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved full results (including every query and outlet) to {out}")


if __name__ == "__main__":
    main()
