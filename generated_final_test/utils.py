"""Utility functions for BMAD PocketFlow runtime."""

import os

from openai import OpenAI

# Initialize OpenAI client with API key from environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_llm(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    """Call LLM with the given prompt.

    Args:
        prompt: The prompt to send to the LLM
        model: OpenAI model to use

    Returns:
        The LLM response text

    Raises:
        Exception: If API call fails or API key is missing
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is required")

    try:
        response = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}], temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"LLM API call failed: {e}")
