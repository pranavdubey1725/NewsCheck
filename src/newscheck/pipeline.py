from newscheck.claims import analyse_input
from newscheck.judge import judge_article
from newscheck.report import render, render_not_checkable
from newscheck.search import search_news


def check(text: str) -> str:
    analysis = analyse_input(text)
    if analysis.input_type != "factual_claim":
        return render_not_checkable(analysis)
    articles = search_news(analysis.claim)
    verdicts = [judge_article(analysis.claim, a) for a in articles]
    return render(analysis, verdicts)