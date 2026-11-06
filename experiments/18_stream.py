import time

from newscheck.pipeline import check_stream

text = "BREAKING 🚨 Microsoft is kicking out 60,000 employees!!! Share before it's deleted 😱"

start = previous = time.perf_counter()
for event in check_stream(text):
    now = time.perf_counter()
    print(f"[{now - start:6.1f}s  +{now - previous:5.1f}s]  {event.message}")
    previous = now
    if event.report:
        print("\n" + event.report)