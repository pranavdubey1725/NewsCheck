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