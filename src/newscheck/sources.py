from itertools import combinations

from newscheck.overlap import is_copy, shingles
from newscheck.search import SearchResult


def group_into_sources(articles: list[SearchResult]) -> list[list[SearchResult]]:
    """Group articles that are copies of each other. Each group is one independent source."""
    sets = [shingles(f"{a.title} {a.content}") for a in articles]

    neighbours: dict[int, set[int]] = {i: set() for i in range(len(articles))}
    for i, j in combinations(range(len(articles)), 2):
        if is_copy(sets[i], sets[j]):
            neighbours[i].add(j)
            neighbours[j].add(i)

    seen: set[int] = set()
    groups: list[list[SearchResult]] = []
    for start in range(len(articles)):
        if start in seen:
            continue
        seen.add(start)
        stack, component = [start], []
        while stack:
            i = stack.pop()
            component.append(i)
            for j in neighbours[i]:
                if j not in seen:
                    seen.add(j)
                    stack.append(j)
        groups.append([articles[i] for i in sorted(component)])
    return groups


MAX_SOURCES = 6          # judge at most this many sources per check (rate limits, latency)
RESERVED_FACT_CHECK = 2  # of those, slots kept for sources found by the fact-check search


def select_sources(
    groups: list[list[SearchResult]],
    fact_check_urls: set[str],
    max_sources: int = MAX_SOURCES,
    reserved: int = RESERVED_FACT_CHECK,
) -> list[list[SearchResult]]:
    """Keep at most max_sources groups, guaranteeing up to `reserved` fact-check groups a place."""
    def from_fact_check(group: list[SearchResult]) -> bool:
        return any(a.url in fact_check_urls for a in group)

    fact = [g for g in groups if from_fact_check(g)]
    other = [g for g in groups if not from_fact_check(g)]

    chosen = fact[:reserved]
    chosen += other[: max_sources - len(chosen)]
    chosen += fact[reserved:][: max_sources - len(chosen)]   # unused slots go back to fact-check results
    return chosen