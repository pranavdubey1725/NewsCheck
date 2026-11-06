import numpy as np

from newscheck.embeddings import embed_passages

def chunk_fixed(text: str, size: int = 600) -> list[str]:
    """Cut text into pieces of `size` characters. Deliberately naive."""
    return [text[i : i + size] for i in range(0, len(text), size)]
#This function takes a long article and divides the information into chunks of 600 characters each


import re

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    """Split on sentence-ending punctuation followed by space, and on every newline."""
    return [s.strip() for s in _SENTENCE_BREAK.split(text) if s.strip()]


def chunk_sentences(text: str, target_words: int = 150, overlap: int = 1) -> list[str]:
    """Group whole sentences into chunks of about target_words, sharing `overlap` sentences between neighbours."""
    sentences = split_sentences(text)
    chunks: list[str] = []
    i = 0
    while i < len(sentences):
        words, j = 0, i
        while j < len(sentences) and (words < target_words or j == i):
            words += len(sentences[j].split())
            j += 1
        chunks.append(" ".join(sentences[i:j]))
        if j >= len(sentences):
            break
        i = max(i + 1, j - overlap)
    return chunks



def chunk_semantic(text: str, threshold: float = 0.55, max_words: int = 200) -> list[str]:
    """Start a new chunk wherever two neighbouring sentences are less similar than `threshold`."""
    sentences = split_sentences(text)
    if not sentences:
        return []
    vectors = np.array(embed_passages(sentences))
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    chunks, current, words = [], [sentences[0]], len(sentences[0].split())
    for i in range(1, len(sentences)):
        similarity = float(vectors[i] @ vectors[i - 1])
        n = len(sentences[i].split())
        if similarity < threshold or words + n > max_words:
            chunks.append(" ".join(current))
            current, words = [], 0
        current.append(sentences[i])
        words += n
    chunks.append(" ".join(current))
    return chunks