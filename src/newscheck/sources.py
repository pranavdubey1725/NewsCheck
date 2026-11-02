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