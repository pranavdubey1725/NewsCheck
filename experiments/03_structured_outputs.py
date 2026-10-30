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

#Strict JSON Schema
schema = Verdict.model_json_schema()
schema["additionalProperties"] = False   # strict mode requires this: no extra fields allowed
print(schema)  



samples = [
    '{"verdict": "false", "reason": "No record of this."}',     # valid
    '{"verdict": "False", "reason": "No record of this."}',     # wrong case
    '{"verdict": "unverifiable", "reason": "Too recent."}',     # invented label
    '{"verdict": "true"}',                                      # missing field
    '{"verdict": "true", "reason": ""}',                        # empty reason
    '```json\n{"verdict": "true", "reason": "ok"}\n```',        # code fences
    '{"verdict": " FALSE ", "reason": "No record of this."}',   # case + spaces
]


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
    " Reply using the provided JSON format."
)

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    temperature=0,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Is this news claim true? {claim}"},
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {"name": "verdict", "strict": True, "schema": schema},
    },
)

answer = response.choices[0].message.content

import json   # put this with the other imports at the top

raw = response.choices[0].message.content
print(repr(raw))          # repr shows the exact string, including hidden characters

raw = response.choices[0].message.content
result = Verdict.model_validate_json(raw)
print(result.verdict)
print(result.reason)