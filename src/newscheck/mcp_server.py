"""newscheck as an MCP server (stdio). One tool: check_claim.

Run:  uv run python -m newscheck.mcp_server   (or: uv run newscheck-mcp)
"""
import contextlib
import sys

from mcp.server.mcpserver import MCPServer

from newscheck import pipeline

TOOL_DESCRIPTION = (
    "Check a viral social media post (English text) against recent news coverage. "
    "Returns a report of what independent news sources say about the post's claim: which agree, "
    "which report something different (with quotes and links), and which don't address it. "
    "newscheck reports what news sources say; it never decides whether a claim is true or false. "
    "Opinions, predictions and vague posts are reported as not checkable. "
    "A check searches the news live and can take a minute."
)

server = MCPServer(
    "newscheck",
    instructions="newscheck reports what news sources say about a claim. It never decides whether the claim is true.",
)


@server.tool(description=TOOL_DESCRIPTION)
def check_claim(text: str) -> str:
    # On stdio, stdout carries the MCP protocol: the pipeline's developer logs must go to stderr.
    with contextlib.redirect_stdout(sys.stderr):
        return pipeline.check(text)


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
