from newscheck.claims import analyse_input
from newscheck.search import search_news

MESSAGES = {
    "opinion": "This is an opinion, so there is nothing to check.",
    "prediction": "This is about the future, so it can't be checked yet.",
    "needs_context": "This is too vague to check. Say who or what it is about.",
    "not_a_claim": "There is nothing here to check.",
}

def check(text: str) -> None:
    print(f"\nINPUT: {text}")
    analysis = analyse_input(text)

    if analysis.input_type != "factual_claim":
        print(f"  {MESSAGES[analysis.input_type]}")
        return

    print(f"  CLAIM: {analysis.claim}")
    if analysis.opinion_set_aside:
        print(f"  NOT CHECKED (opinion): {analysis.opinion_set_aside}")

    results = search_news(analysis.claim)
    if not results:
        print("  No matching news coverage found. This is not evidence that the claim is false.")
        return

    print(f"  {len(results)} matching article(s):")
    for r in results:
        date = r.published_date.date() if r.published_date else "no date"
        print(f"    {r.score:.2f}  {date}  {r.title}")
        print(f"          {r.url}")


INPUTS = [
    "BREAKING 🚨 Microsoft is kicking out 60,000 employees!!! Share before it's deleted 😱",
    "Infosys fired 20,000 people. What a shameful company.",
    "Virat Kohli is the greatest batsman of all time.",
    "It reached 40 yesterday.",
]

for text in INPUTS:
    check(text)