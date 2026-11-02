from newscheck.search import SearchResult
from newscheck.sources import group_into_sources

WIRE = (
    "Microsoft has offered 60,000 employees or about 27 percent of its global workforce "
    "voluntary buyouts as the software giant spends heavily on artificial intelligence "
    "the company said the offer is time limited and built on an earlier retirement program"
)
WORDS = WIRE.split()


def article(url: str, text: str) -> SearchResult:
    return SearchResult(url=url, title="", content=text, score=0.9)


def test_chain_of_partial_copies_is_one_source():
    first_half = article("https://a.com", " ".join(WORDS[:16]))
    full = article("https://b.com", WIRE)
    second_half = article("https://c.com", " ".join(WORDS[-16:]))
    assert len(group_into_sources([first_half, full, second_half])) == 1


def test_independent_articles_stay_separate():
    a = article("https://a.com", WIRE)
    b = article("https://b.com", "The central bank kept interest rates unchanged on Thursday after a two day meeting of its policy committee in the capital")
    assert len(group_into_sources([a, b])) == 2