from newscheck.report import DISCLAIMER, headline


def test_no_coverage_is_never_called_false():
    text = headline([])
    assert "not evidence" in text
    assert "false" not in text.replace("is not evidence that the claim is false", "")


def test_disclaimer_says_we_do_not_decide_truth():
    assert "does not decide whether a claim is true" in DISCLAIMER