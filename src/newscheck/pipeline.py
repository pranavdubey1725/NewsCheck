import traceback
from collections.abc import Iterator
from urllib.parse import urlparse

from pydantic import BaseModel

from newscheck.agent import gather_coverage
from newscheck.chunks import chunk_sentences
from newscheck.claims import analyse_input
from newscheck.index import RELEVANCE_FLOOR, Passage, PassageIndex
from newscheck.judge import ArticleVerdict, judge_article
from newscheck.report import render, render_not_checkable
from newscheck.sources import group_into_sources, select_sources
from newscheck.summary import stream_summary

PASSAGES_PER_SOURCE = 2


class Event(BaseModel):
    stage: str
    message: str
    report: str | None = None   # set only on the final "done" event


def check_stream(text: str) -> Iterator[Event]:
    yield Event(stage="analyse", message="Reading the post")
    analysis = analyse_input(text)
    if analysis.input_type != "factual_claim":
        yield Event(stage="done", message="Done", report=render_not_checkable(analysis))
        return

    yield Event(stage="search", message="Searching the news (choosing several queries)")
    articles, queries, fact_check_urls = gather_coverage(analysis.claim)
    all_groups = group_into_sources(articles)
    groups = select_sources(all_groups, fact_check_urls)
    searched = "; ".join(queries)
    yield Event(
        stage="sources",
        message=(
            f"Searched for: {searched}. Found {len(articles)} articles from {len(all_groups)} "
            f"independent sources; checking {len(groups)} of them"
        ),
    )

    yield Event(stage="index", message="Reading the full articles")
    index = PassageIndex()
    representatives = []
    for source_id, group in enumerate(groups):
        rep = max(group, key=lambda a: len(a.raw_content or a.content))
        representatives.append(rep)
        chunks = chunk_sentences(rep.raw_content or rep.content)
        index.add([Passage(text=c, url=rep.url, title=rep.title, source_id=source_id) for c in chunks])

    verdicts = []
    for source_id, (group, rep) in enumerate(zip(groups, representatives)):
        outlet = urlparse(rep.url).netloc.removeprefix("www.")
        yield Event(stage="judge", message=f"Checking source {source_id + 1} of {len(groups)}: {outlet}")
        hits = index.search_source_hybrid(analysis.claim, source_id, k=PASSAGES_PER_SOURCE)
        relevant = [h for h in hits if h.score >= RELEVANCE_FLOOR]
        if not relevant:
            verdict = ArticleVerdict(article=rep)   # nothing relevant: no LLM call
        else:
            try:
                verdict = judge_article(analysis.claim, rep, "\n\n".join(h.passage.text for h in relevant))
            except Exception:
                traceback.print_exc()               # developer log: the real error
                verdict = ArticleVerdict(article=rep, failed=True)
        verdict.copies = [a for a in group if a is not rep]
        verdicts.append(verdict)

    yield Event(stage="summarise", message="Summarising what the sources say")
    try:
        for token in stream_summary(analysis.claim, verdicts):
            yield Event(stage="summary_token", message=token)
    except Exception:
        traceback.print_exc()
        yield Event(stage="summary_token", message="(The summary couldn't be written right now; see the sources below.)")

    yield Event(stage="done", message="Done", report=render(analysis, verdicts))


def check(text: str) -> str:
    """Run the whole check and return only the final report."""
    *_, last = check_stream(text)
    return last.report