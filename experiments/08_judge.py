import json
from pathlib import Path

from newscheck.judge import judge_article
from newscheck.search import SearchResult, search_news

CASES = {
    "Microsoft is kicking out 60,000 employees.": Path("experiments/data/kicking_out_articles.json"),
    "Microsoft offered voluntary buyouts to 60,000 employees.": Path("experiments/data/buyouts_articles.json"),
}


def load_articles(claim: str, cache: Path) -> list[SearchResult]:
    if cache.exists():
        return [SearchResult.model_validate(a) for a in json.loads(cache.read_text(encoding="utf-8"))]
    articles = search_news(claim)
    cache.parent.mkdir(exist_ok=True)
    cache.write_text(
        json.dumps([a.model_dump(mode="json") for a in articles], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return articles


for claim, cache in CASES.items():
    articles = load_articles(claim, cache)
    print(f"\nCLAIM: {claim}  ({len(articles)} frozen articles)")
    counts = {"supports": 0, "contradicts": 0, "not_addressed": 0}
    for article in articles:
        j = judge_article(claim, article)
        counts[j.stance] += 1
        print(f"\n  [{j.stance}] {article.title}")
        for d in j.details:
            print(f"      {d.matches:<13} {d.detail}  →  {d.article_says}")
    print(f"\n  SUMMARY: {counts}")