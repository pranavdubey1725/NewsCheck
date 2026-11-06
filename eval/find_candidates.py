"""Print every sentence containing a keyword, per source, so you can pick the gold sentence."""
import json
import sys
from pathlib import Path

from newscheck.chunks import split_sentences

name, keywords = sys.argv[1], [k.lower() for k in sys.argv[2:]]
data = json.loads(Path(f"eval/data/{name}.json").read_text(encoding="utf-8"))

print(f"CLAIM: {data['claim']}\n")
for a in data["articles"]:
    text = a.get("raw_content") or a["content"]
    hits = [s for s in split_sentences(text) if any(k in s.lower() for k in keywords)]
    print(f"=== {a['url']}")
    for s in hits[:6]:
        print(f"   - {s[:200]}")
    print()