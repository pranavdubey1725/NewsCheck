import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import BaseModel, field_validator
from tavily import TavilyClient

load_dotenv()

# Provisional: midpoint of the gap between irrelevant (≤0.18) and relevant (≥0.60) scores seen so far.
MIN_SCORE = 0.4
MAX_RESULTS = 5

# newscheck checks posts FROM social media, so posts ON social media are never evidence (circular).
EXCLUDED_DOMAINS = [
    "instagram.com", "facebook.com", "x.com", "twitter.com", "threads.net",
    "youtube.com", "tiktok.com", "reddit.com", "whatsapp.com", "t.me",
    "linkedin.com", "quora.com", "pinterest.com", "snapchat.com", "tumblr.com",
]

_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


class SearchResult(BaseModel):
    url: str
    title: str
    content: str
    score: float
    published_date: datetime | None = None
    raw_content: str | None = None  # full page text, when Tavily could extract it

    @field_validator("published_date", mode="before")
    @classmethod
    def parse_rfc2822(cls, v):
        if isinstance(v, str):
            try:
                return parsedate_to_datetime(v)
            except (TypeError, ValueError):
                return None
        return v


def is_excluded(url: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.").removeprefix("m.")
    return any(host == d or host.endswith("." + d) for d in EXCLUDED_DOMAINS)


def search_news(query: str, max_results: int = MAX_RESULTS) -> list[SearchResult]:
    response = _client.search(
        query=query,
        topic="news",
        time_range="month",
        max_results=max_results,
        include_raw_content="text",
        exclude_domains=EXCLUDED_DOMAINS,
    )
    results = [SearchResult.model_validate(r) for r in response.get("results", [])]
    return [r for r in results if r.score >= MIN_SCORE and not is_excluded(r.url)]