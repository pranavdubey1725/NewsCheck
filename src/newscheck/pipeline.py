from newscheck.claims import analyse_input
from newscheck.judge import judge_article
from newscheck.report import render, render_not_checkable
from newscheck.search import search_news
from newscheck.sources import group_into_sources


def check(text: str) -> str:
    analysis = analyse_input(text)
    if analysis.input_type != "factual_claim":
        return render_not_checkable(analysis)

    articles = search_news(analysis.claim)
    verdicts = []
    for group in group_into_sources(articles):
        representative = max(group, key=lambda a: len(a.content))
        verdict = judge_article(analysis.claim, representative)
        verdict.copies = [a for a in group if a is not representative]
        verdicts.append(verdict)
    return render(analysis, verdicts)