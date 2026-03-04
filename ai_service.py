import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional

load_dotenv()

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
        _client = OpenAI(api_key=api_key)
    return _client


def ask_ai(
    prompt: str,
    strict_mode: bool = False,
    expect_json: bool = True
) -> str:
    """
    Central AI invocation layer.
    Supports:
    - Strict mode (lower temperature)
    - JSON enforcement
    - Error resilience
    """

    temperature = 0.3 if strict_mode else 0.6
    max_tokens = 3000

    try:
        response = _get_client().chat.completions.create(
            model="gpt-4.1",
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"} if expect_json else None,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior QA architect with strong "
                        "focus on structured, deterministic output."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        print("AI SERVICE ERROR:", str(e))
        raise RuntimeError("AI generation failed.")