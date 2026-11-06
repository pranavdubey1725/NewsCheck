from collections.abc import Iterator
from urllib.parse import urlparse

from pydantic import BaseModel

from newscheck.chunks import chunk_sentences
from newscheck.claims import analyse_input
from newscheck.index import RELEVANCE_FLOOR, Passage, PassageIndex
from newscheck.judge import ArticleVerdict, judge_article
from newscheck.report import render, render_not_checkable
from newscheck.search import search_news
from newscheck.sources import group_into_sources

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

    yield Event(stage="search", message=f"Searching the news for: {analysis.claim}")
    articles = search_news(analysis.claim)
    groups = group_into_sources(articles)
    yield Event(stage="sources", message=f"Found {len(articles)} articles from {len(groups)} independent sources")

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
        if relevant:
            verdict = judge_article(analysis.claim, rep, "\n\n".join(h.passage.text for h in relevant))
        else:
            verdict = ArticleVerdict(article=rep)
        verdict.copies = [a for a in group if a is not rep]
        verdicts.append(verdict)

    yield Event(stage="done", message="Done", report=render(analysis, verdicts))


def check(text: str) -> str:
    """Run the whole check and return only the final report."""
    *_, last = check_stream(text)
    return last.report