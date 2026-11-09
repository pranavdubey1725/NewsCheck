import copy
import json
from types import SimpleNamespace

import pytest

from newscheck import agent
from newscheck.agent import FACT_CHECK_SUFFIX, MAX_SEARCHES, gather_coverage
from newscheck.search import SearchResult

CLAIM = "RBI announced that ₹10, ₹20 and ₹50 notes would be in short supply before Diwali 2026."
FACT_CHECK_QUERY = f"{CLAIM} {FACT_CHECK_SUFFIX}"

# One shared body: every fake article is a copy of the others, so they form ONE independent source
# and the agent's "enough sources" stop never fires. Only the search limit can end the loop.
SYNDICATED_BODY = " ".join(f"word{i}" for i in range(40))


def article(url: str) -> SearchResult:
    return SearchResult(url=url, title="Same story", content=SYNDICATED_BODY, score=0.9)


def tool_call(arguments: str, call_id: str = "call") -> SimpleNamespace:
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name="search_news", arguments=arguments))


def search_call(query: str, call_id: str = "call") -> SimpleNamespace:
    return tool_call(json.dumps({"query": query}), call_id)


def reply(*tool_calls) -> SimpleNamespace:
    return SimpleNamespace(content="", tool_calls=list(tool_calls) or None)


class FakeChat:
    """Plays back scripted model replies; records what the model was shown at each turn.

    `seen` holds a snapshot per turn; `conversation` is the live list, including tool results
    appended after the model's last turn.
    """

    def __init__(self, replies, repeat_last=False):
        self.replies = list(replies)
        self.repeat_last = repeat_last
        self.seen: list[list[dict]] = []
        self.conversation: list[dict] = []

    def __call__(self, messages, tools=None):
        self.conversation = messages
        self.seen.append(copy.deepcopy(messages))
        if self.repeat_last and len(self.replies) == 1:
            return self.replies[0]
        return self.replies.pop(0) if self.replies else reply()


class FakeSearch:
    """Returns scripted results per query (default: one unique article per query); records queries."""

    def __init__(self, results_by_query=None):
        self.results_by_query = results_by_query or {}
        self.queries: list[str] = []

    def __call__(self, query, max_results=5):
        self.queries.append(query)
        if query in self.results_by_query:
            return self.results_by_query[query]
        return [article(f"https://news{len(self.queries)}.example/{len(self.queries)}")]


@pytest.fixture
def fake_search(monkeypatch):
    def install(results_by_query=None):
        search = FakeSearch(results_by_query)
        monkeypatch.setattr(agent, "search_news", search)
        return search
    return install


@pytest.fixture
def fake_chat(monkeypatch):
    def install(replies, repeat_last=False):
        chat = FakeChat(replies, repeat_last)
        monkeypatch.setattr(agent, "chat", chat)
        return chat
    return install


def tool_messages(messages: list[dict]) -> list[str]:
    return [m["content"] for m in messages if m["role"] == "tool"]


def test_fact_check_search_always_runs_last(fake_chat, fake_search):
    fake_chat([reply(search_call("RBI coin shortage")), reply(search_call("small notes supply Diwali")), reply()])
    search = fake_search()

    _, queries, _ = gather_coverage(CLAIM)

    assert queries == ["RBI coin shortage", "small notes supply Diwali", FACT_CHECK_QUERY]
    assert search.queries[-1] == FACT_CHECK_QUERY


def test_fact_check_search_runs_even_if_the_model_never_searches(fake_chat, fake_search):
    fake_chat([reply()])
    search = fake_search()

    _, queries, _ = gather_coverage(CLAIM)

    assert queries == [FACT_CHECK_QUERY]
    assert search.queries == [FACT_CHECK_QUERY]


def test_max_searches_is_never_exceeded_even_if_the_model_keeps_calling_the_tool(fake_chat, fake_search):
    # The model asks for three searches per turn, forever.
    greedy = reply(*(search_call(f"query {i}", f"call{i}") for i in range(3)))
    fake_chat([greedy], repeat_last=True)
    search = fake_search()

    _, queries, _ = gather_coverage(CLAIM)

    assert len(search.queries) == MAX_SEARCHES + 1           # the agent's limit, plus the code's fact-check search
    assert queries == search.queries
    assert queries[-1] == FACT_CHECK_QUERY


def test_extra_tool_calls_past_the_limit_get_a_limit_message(fake_chat, fake_search):
    calls = [search_call(f"query {i}", f"call{i}") for i in range(MAX_SEARCHES + 2)]
    chat = fake_chat([reply(*calls), reply()])
    search = fake_search()

    gather_coverage(CLAIM)

    assert len(search.queries) == MAX_SEARCHES + 1
    results = tool_messages(chat.conversation)
    assert len(results) == MAX_SEARCHES + 2                   # every tool call still gets an answer
    assert results[MAX_SEARCHES:] == ["Search limit reached. Do not search again."] * 2


@pytest.mark.parametrize("arguments", ["{not json", '{"query": ""}', '{"query": "   "}', "{}"])
def test_malformed_tool_arguments_produce_an_error_tool_message_not_a_crash(fake_chat, fake_search, arguments):
    chat = fake_chat([reply(tool_call(arguments, "bad")), reply()])
    search = fake_search()

    articles, queries, _ = gather_coverage(CLAIM)

    assert tool_messages(chat.seen[-1]) == ["Invalid call: provide a non-empty 'query'."]
    assert search.queries == [FACT_CHECK_QUERY]                # the bad call searched nothing
    assert queries == [FACT_CHECK_QUERY]
    assert len(articles) == 1


def test_claim_text_is_never_changed(fake_chat, fake_search):
    fake_chat([reply(search_call("rewritten: RBI says notes are fine")), reply()])
    search = fake_search()

    _, queries, _ = gather_coverage(CLAIM)

    # The model's rewording stays its own query; the fact-check search uses the claim exactly as given.
    assert queries[-1] == f"{CLAIM} {FACT_CHECK_SUFFIX}"
    assert search.queries[-1] == f"{CLAIM} {FACT_CHECK_SUFFIX}"


def test_claim_reaches_the_model_verbatim_inside_claim_tags(fake_chat, fake_search):
    chat = fake_chat([reply()])
    fake_search()

    gather_coverage(CLAIM)

    user_messages = [m["content"] for m in chat.seen[0] if m["role"] == "user"]
    assert user_messages == [f"<claim>\n{CLAIM}\n</claim>"]


def test_articles_are_deduplicated_by_url(fake_chat, fake_search):
    a, b, c = article("https://a.example/1"), article("https://b.example/2"), article("https://c.example/3")
    a_again = SearchResult(url=a.url, title="Updated headline", content="different text", score=0.5)
    fake_chat([reply(search_call("first")), reply(search_call("second")), reply()])
    fake_search({"first": [a, b], "second": [a_again, c], FACT_CHECK_QUERY: [b, c]})

    articles, _, _ = gather_coverage(CLAIM)

    assert [x.url for x in articles] == [a.url, b.url, c.url]
    assert articles[0].title == "Same story"                  # the first copy found is kept


def test_fact_check_urls_contain_only_articles_first_found_by_the_fact_check_search(fake_chat, fake_search):
    seen_before = article("https://already.example/1")
    only_fact_check = article("https://factcheck.example/2")
    fake_chat([reply(search_call("first")), reply()])
    fake_search({"first": [seen_before], FACT_CHECK_QUERY: [seen_before, only_fact_check]})

    articles, _, fact_check_urls = gather_coverage(CLAIM)

    assert fact_check_urls == {only_fact_check.url}
    assert {x.url for x in articles} == {seen_before.url, only_fact_check.url}
