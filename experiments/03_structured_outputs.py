import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()                                        # reads .env into environment variables
client = Groq(api_key=os.environ["GROQ_API_KEY"])    # one client, reused for every call

claim = "Humans have 5 legs"
# claim = "square has 4 sides"
# claim = "26/11 happened in Mumbai"

SYSTEM_PROMPT = (
    "You are a careful news analyst. Your training data has a cutoff date and "
    "you cannot see recent news. If a claim could be about events after your "
    "cutoff, say you cannot verify it. Never call a claim false just because "
    "you have no information about it."
    " Reply with ONLY a JSON object of this exact shape: "
    '{"verdict": "true" | "false" | "cannot_verify", "reason": "<one sentence>"}'
)

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    temperature=0,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Is this news claim true? {claim}"},
    ],
)

answer = response.choices[0].message.content

import json   # put this with the other imports at the top

raw = response.choices[0].message.content
print(repr(raw))          # repr shows the exact string, including hidden characters

data = json.loads(raw)    # text → Python dict
print("Verdict:", data["verdict"])
print("Reason: ", data["reason"])