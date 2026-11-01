import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, field_validator
from tavily import TavilyClient


#We write this file differently because later if tavily becomes the bad choice, we can just change it here 


load_dotenv()

MIN_SCORE = 0.75      # ← your decision goes here (provisional)
MAX_RESULTS = 5

_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


class SearchResult(BaseModel):
    url: str
    title: str
    content: str
    score: float
    published_date: Optional[datetime] = None

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
    )
    results = [SearchResult.model_validate(r) for r in response.get("results", [])]
    return [r for r in results if r.score >= MIN_SCORE]