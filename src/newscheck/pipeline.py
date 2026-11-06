from newscheck.chunks import chunk_sentences
from newscheck.claims import analyse_input
from newscheck.index import RELEVANCE_FLOOR, Passage, PassageIndex
from newscheck.judge import ArticleVerdict, judge_article
from newscheck.report import render, render_not_checkable
from newscheck.search import search_news
from newscheck.sources import group_into_sources

PASSAGES_PER_SOURCE = 2


def check(text: str) -> str:
    analysis = analyse_input(text)
    if analysis.input_type != "factual_claim":
        return render_not_checkable(analysis)

    articles = search_news(analysis.claim)
    groups = group_into_sources(articles)

    index = PassageIndex()
    representatives = []
    for source_id, group in enumerate(groups):
        rep = max(group, key=lambda a: len(a.raw_content or a.content))
        representatives.append(rep)
        chunks = chunk_sentences(rep.raw_content or rep.content)
        index.add([Passage(text=c, url=rep.url, title=rep.title, source_id=source_id) for c in chunks])

    verdicts = []
    for source_id, (group, rep) in enumerate(zip(groups, representatives)):
        hits = index.search_source_hybrid(analysis.claim, source_id, k=PASSAGES_PER_SOURCE)
        relevant = [h for h in hits if h.score >= RELEVANCE_FLOOR]
        if relevant:
            excerpt = "\n\n".join(h.passage.text for h in relevant)
            verdict = judge_article(analysis.claim, rep, excerpt)
        else:
            verdict = ArticleVerdict(article=rep)   # nothing relevant: no LLM call
        verdict.copies = [a for a in group if a is not rep]
        verdicts.append(verdict)

    return render(analysis, verdicts)