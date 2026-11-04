from newscheck.chunks import chunk_sentences, split_sentences

TEXT = (
    "Microsoft offered buyouts to 60,000 employees. The offer is voluntary. "
    "Staff have until December to decide. The company said layoffs remain possible. "
    "Shares rose one percent on Monday."
)


def test_no_sentence_is_ever_cut():
    chunks = chunk_sentences(TEXT, target_words=8)
    for sentence in split_sentences(TEXT):
        assert any(sentence in chunk for chunk in chunks)


def test_neighbouring_chunks_share_one_sentence():
    chunks = chunk_sentences(TEXT, target_words=8, overlap=1)
    for a, b in zip(chunks, chunks[1:]):
        assert split_sentences(a)[-1] == split_sentences(b)[0]


def test_short_text_is_one_chunk():
    assert chunk_sentences("One short sentence.", target_words=150) == ["One short sentence."]


def test_empty_text_gives_no_chunks():
    assert chunk_sentences("") == []