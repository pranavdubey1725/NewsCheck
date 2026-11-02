from newscheck.judge import ArticleVerdict, DetailCheck, Judgement, quote_in_text
from newscheck.search import SearchResult

def test_exact_quote_is_found():
    assert quote_in_text("offered voluntary buyouts", "Microsoft has offered voluntary buyouts to staff")


def test_curly_quotes_case_and_spacing_are_ignored():
    assert quote_in_text('"Around 60,000 people"', "targeting “around   60,000 people”")


def test_invented_quote_is_rejected():
    assert not quote_in_text("Microsoft fired 60,000 staff", "Microsoft has offered voluntary buyouts")


def test_empty_quote_is_never_found():
    assert not quote_in_text("", "any article text at all")



ARTICLE = SearchResult(url="https://example.com", title="T", content="C", score=0.9)
CONTRADICTING = Judgement(
    details=[DetailCheck(detail="action: fired", article_says="voluntary buyouts", matches="no")],
    evidence="voluntary buyouts",
    reason="Different action.",
)


def test_verified_quote_keeps_the_stance():
    v = ArticleVerdict(article=ARTICLE, judgement=CONTRADICTING, evidence_found=True)
    assert v.stance == "contradicts"


def test_unverified_quote_downgrades_to_not_addressed():
    v = ArticleVerdict(article=ARTICLE, judgement=CONTRADICTING, evidence_found=False)
    assert v.stance == "not_addressed"


def test_spacing_glitches_in_the_source_are_ignored():
    assert quote_in_text("multiple outlets reported Monday", "...multiple outletsreported Monday.")


def test_a_changed_number_is_still_rejected():
    assert not quote_in_text("offered buyouts to 6,000 employees", "offered buyouts to 60,000 employees")


def test_quote_marks_inside_the_source_are_ignored():
    assert quote_in_text("providing a voluntary exit offer", "Providing a “Voluntary Exit Offer” to staff")