from newscheck.overlap import containment, jaccard, shingles

WIRE = (
    "Microsoft has offered 60,000 employees or about 27 percent of its global workforce "
    "voluntary buyouts as the software giant spends heavily on artificial intelligence "
    "the company said the offer is time limited and built on an earlier retirement program"
)


def test_identical_texts_score_one():
    s = shingles("Microsoft has offered 60,000 employees voluntary buyouts this week")
    assert jaccard(s, s) == 1.0


def test_unrelated_texts_score_zero():
    a = shingles("Microsoft has offered 60,000 employees voluntary buyouts this week")
    b = shingles("The central bank kept interest rates unchanged on Thursday morning")
    assert jaccard(a, b) == 0.0


def test_punctuation_and_case_are_ignored():
    a = shingles("Microsoft has offered “60,000” employees voluntary buyouts")
    b = shingles("microsoft HAS offered 60,000 employees, voluntary buyouts!")
    assert jaccard(a, b) == 1.0


def test_empty_text_never_matches():
    assert jaccard(shingles(""), shingles("")) == 0.0


def test_trimmed_copy_has_low_jaccard_but_full_containment():
    full = shingles(WIRE)
    trimmed = shingles(" ".join(WIRE.split()[:15]))
    assert jaccard(full, trimmed) < 0.5
    assert containment(full, trimmed) == 1.0


def test_containment_of_unrelated_texts_is_zero():
    a = shingles(WIRE)
    b = shingles("The central bank kept interest rates unchanged on Thursday morning")
    assert containment(a, b) == 0.0