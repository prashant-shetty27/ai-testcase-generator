import os
import base64
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional

load_dotenv()

_client = None

ALLOWED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
        _client = OpenAI(api_key=api_key)
    return _client


def _encode_image_to_base64(image_path: str) -> tuple[str, str]:
    """Returns (base64_data, media_type)."""
    path = Path(image_path)
    suffix = path.suffix.lower()
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = media_type_map.get(suffix, "image/png")
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, media_type


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
    # Allow scaling output size via env; keep safe defaults.
    max_tokens_env = os.getenv("AI_MAX_TOKENS", "7000")
    try:
        max_tokens = int(max_tokens_env)
    except ValueError:
        max_tokens = 7000
    max_tokens = max(1000, min(max_tokens, 12000))

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


def ask_ai_with_image(image_path: str, prompt: str, expect_json: bool = True) -> str:
    """
    Vision-capable AI call using GPT-4o.
    Accepts a local image file path + a text prompt.
    Returns the model response as a string.
    """
    suffix = Path(image_path).suffix.lower()
    if suffix not in ALLOWED_IMAGE_TYPES:
        raise ValueError(f"Unsupported image type: {suffix}. Allowed: {ALLOWED_IMAGE_TYPES}")

    b64_data, media_type = _encode_image_to_base64(image_path)
    data_url = f"data:{media_type};base64,{b64_data}"

    max_tokens_env = os.getenv("AI_MAX_TOKENS", "7000")
    try:
        max_tokens = int(max_tokens_env)
    except ValueError:
        max_tokens = 7000
    max_tokens = max(1000, min(max_tokens, 12000))

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior QA architect with 12+ years of experience. "
                    "You specialize in analysing UI screenshots, mockups, and design files "
                    "to produce structured, production-level test cases."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "high"}
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]

        kwargs = {
            "model": "gpt-4o",
            "max_tokens": max_tokens,
            "messages": messages,
        }
        # json_object response_format is not supported on vision calls in all regions;
        # rely on prompt-level instruction + post-parse instead.
        if expect_json:
            kwargs["response_format"] = {"type": "json_object"}

        response = _get_client().chat.completions.create(**kwargs)
        return response.choices[0].message.content

    except Exception as e:
        print("AI VISION SERVICE ERROR:", str(e))
        raise RuntimeError(f"Image-based AI generation failed: {e}")
