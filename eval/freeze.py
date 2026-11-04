"""Search a claim once (with full text) and freeze the results for evaluation. Costs 1 Tavily credit."""
import json
import sys
from pathlib import Path

from newscheck.search import search_news

DATA = Path("eval/data")


def freeze(name: str, claim: str) -> None:
    path = DATA / f"{name}.json"
    if path.exists():
        print(f"{path} already exists. Delete it first to re-freeze.")
        return
    articles = search_news(claim)
    DATA.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"claim": claim, "articles": [a.model_dump(mode="json") for a in articles]},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Froze {len(articles)} articles to {path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit('usage: uv run eval/freeze.py <name> "<claim>"   (the name must not contain spaces)')
    freeze(sys.argv[1], sys.argv[2])