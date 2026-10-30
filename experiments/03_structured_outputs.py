import os
from dotenv import load_dotenv
from groq import Groq

from typing import Literal
from pydantic import BaseModel, Field, ValidationError, field_validator

class Verdict(BaseModel):
    verdict: Literal["true", "false", "cannot_verify"]
    reason: str = Field(min_length=1)

    @field_validator("verdict", mode="before")
    @classmethod
    def normalise_verdict(cls, v):
        if isinstance(v, str):
            return v.strip().lower()
        return v


samples = [
    '{"verdict": "false", "reason": "No record of this."}',     # valid
    '{"verdict": "False", "reason": "No record of this."}',     # wrong case
    '{"verdict": "unverifiable", "reason": "Too recent."}',     # invented label
    '{"verdict": "true"}',                                      # missing field
    '{"verdict": "true", "reason": ""}',                        # empty reason
    '```json\n{"verdict": "true", "reason": "ok"}\n```',        # code fences
    '{"verdict": " FALSE ", "reason": "No record of this."}',   # case + spaces
]

for s in samples:
    try:
        v = Verdict.model_validate_json(s)
        print("OK    ", v)
    except ValidationError as e:
        print("REJECT", e.errors()[0]["msg"])


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

raw = response.choices[0].message.content
result = Verdict.model_validate_json(raw)
print(result.verdict)
print(result.reason)