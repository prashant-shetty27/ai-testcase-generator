import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_requirement(requirement: str):
    prompt = f"""
You are a senior QA architect.

Analyze the requirement and extract structured system understanding.

Return ONLY valid JSON.

Format:
{{
  "feature": "",
  "actors": [],
  "inputs": [],
  "constraints": [],
  "business_rules": [],
  "possible_apis": []
}}

Requirement:
{requirement}
"""

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content

    return json.loads(content)