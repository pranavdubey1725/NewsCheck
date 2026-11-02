from collections import Counter

from newscheck.claims import ClaimAnalysis
from newscheck.judge import ArticleVerdict

NOT_CHECKABLE = {
    "opinion": "This is an opinion, so there is nothing to check.",
    "prediction": "This is about the future, so it can't be checked yet.",
    "needs_context": "This is too vague to check. Say who or what it is about.",
    "not_a_claim": "There is nothing here to check.",
}

STANCE_LABELS = {
    "supports": "agrees with the post",
    "contradicts": "disagrees with the post",
    "not_addressed": "doesn't address this claim",
}

DISCLAIMER = "newscheck shows what news articles say. It does not decide whether a claim is true."


def render_not_checkable(analysis: ClaimAnalysis) -> str:
    return NOT_CHECKABLE[analysis.input_type]


def headline(verdicts: list[ArticleVerdict]) -> str:
    if not verdicts:
        return "No matching news coverage found. This is not evidence that the claim is false."
    counts = Counter(v.stance for v in verdicts)
    agree, disagree = counts["supports"], counts["contradicts"]
    if agree == 0 and disagree == 0:
        return "Articles were found, but none of them addresses this specific claim."
    if disagree and not agree:
        return f"{disagree} article(s) report something different from the post."
    if agree and not disagree:
        return f"{agree} article(s) report the same thing as the post."
    return f"Articles are split: {agree} agree with the post, {disagree} disagree."


def render(analysis: ClaimAnalysis, verdicts: list[ArticleVerdict]) -> str:
    lines = [f"CLAIM CHECKED: {analysis.claim}"]
    if analysis.opinion_set_aside:
        lines.append(f"NOT CHECKED (opinion): {analysis.opinion_set_aside}")
    lines += ["", headline(verdicts)]

    order = {"contradicts": 0, "supports": 1, "not_addressed": 2}
    for v in sorted(verdicts, key=lambda v: order[v.stance]):
        lines += ["", f"- {v.article.title}  ({STANCE_LABELS[v.stance]})"]
        if v.stance != "not_addressed":
            lines.append(f'    "{v.judgement.evidence}"')
        if v.stance == "contradicts" and v.judgement.conflicting_detail:
            lines.append(f"    Reports instead: {v.judgement.conflicting_detail}")
        lines.append(f"    {v.article.url}")

    lines += ["", DISCLAIMER]
    return "\n".join(lines)