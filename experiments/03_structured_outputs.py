import os
from dotenv import load_dotenv
from groq import Groq
import groq
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
client = Groq(api_key=os.environ["GROQ_API_KEY"], max_retries=2)  # SDK retries 429/5xx/network itself

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

MAX_ATTEMPTS = 3

def is_json_validate_failed(err: groq.BadRequestError) -> bool:
    body = err.body if isinstance(err.body, dict) else {}
    detail = body.get("error", body)
    return isinstance(detail, dict) and detail.get("code") == "json_validate_failed"


def check_claim(claim: str) -> Verdict:
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
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
            return Verdict.model_validate_json(response.choices[0].message.content)  #we put return because as soon as validate suceeds we get out as we have a valid result now no need to retry

        except groq.BadRequestError as e:
            if not is_json_validate_failed(e):
                raise                # a 400 that's OUR fault (bad schema, bad request): never retry
            last_error = e
        except ValidationError as e:
            last_error = e           # model output passed Groq but failed our checks

        print(f"Attempt {attempt}/{MAX_ATTEMPTS} failed: {type(last_error).__name__}")

    raise RuntimeError(f"No valid verdict after {MAX_ATTEMPTS} attempts") from last_error


result = check_claim(claim)
print(result.verdict)
print(result.reason)