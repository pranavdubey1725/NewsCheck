"""Verify every gold phrase really appears in its source's frozen text."""
import json
from pathlib import Path

from newscheck.judge import quote_in_text

cases = json.loads(Path("eval/cases.json").read_text(encoding="utf-8"))
for case in cases:
    data = json.loads(Path(f"eval/data/{case['name']}.json").read_text(encoding="utf-8"))
    texts = {a["url"]: a.get("raw_content") or a["content"] for a in data["articles"]}
    print(f"\n{case['name']}")
    for url, gold in case["gold"].items():
        if url not in texts:
            print(f"  MISSING URL  {url}")
        elif gold is None:
            print(f"  (no gold)    {url}")
        elif quote_in_text(gold, texts[url]):
            print(f"  OK           {url}")
        else:
            print(f"  NOT FOUND    {url}")