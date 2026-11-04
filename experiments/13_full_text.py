import json
from pathlib import Path

from newscheck.search import SearchResult, search_news

CLAIM = "Microsoft is kicking out 60,000 employees."
CACHE = Path("experiments/data/kicking_out_full_text.json")

if CACHE.exists():
    articles = [SearchResult.model_validate(a) for a in json.loads(CACHE.read_text(encoding="utf-8"))]
else:
    articles = search_news(CLAIM)
    CACHE.write_text(
        json.dumps([a.model_dump(mode="json") for a in articles], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

for a in articles:
    full = a.raw_content or ""
    print("=" * 70)
    print(a.url)
    print(f"snippet: {len(a.content):>6} chars    full text: {len(full):>6} chars  (~{len(full) // 4} tokens)")
    print("\n--- first 400 chars ---")
    print(full[:400])
    print("\n--- last 400 chars ---")
    print(full[-400:])