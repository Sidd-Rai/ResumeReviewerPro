import streamlit as st
from google import genai
from google.genai import types

from src.config.settings import GEMINI_API_KEY


@st.cache_resource(show_spinner=False)
def get_gemini_client() -> genai.Client:
    """Return a single Gemini client for the Streamlit process."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY variable is missing or unconfigured in your environment.")

    return genai.Client(api_key=GEMINI_API_KEY)


@st.cache_resource(show_spinner=False)
def get_prompt_cache_name(model: str, display_name: str, system_instruction: str, ttl: str = "86400s") -> str | None:
    """Create a reusable Gemini cached-content resource for static prompt context."""
    try:
        client = get_gemini_client()
        cached_content = client.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(
                displayName=display_name,
                ttl=ttl,
                systemInstruction=system_instruction,
            ),
        )
        return cached_content.name
    except Exception:
        # Fall back to uncached prompts if cached content is unavailable.
        return None
