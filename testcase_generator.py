import os
import json
from urllib import response
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_testcases(analysis_json):

    prompt = f"""
You are a Principal QA Automation Architect.

Using the analyzed requirement below, generate structured test cases.

Return ONLY valid JSON.

Structure:

{{
 "positive_tests": [],
 "negative_tests": [],
 "edge_cases": [],
 "boundary_value_tests": [],
 "api_tests": [],
 "network_tests": [],
 "automation_candidates": []
}}

Each test case format:

{{
 "testcase_id": "",
 "scenario": "",
 "steps": [],
 "expected_result": ""
}}

Analyzed Requirement:
{json.dumps(analysis_json, indent=2)}
"""

    response = client.chat.completions.create(
    model="gpt-4.1",
    response_format={"type": "json_object"},
    messages=[{"role": "user", "content": prompt}]
)

    content = response.choices[0].message.content
    print("AI RAW RESPONSE:")
    print(content)    
    try:
        return json.loads(content)
    except Exception as e:
        print("JSON PARSE FAILED")
    print(content)
    return {
        "error": "AI did not return valid JSON",
        "raw_response": content
    }