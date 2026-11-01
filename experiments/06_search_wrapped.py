from newscheck.search import search_news

QUERIES = [
    "Infosys fired 20,000 people",
    "Microsoft offers voluntary exit to 60,000 employees",
]

for q in QUERIES:
    results = search_news(q)
    print(f"\n{q}  →  {len(results)} result(s) kept")
    for r in results:
        date = r.published_date.date() if r.published_date else "no date"
        print(f"  {r.score:.2f}  {date}  {r.title}")