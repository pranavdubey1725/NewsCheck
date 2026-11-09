from newscheck import judge
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
    details=[
        DetailCheck(detail="action: fired", article_says="voluntary buyouts", matches="no"),
        DetailCheck(detail="number: 60,000", article_says="60,000", matches="yes"),
    ],
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


def test_source_with_no_relevant_passage_is_not_addressed():
    v = ArticleVerdict(article=ARTICLE)
    assert v.stance == "not_addressed"

# --- quote retry loop, with a fake model (no network) ---------------------------------------------

PASSAGES = "Microsoft has offered voluntary buyouts to around 60,000 employees."
INVENTED = CONTRADICTING.model_copy(update={"evidence": "Microsoft is laying off 60,000 people"})


def fake_model(monkeypatch, *judgements):
    """Replace the model with scripted judgements; returns the list of calls made."""
    calls = []

    def call_structured(system, user, output_model):
        calls.append(user)
        return judgements[min(len(calls), len(judgements)) - 1]

    monkeypatch.setattr(judge, "call_structured", call_structured)
    return calls


def test_retry_message_is_printed_only_when_another_attempt_follows(monkeypatch, capsys):
    calls = fake_model(monkeypatch, INVENTED)   # the quote is never in the passages

    verdict = judge.judge_article("Microsoft is kicking out 60,000 employees.", ARTICLE, PASSAGES)

    out = capsys.readouterr().out
    assert len(calls) == 1 + judge.MAX_QUOTE_RETRIES
    assert out.count("[retry]") == judge.MAX_QUOTE_RETRIES
    assert out.count("[downgraded]") == 1
    assert verdict.stance == "not_addressed"


def test_no_retry_message_when_the_first_quote_is_found(monkeypatch, capsys):
    calls = fake_model(monkeypatch, CONTRADICTING)   # "voluntary buyouts" is in the passages

    verdict = judge.judge_article("Microsoft is kicking out 60,000 employees.", ARTICLE, PASSAGES)

    out = capsys.readouterr().out
    assert len(calls) == 1
    assert "[retry]" not in out and "[downgraded]" not in out
    assert verdict.stance == "contradicts"


def test_retry_with_feedback_can_recover_the_quote(monkeypatch, capsys):
    calls = fake_model(monkeypatch, INVENTED, CONTRADICTING)

    verdict = judge.judge_article("Microsoft is kicking out 60,000 employees.", ARTICLE, PASSAGES)

    out = capsys.readouterr().out
    assert len(calls) == 2
    assert "does not appear in the passages" in calls[1]
    assert out.count("[retry]") == 1 and "[downgraded]" not in out
    assert verdict.stance == "contradicts"
