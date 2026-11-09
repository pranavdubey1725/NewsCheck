import importlib.util
from pathlib import Path

import pytest

import newscheck.agent
import newscheck.search

EVAL_SCRIPT = Path(__file__).resolve().parents[1] / "eval" / "agent_eval.py"


def _no_live_calls(*args, **kwargs):
    raise AssertionError("agent_eval must not search or call the model when imported")


def load_agent_eval():
    """eval/ is a folder of scripts, not a package: load agent_eval.py by path, with live calls blocked."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(newscheck.search, "search_news", _no_live_calls)
        mp.setattr(newscheck.agent, "gather_coverage", _no_live_calls)
        spec = importlib.util.spec_from_file_location("agent_eval", EVAL_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


agent_eval = load_agent_eval()


def test_same_outlets_every_run_is_fully_stable():
    runs = [{"bbc.com", "reuters.com"}, {"reuters.com", "bbc.com"}, {"bbc.com", "reuters.com"}]
    assert agent_eval.stability(runs) == 1.0


def test_disjoint_outlets_have_zero_stability():
    assert agent_eval.stability([{"bbc.com"}, {"reuters.com"}, {"thehindu.com"}]) == 0.0


def test_stability_is_mean_pairwise_jaccard():
    # pairs: (a,b) 1/3, (a,c) 1/1, (b,c) 1/3  ->  mean 5/9
    a, b, c = {"x", "y"}, {"y", "z"}, {"x", "y"}
    assert agent_eval.stability([a, b, c]) == pytest.approx(5 / 9)


def test_stability_with_fewer_than_two_runs_is_one():
    assert agent_eval.stability([{"bbc.com"}]) == 1.0
    assert agent_eval.stability([]) == 1.0


def test_two_runs_that_found_nothing_count_as_stable():
    assert agent_eval.stability([set(), set()]) == 1.0


def test_fact_check_titles_are_recognised_case_insensitively():
    for title in [
        "FACT CHECK: Microsoft is not firing 60,000",
        "Fake news alert: RBI notes shortage claim",
        "PIB Fact-Check debunks viral post",
        "Infosys denies layoff report",
        "Company clarifies its hiring plans",
    ]:
        assert agent_eval.is_fact_check(title), title


def test_ordinary_news_titles_are_not_fact_checks():
    for title in ["Microsoft offers voluntary buyouts to staff", "Tamil Nadu announces school holiday"]:
        assert not agent_eval.is_fact_check(title), title


def test_outlet_strips_www_and_mobile_prefixes():
    assert agent_eval.outlet("https://www.thehindu.com/news/a") == "thehindu.com"
    assert agent_eval.outlet("https://m.economictimes.com/b?x=1") == "economictimes.com"
    assert agent_eval.outlet("https://edition.cnn.com/c") == "edition.cnn.com"


def test_importing_the_eval_runs_nothing_live():
    # The live loop is behind main(); loading the script must not spend credits (load would raise).
    assert callable(load_agent_eval().main)
