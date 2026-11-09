import asyncio

from newscheck import mcp_server, pipeline

REPORT = "CLAIM CHECKED: Microsoft is cutting 60,000 jobs.\n\nnewscheck shows what news articles say."


def test_check_claim_returns_the_pipeline_report(monkeypatch):
    seen = []
    monkeypatch.setattr(pipeline, "check", lambda text: seen.append(text) or REPORT)

    assert mcp_server.check_claim("Microsoft is cutting 60,000 jobs!!!") == REPORT
    assert seen == ["Microsoft is cutting 60,000 jobs!!!"]   # the post is passed through unchanged


def test_the_server_exposes_exactly_one_tool_that_never_decides_truth():
    tools = asyncio.run(mcp_server.server.list_tools())

    assert [t.name for t in tools] == ["check_claim"]
    assert tools[0].input_schema["required"] == ["text"]
    description = tools[0].description.lower()
    assert "never decides whether a claim is true" in description
    assert "what news sources say" in description


def test_calling_the_tool_over_mcp_returns_the_report_as_text(monkeypatch):
    monkeypatch.setattr(pipeline, "check", lambda text: REPORT)

    result = asyncio.run(mcp_server.server.call_tool("check_claim", {"text": "any post"}))

    assert not result.is_error
    assert [c.text for c in result.content] == [REPORT]


def test_pipeline_logs_go_to_stderr_so_they_cannot_corrupt_the_stdio_protocol(monkeypatch, capsys):
    def noisy_check(text):
        print("[retry] evidence quote not found, asking again")
        return REPORT

    monkeypatch.setattr(pipeline, "check", noisy_check)

    assert mcp_server.check_claim("any post") == REPORT
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "[retry]" in captured.err
