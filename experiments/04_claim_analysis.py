from typing import Literal
from pydantic import BaseModel, Field
from newscheck.llm import call_structured

class Verdict(BaseModel):
    verdict: Literal["true", "false", "cannot_verify"]
    reason: str = Field(min_length=1)

result = call_structured(
    system="You are a careful news analyst. Reply using the provided JSON format.",
    user="Is this news claim true? Humans have five legs.",
    output_model=Verdict,
)
print(result)