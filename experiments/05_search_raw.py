import json
import os

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

response = client.search(
    query="Microsoft offers voluntary exit to 60,000 employees",
    topic="news",
    time_range="month",
    max_results=5,
)

print(json.dumps(response, indent=2, ensure_ascii=False))