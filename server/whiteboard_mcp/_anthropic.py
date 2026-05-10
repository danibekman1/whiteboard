"""Shared Anthropic client construction.

Both evaluators (algo and SD) call get_anthropic_client; centralizing the
helper means a single place to add timeout policy, retry logic, or org-key
selection."""
from __future__ import annotations
import os

import anthropic


def get_anthropic_client() -> anthropic.Anthropic:
    """Construct an Anthropic client. Fail fast at construction rather than
    producing a confusing 401 from Anthropic at request time."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)
