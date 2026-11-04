import os
from datetime import datetime
from email.utils import parsedate_to_datetime

from dotenv import load_dotenv
from pydantic import BaseModel, field_validator
from tavily import TavilyClient

load_dotenv()

# Provisional: midpoint of the gap between irrelevant (≤0.18) and relevant (≥0.60) scores seen so far.
MIN_SCORE = 0.4
MAX_RESULTS = 5

_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


class SearchResult(BaseModel):
    url: str
    title: str
    content: str
    score: float
    published_date: datetime | None = None
    raw_content: str | None = None  # full page text, when Tavily could extract it, no need for markdown (due to extra symbols)

    @field_validator("published_date", mode="before")
    @classmethod
    def parse_rfc2822(cls, v):
        if isinstance(v, str):
            try:
                return parsedate_to_datetime(v)
            except (TypeError, ValueError):
                return None
        return v


def search_news(query: str, max_results: int = MAX_RESULTS) -> list[SearchResult]:
    response = _client.search(
        query=query,
        topic="news",
        time_range="month",
        max_results=max_results,
        include_raw_content="text",
    )
    results = [SearchResult.model_validate(r) for r in response.get("results", [])]
    return [r for r in results if r.score >= MIN_SCORE]