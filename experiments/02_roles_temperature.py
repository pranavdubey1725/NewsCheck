import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()                                        # reads .env into environment variables
client = Groq(api_key=os.environ["GROQ_API_KEY"])    # one client, reused for every call

claim = "Microsoft laid off 60,000 employees last week through a VEO."

SYSTEM_PROMPT = (
    "You are a careful news analyst. Your training data has a cutoff date and "
    "you cannot see recent news. If a claim could be about events after your "
    "cutoff, say you cannot verify it. Never call a claim false just because "
    "you have no information about it."
)

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    temperature=0,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Is this news claim true? {claim}"},
    ],
)

print(response.choices[0].message.content)
print(response.usage)