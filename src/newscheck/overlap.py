import re

MIN_SHINGLES = 10  # below this, a text is too short to judge copying either way

# Provisional, from 10 pairs: independent ≤ 0.02 J / 0.09 C; one copied pair 0.63 J / 0.85 C.
# Set well inside both gaps, leaving room for trimmed copies that score lower than the one we've seen.
JACCARD_THRESHOLD = 0.40
CONTAINMENT_THRESHOLD = 0.60


def shingles(text: str, n: int = 5) -> set[tuple[str, ...]]:
    """All runs of n consecutive words, lowercased, ignoring punctuation."""
    words = re.findall(r"[a-z0-9']+", text.lower())
    if not words:
        return set()
    if len(words) < n:
        return {tuple(words)}
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def jaccard(a: set, b: set) -> float:
    """Shared items divided by all distinct items. 0.0 = nothing shared, 1.0 = identical."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def containment(a: set, b: set) -> float:
    """Shared items divided by the size of the smaller set. 1.0 = the smaller text is entirely inside the larger."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def is_copy(a: set, b: set) -> bool:
    """True if two shingle sets look like the same text (a full or partial copy)."""
    if min(len(a), len(b)) < MIN_SHINGLES:
        return False
    return jaccard(a, b) >= JACCARD_THRESHOLD or containment(a, b) >= CONTAINMENT_THRESHOLD