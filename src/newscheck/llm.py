import os
from typing import Type, TypeVar

import groq
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, ValidationError

load_dotenv()

MODEL = "openai/gpt-oss-20b"
MAX_ATTEMPTS = 3

_client = Groq(api_key=os.environ["GROQ_API_KEY"], max_retries=2)

T = TypeVar("T", bound=BaseModel)


def _is_json_validate_failed(err: groq.BadRequestError) -> bool:
    body = err.body if isinstance(err.body, dict) else {}
    detail = body.get("error", body)
    return isinstance(detail, dict) and detail.get("code") == "json_validate_failed"


def call_structured(system: str, user: str, output_model: Type[T]) -> T:
    """Call the model and return a validated instance of output_model."""
    schema = output_model.model_json_schema()
    schema["additionalProperties"] = False

    last_error = None
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = _client.chat.completions.create(
                model=MODEL,
                temperature=0,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": output_model.__name__, "strict": True, "schema": schema},
                },
            )
        except groq.BadRequestError as e:
            if not _is_json_validate_failed(e):
                raise
            last_error = e
            print(f"Attempt {attempt}/{MAX_ATTEMPTS} failed: {type(e).__name__}")
            continue

        content = response.choices[0].message.content
        try:
            return output_model.model_validate_json(content)
        except ValidationError as e:
            last_error = e
            print(f"Attempt {attempt}/{MAX_ATTEMPTS} failed: {e.errors()[0]['msg']}")
            messages = messages + [
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"Your answer broke a rule: {e.errors()[0]['msg']}. Answer again, following every rule."},
            ]

    raise RuntimeError(f"No valid output after {MAX_ATTEMPTS} attempts") from last_error