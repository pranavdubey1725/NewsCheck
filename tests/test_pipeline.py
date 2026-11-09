"""check_stream end to end, offline: the model, search and embedding model are faked; everything else is real."""
import math
import re
import zlib

import pytest

from newscheck import index, pipeline
from newscheck.claims import ClaimAnalysis
from newscheck.judge import ArticleVerdict, DetailCheck, Judgement
from newscheck.report import DISCLAIMER, NOT_CHECKABLE
from newscheck.search import SearchResult
from newscheck.sources import MAX_SOURCES

CLAIM = "Microsoft is cutting 60,000 jobs in 2026."
FACTUAL = ClaimAnalysis(input_type="factual_claim", claim=CLAIM, opinion_set_aside="", reason="A checkable event.")
OPINION = ClaimAnalysis(input_type="opinion", claim="", opinion_set_aside="", reason="A judgement.")


# --- fakes ---------------------------------------------------------------------------------------

def fake_vector(text: str) -> list[float]:
    """Deterministic bag-of-words vector: texts sharing words point the same way (cosine ~ word overlap)."""
    v = [0.0] * index.VECTOR_SIZE
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        v[zlib.crc32(token.encode()) % (index.VECTOR_SIZE - 1)] += 1.0
    v[-1] = 0.1   # never a zero vector
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v]


def on_topic(n: int) -> SearchResult:
    """An independent article (its own wording) that discusses the claim."""
    tail = " ".join(f"s{n}w{j}" for j in range(12))
    return SearchResult(
        url=f"https://outlet{n}.example/story",
        title=f"Outlet {n} headline",
        content=f"Microsoft is cutting 60,000 jobs in 2026. {tail}.",
        score=0.9,
    )


OFF_TOPIC = SearchResult(
    url="https://elsewhere.example/weather",
    title="Rain expected",
    content="Heavy rain is expected across the coast tomorrow, forecasters warned residents on Sunday evening.",
    score=0.9,
)


def supporting(claim: str, article: SearchResult, excerpt: str | None = None) -> ArticleVerdict:
    judgement = Judgement(
        details=[
            DetailCheck(detail="action: cutting jobs", article_says="cutting jobs", matches="yes"),
            DetailCheck(detail="number: 60,000", article_says="60,000", matches="yes"),
        ],
        evidence="Microsoft is cutting 60,000 jobs in 2026",
        reason="Same action and number.",
    )
    return ArticleVerdict(article=article, judgement=judgement, evidence_found=True)


def must_not_be_called(*args, **kwargs):
    raise AssertionError("should not be called")


@pytest.fixture
def fakes(monkeypatch):
    """Install offline fakes; returns a dict the test can tweak (articles, judge, summary) and inspect (judged)."""
    state = {
        "analysis": FACTUAL,
        "articles": [on_topic(1), on_topic(2), on_topic(3)],
        "fact_check_urls": set(),
        "judge": supporting,
        "summary": lambda claim, verdicts: iter(["Three outlets ", "report 60,000 job cuts."]),
        "judged": [],
    }

    def judge(claim, article, excerpt=None):
        state["judged"].append(article.url)
        return state["judge"](claim, article, excerpt)

    monkeypatch.setattr(pipeline, "analyse_input", lambda text: state["analysis"])
    monkeypatch.setattr(
        pipeline, "gather_coverage",
        lambda claim: (state["articles"], ["microsoft job cuts", f"{claim} fact check"], state["fact_check_urls"]),
    )
    monkeypatch.setattr(pipeline, "judge_article", judge)
    monkeypatch.setattr(pipeline, "stream_summary", lambda claim, verdicts: state["summary"](claim, verdicts))
    monkeypatch.setattr(index, "embed_passages", lambda texts: [fake_vector(t) for t in texts])
    monkeypatch.setattr(index, "embed_query", fake_vector)
    return state


def run(text: str = "Microsoft is cutting 60,000 jobs!!! Share before they delete this") -> list[pipeline.Event]:
    return list(pipeline.check_stream(text))


def stages(events: list[pipeline.Event]) -> list[str]:
    return [e.stage for e in events]


# --- tests ---------------------------------------------------------------------------------------

def test_non_factual_input_yields_only_analyse_and_done_with_the_not_checkable_message(fakes, monkeypatch):
    fakes["analysis"] = OPINION
    monkeypatch.setattr(pipeline, "gather_coverage", must_not_be_called)

    events = run("Microsoft is the worst company ever")

    assert stages(events) == ["analyse", "done"]
    assert events[-1].report == NOT_CHECKABLE["opinion"]


def test_events_arrive_in_pipeline_order_with_one_judge_event_per_source(fakes):
    events = run()

    assert stages(events) == [
        "analyse", "search", "sources", "index",
        "judge", "judge", "judge",
        "summarise", "summary_token", "summary_token", "done",
    ]
    assert "".join(e.message for e in events if e.stage == "summary_token") == "Three outlets report 60,000 job cuts."


def test_only_selected_sources_are_judged_when_coverage_exceeds_the_cap(fakes):
    fakes["articles"] = [on_topic(n) for n in range(MAX_SOURCES + 3)]

    events = run()

    assert stages(events).count("judge") == MAX_SOURCES
    assert len(fakes["judged"]) == MAX_SOURCES
    assert f"from {MAX_SOURCES + 3} independent sources; checking {MAX_SOURCES}" in events[2].message


def test_done_carries_the_report(fakes):
    done = run()[-1]

    assert done.stage == "done"
    assert done.report.startswith(f"CLAIM CHECKED: {CLAIM}")
    assert "3 independent source(s) report the same thing as the post." in done.report
    for n in (1, 2, 3):
        assert f"https://outlet{n}.example/story" in done.report
    assert done.report.rstrip().endswith(DISCLAIMER)


def test_a_source_whose_judge_raises_is_reported_as_unchecked_and_the_check_completes(fakes):
    def flaky(claim, article, excerpt=None):
        if "outlet2" in article.url:
            raise RuntimeError("rate limited")
        return supporting(claim, article, excerpt)

    fakes["judge"] = flaky

    events = run()

    assert events[-1].stage == "done"
    report = events[-1].report
    assert "- Outlet 2 headline  (couldn't be checked right now)" in report
    assert "2 independent source(s) report the same thing as the post." in report


def test_a_summary_failure_still_yields_done(fakes):
    def broken(claim, verdicts):
        yield "Partial "
        raise RuntimeError("stream dropped")

    fakes["summary"] = broken

    events = run()

    tokens = [e.message for e in events if e.stage == "summary_token"]
    assert tokens == ["Partial ", "(The summary couldn't be written right now; see the sources below.)"]
    assert events[-1].stage == "done"
    assert events[-1].report.startswith("CLAIM CHECKED:")


def test_a_source_with_nothing_above_the_relevance_floor_is_not_sent_to_the_judge(fakes):
    fakes["articles"] = [on_topic(1), OFF_TOPIC]

    done = run()[-1]

    assert fakes["judged"] == ["https://outlet1.example/story"]
    assert "- Rain expected  (doesn't address this claim)" in done.report


def test_check_returns_the_same_report_as_the_done_event(fakes):
    streamed = run()[-1].report

    assert pipeline.check("Microsoft is cutting 60,000 jobs!!! Share before they delete this") == streamed
