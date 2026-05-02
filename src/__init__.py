# SAR Processing System - Source Code Package
"""
Financial Services Agentic AI Project
Suspicious Activity Report (SAR) Processing System

This package contains the core modules for building an AI-powered
SAR processing system for financial crime detection.
"""

__version__ = "1.0.0"
__author__ = "Udacity Student"

import os


def create_openai_client():
    """
    Create an OpenAI client for the Chat Completions API.

    - By default uses the official OpenAI endpoint (no ``base_url`` → ``https://api.openai.com/v1``).
    - Set ``OPENAI_BASE_URL`` in the environment to override (e.g. Udacity Vocareum proxy).

    Returns:
        openai.OpenAI: Configured client instance

    Raises:
        ValueError: If ``OPENAI_API_KEY`` is not set
        ImportError: If the ``openai`` package is not installed
    """
    try:
        import openai
    except ImportError as exc:
        raise ImportError("openai package is required. Install with: pip install openai") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is not set. "
            "Add it to your .env (OpenAI: https://platform.openai.com/api-keys )."
        )

    base_url = (os.getenv("OPENAI_BASE_URL") or "").strip()
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    client = openai.OpenAI(**kwargs)
    resolved = base_url if base_url else "https://api.openai.com/v1 (OpenAI default)"
    print("✅ OpenAI client initialized")
    print(f"🔑 API key: {api_key[:8]}...{api_key[-4:]}")
    print(f"📍 Base URL: {resolved}")
    return client


def create_vocareum_openai_client():
    """
    Legacy helper: forces Udacity Vocareum routing.

    Prefer ``create_openai_client()`` with ``OPENAI_BASE_URL=https://openai.vocareum.com/v1`` instead.
    """
    try:
        import openai
    except ImportError as exc:
        raise ImportError("openai package is required. Install with: pip install openai") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is not found. "
            "Get your Vocareum OpenAI API key from 'Cloud Resources' in your Udacity workspace."
        )

    client = openai.OpenAI(
        base_url="https://openai.vocareum.com/v1",
        api_key=api_key,
    )
    print("✅ OpenAI client initialized (Vocareum routing)")
    print(f"🔑 API key: {api_key[:8]}...{api_key[-4:]}")
    print("📍 Base URL: https://openai.vocareum.com/v1")
    return client
