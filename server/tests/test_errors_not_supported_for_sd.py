"""Test for the not_supported_for_sd error helper.

Used by get_hint when called on an SD session - SD coaching is driven by
pushbacks and Socratic phase advancement, not graded hints. The helper takes
a tool_name so future tools (e.g. evaluate_attempt rejecting SD) can also use it."""
from __future__ import annotations
import json

from whiteboard_mcp.errors import not_supported_for_sd


def test_not_supported_for_sd_shape():
    err = not_supported_for_sd(tool="get_hint")
    assert err == {
        "error": "not_supported_for_sd",
        "tool": "get_hint",
        "message": "get_hint is not supported for system_design sessions",
    }


def test_not_supported_for_sd_serializable():
    json.dumps(not_supported_for_sd(tool="get_hint"))
