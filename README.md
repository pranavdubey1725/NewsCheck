---
title: newscheck
emoji: 📰
colorFrom: gray
colorTo: red
sdk: docker
app_port: 7860
pinned: false
short_description: See what independent news says about a viral post
---

# newscheck

Paste a viral social-media post. newscheck finds recent news coverage of the claim in it and reports **what independent news sources say** about it: which sources report the same thing, which report something different (with an exact quote and a link), and which don't address it.

newscheck never decides whether a claim is true. There is no truth score, no "fake" label and no verdict. The output is an evidence report, and every report ends with:

> newscheck shows what news articles say. It does not decide whether a claim is true.

**Why:** viral posts spread faster than fact-checks. A reader who can see in a minute that three independent outlets describe the same event differently ("voluntary buyouts", not "kicking out") can judge the post for themselves. A tool that hands out true/false labels has to be right every time, but a tool that shows its sources only has to quote them accurately. Accurate quoting is something code can verify.

## How a check works

```
  post (English text)
        │
        ▼
 1. analyse ── classify: factual_claim / opinion / prediction / needs_context / not_a_claim
        │      (not a factual claim → stop: "nothing to check")
        │      rewrite the claim as one neutral sentence; opinions are "set aside", not dropped
        ▼
 2. search ─── agent chooses news queries (tool calling, max 4)
        │      + code always adds one "<claim> fact check" search
        ▼
 3. sources ── group syndicated copies (5-word shingles, Jaccard / containment,
        │      connected components) → independent sources; judge at most 6,
        │      2 slots reserved for fact-check results
        ▼
 4. retrieve ─ one representative article per source → sentence chunks → embeddings
        │      → per-source hybrid search (dense + BM25, RRF) → relevance floor
        │      (nothing clears the floor → no LLM call for that source)
        ▼
 5. judge ──── per source, check each claim detail; stance computed in code;
        │      evidence quote verified against the passages (one retry, then not_addressed)
        ▼
 6. report ─── stream progress + an evidence-only summary, then a deterministic report
```

| Step | Module |
|---|---|
| 1. Claim analysis | `src/newscheck/claims.py` |
| 2. Search agent | `src/newscheck/agent.py`, `src/newscheck/search.py` |
| 3. Independent sources | `src/newscheck/overlap.py`, `src/newscheck/sources.py` |
| 4. Retrieval | `src/newscheck/chunks.py`, `src/newscheck/embeddings.py`, `src/newscheck/index.py` |
| 5. Judge | `src/newscheck/judge.py` |
| 6. Summary, report, streaming | `src/newscheck/summary.py`, `src/newscheck/report.py`, `src/newscheck/pipeline.py`, `src/newscheck/api.py` |

All model calls go through `src/newscheck/llm.py` (Groq, `openai/gpt-oss-20b`), and all searches go through `src/newscheck/search.py` (Tavily).

**Stack:** Python 3.13, uv, Groq, Tavily, fastembed (`BAAI/bge-small-en-v1.5`), Qdrant (in memory), rank-bm25, FastAPI + uvicorn (Server-Sent Events), pydantic v2, MCP Python SDK, pytest, ruff.

## How to run

### 1. Install

```bash
uv sync
```

### 2. API keys

Create a `.env` file in the project root (it is git-ignored):

```
GROQ_API_KEY=your-groq-key
TAVILY_API_KEY=your-tavily-key
```

Every check spends real Tavily credits and Groq tokens (see *Known limitations* for the free-tier limits).

### 3. Start the API

```bash
uv run uvicorn newscheck.api:app
```

`POST /check` with `{"text": "..."}` streams Server-Sent Events: one `data: {...}` line per progress step (`analyse`, `search`, `sources`, `index`, `judge`, `summarise`, `summary_token`), then a final `done` event that carries the full report. If something fails, the stream ends with an `error` event.

```bash
curl -N -X POST http://127.0.0.1:8000/check \
  -H "Content-Type: application/json" \
  -d '{"text": "BREAKING: Microsoft is kicking out 60,000 employees!!! Share before it gets deleted"}'
```

FastAPI's interactive docs are at http://127.0.0.1:8000/docs.

### 4. Use it from an MCP client (e.g. Claude Desktop)

newscheck also runs as an MCP server over stdio, with one tool: `check_claim(text) -> report`.

```bash
uv run python -m newscheck.mcp_server
# or
uv run newscheck-mcp
```

To register it in Claude Desktop, add it to `claude_desktop_config.json`, replacing the path with your clone:

```json
{
  "mcpServers": {
    "newscheck": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/newscheck", "python", "-m", "newscheck.mcp_server"]
    }
  }
}
```

On Windows, use a path like `"C:\\path\\to\\newscheck"`. The `.env` keys are read from the project folder. A check runs the full pipeline, so each tool call spends credits and can take a minute.

## Tests and evals

### Tests

```bash
uv run pytest
uv run ruff check src tests eval
```

The test suite is offline and finishes in a few seconds. Groq, Tavily and the embedding model are replaced with fakes (`monkeypatch`), so the tests never touch the network or spend credits. They cover the decisions below: copy detection, source selection, quote verification and the retry message, stance derivation, the search agent's limits and fact-check search, the end-to-end event order of `check_stream`, failure handling, and the MCP tool.

### Evals

| Script | Measures | Cost |
|---|---|---|
| `eval/retrieval_eval.py` | For each frozen case with a gold phrase, is that phrase in the source's top-k retrieved passages (hit@k)? Compares chunkers (sentence, semantic, fixed-size) and retrieval modes (dense, hybrid). | No API calls. Runs on frozen text plus the local embedding model. |
| `eval/floor_eval.py` | Best passage scores for answerable sources vs unanswerable (cross-story) sources, and how much of each a given relevance floor keeps or silences. | No API calls. Same as above. |
| `eval/agent_eval.py` | Single search vs the search agent, 3 runs per claim: independent sources, fact-check articles (by title keywords), searches, seconds, stability (mean pairwise Jaccard of the outlet sets across runs) and excluded-domain leaks. Saves dated JSON to `eval/results/`. | **Live**, about 70 Tavily credits plus Groq tokens. |

```bash
uv run python eval/retrieval_eval.py
uv run python eval/floor_eval.py
uv run python eval/agent_eval.py   # live: spends credits
```

The retrieval and floor evals read frozen search results in `eval/data/`, which is git-ignored because it contains third-party article text. `eval/freeze.py` creates it (1 Tavily credit per claim). `eval/check_gold.py` verifies that every gold phrase in `eval/cases.json` really appears in its frozen source.

## Key decisions

| Decision | What and why |
|---|---|
| Evidence report, not a truth score | Output is an evidence report, never a truth score. Claim types: `factual_claim`, `opinion`, `prediction`, `needs_context`, `not_a_claim`. Opinions inside factual posts are reported as "set aside", not silently dropped. |
| Verdict casing | Verdict casing is normalised (lowercase/strip) before validation. This was decided in the structured-output experiment (`experiments/03_structured_outputs.py`), before claim analysis replaced verdicts. |
| Search provider | Tavily (news mode, one-month window), chosen for freshness of viral claims. Social media domains are excluded. |
| Syndication detection | Lexical (5-word shingles, Jaccard 0.40 or containment 0.60), not embeddings, because independent same-event articles are semantically near-identical. Chains of partial copies are grouped with connected components. |
| Per-detail judging | The judge checks each claim detail; stance is computed in code. Prompt-only fixes were tried first (field reordering, a stricter rule): no change on frozen inputs. Per-detail checks moved the "kicking out vs voluntary buyouts" case from 2 wrong supports to 0–1. |
| Verified quotes | Evidence quotes must appear in the text (normalised for case, whitespace and quote marks). Fuzzy matching was rejected because it accepts changed numbers. One retry with feedback, then downgrade to `not_addressed`. |
| Chunking | Sentence-aware, 150 words, 1-sentence overlap. Retrieval eval (29 frozen cases, hybrid, hit@2): sentence 0.79; semantic 0.72 / 0.62 / 0.55 (thresholds 0.45 / 0.55 / 0.65); fixed-size 0.55. |
| Retrieval | Per-source top-2 (Qdrant payload filter). Hybrid dense + BM25 (RRF), adopted as a bet on number-heavy viral claims: hit@2 unchanged at 23/29 (+2 on claims sharing numbers or names, −2 on a heavy paraphrase); hit@1 0.55 → 0.66. To be revisited as the eval grows. |
| Relevance floor 0.55 | Keeps 100% of answerable sources and silences 75% of cross-story noise (0.50: 100% / 67%; 0.60: 97% / 90%). Recall is preferred because a silenced source cannot be recovered, and the judge is a second check. |
| Search agent | The model chooses queries; code enforces the limits, always adds a fact-check search (+1 credit; the prompt-only version was never followed), and the claim is read-only. |
| Not built on purpose | Multi-tenancy (only public data; per-check collection isolation instead). LangGraph (single loop, no branches). |

## Known limitations

- Two facts in one post become one claim.
- Hinglish is silently translated and can gain details.
- Sarcasm can leak into the claim.
- The domain blocklist cannot catch forum or comment pages on news sites.
- The streamed summary is free text and can overstate agreement.
- Live search results drift between runs.
- Copy detection runs on Tavily excerpts.
- Thresholds are calibrated on small evals.
- English only.
- Tavily's free tier is 1,000 credits/month, and Groq's free tier is 8,000 tokens/minute.

## Project history

v1 was built quickly with an AI agent. This v2 was rebuilt from scratch one decision at a time, with one PR per feature. The scripts in `experiments/` are the learning history: each one tried a single idea (structured outputs, raw vs wrapped search, overlap, chunking, embeddings, per-source retrieval, streaming, the agent) before it became part of `src/newscheck/`.
