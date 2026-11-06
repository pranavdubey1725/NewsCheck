from urllib.parse import urlparse

from newscheck.agent import gather_coverage
from newscheck.sources import group_into_sources

CLAIMS = [
    "Microsoft is kicking out 60,000 employees.",
    "RBI announced that ₹10, ₹20 and ₹50 currency notes would be in short supply before Diwali 2026.",
]

for claim in CLAIMS:
    articles, queries = gather_coverage(claim)
    groups = group_into_sources(articles)
    print(f"\nCLAIM: {claim}")
    print(f"Queries the agent chose ({len(queries)}):")
    for q in queries:
        print(f"   - {q}")
    print(f"→ {len(articles)} articles, {len(groups)} independent sources")
    for a in articles:
        print(f"     {urlparse(a.url).netloc.removeprefix('www.'):<28} {a.title[:70]}")