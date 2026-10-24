"""Helpers for turning Reddit HTTP error responses into short, readable details."""

import html
import re

import httpx

_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_SENTENCE_END_RE = re.compile(r"[.!?](\s|$)")
_JSON_MESSAGE_KEYS = ("message", "reason", "explanation", "error_description", "error")


def describe_response(response: httpx.Response, *, limit: int = 200) -> str:
    """Return a short human-readable summary of an error response body.

    Reddit answers blocked requests with a large HTML page ("You've been
    blocked by network security...") and API errors with small JSON
    objects (``{"message": "Forbidden", "error": 403}``). This extracts the
    meaningful text from either, truncated to *limit* characters.
    """
    text = ""
    content_type = response.headers.get("content-type", "")

    if "json" in content_type:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            for key in _JSON_MESSAGE_KEYS:
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    text = value.strip()
                    break
    else:
        body = _SCRIPT_STYLE_RE.sub(" ", response.text)
        body = _TAG_RE.sub(" ", body)
        text = " ".join(html.unescape(body).split())
        # HTML error pages carry boilerplate after the headline; keep the first sentence.
        first_sentence = _SENTENCE_END_RE.search(text)
        if first_sentence:
            text = text[: first_sentence.end()].rstrip()

    # Callers embed the detail in their own sentence, e.g. "(HTTP 403: <detail>)."
    text = text.rstrip(" .")
    if len(text) > limit:
        text = text[:limit].rstrip() + "..."
    return text
