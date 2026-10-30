import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()                                        # reads .env into environment variables
client = Groq(api_key=os.environ["GROQ_API_KEY"])    # one client, reused for every call

claim = "Microsoft laid off 60,000 employees last week through a VEO."

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {"role": "user", "content": f"Is this news claim true? {claim}"},
    ],
)

print(response.choices[0].message.content)