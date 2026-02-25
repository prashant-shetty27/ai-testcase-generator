import os
from dotenv import load_dotenv
from openai import OpenAI

# load environment variables
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def ask_ai(prompt: str):
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You are a senior QA architect."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content