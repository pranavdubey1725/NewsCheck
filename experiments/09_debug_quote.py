import json
import unicodedata
from pathlib import Path

from newscheck.search import SearchResult

articles = [
    SearchResult.model_validate(a)
    for a in json.loads(Path("experiments/data/buyouts_articles.json").read_text(encoding="utf-8"))
]
article = next(a for a in articles if "axios" in a.url)

print(repr(article.content[:800]))

hidden = sorted({c for c in article.content if unicodedata.category(c) in ("Cf", "Zs") and c != " "})
print("\nUnusual characters:", [f"U+{ord(c):04X} {unicodedata.name(c, '?')}" for c in hidden])