import json

import httpx

TEXT = "BREAKING 🚨 Microsoft is kicking out 60,000 employees!!! Share before it's deleted 😱"

with httpx.stream("POST", "http://127.0.0.1:8000/check", json={"text": TEXT}, timeout=120) as response:
    for line in response.iter_lines():
        if not line.startswith("data: "):
            continue
        event = json.loads(line.removeprefix("data: "))
        print(f"[{event['stage']}] {event['message']}")
        if event["report"]:
            print("\n" + event["report"])