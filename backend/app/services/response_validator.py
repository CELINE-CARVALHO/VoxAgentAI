
"""
response_validator.py

Validates and normalizes AI responses before they are returned
to the frontend.

This prevents malformed JSON, missing fields, and invalid values
from breaking the application.
"""

from typing import Any, Dict


DEFAULT_RESPONSE = {
    "language": "en",
    "intent": "general",
    "intent_confidence": 0.0,
    "sentiment": "neutral",
    "emotion": "neutral",
    "response": "I'm sorry, I couldn't process your request.",
    "should_escalate": False,
    "next_action": "none",
    "entities": {}
}


VALID_LANGUAGES = {
    "en",
    "ta",
    "hi"
}

VALID_SENTIMENTS = {
    "positive",
    "neutral",
    "negative"
}

VALID_EMOTIONS = {
    "happy",
    "neutral",
    "frustrated",
    "angry",
    "sad",
    "confused"
}


def validate_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize an AI response.
    """

    if not isinstance(data, dict):
        return DEFAULT_RESPONSE.copy()

    result = DEFAULT_RESPONSE.copy()

    result.update(data)

    # -------------------------
    # language
    # -------------------------

    if result["language"] not in VALID_LANGUAGES:
        result["language"] = "en"

    # -------------------------
    # sentiment
    # -------------------------

    if result["sentiment"] not in VALID_SENTIMENTS:
        result["sentiment"] = "neutral"

    # -------------------------
    # emotion
    # -------------------------

    if result["emotion"] not in VALID_EMOTIONS:
        result["emotion"] = "neutral"

    # -------------------------
    # confidence
    # -------------------------

    try:
        result["intent_confidence"] = float(
            result["intent_confidence"]
        )
    except Exception:
        result["intent_confidence"] = 0.0

    result["intent_confidence"] = max(
        0.0,
        min(
            1.0,
            result["intent_confidence"]
        )
    )

    # -------------------------
    # response
    # -------------------------

    if not isinstance(result["response"], str):

        result["response"] = DEFAULT_RESPONSE["response"]

    if len(result["response"].strip()) == 0:

        result["response"] = DEFAULT_RESPONSE["response"]

    # -------------------------
    # next_action
    # -------------------------

    if not isinstance(result["next_action"], str):

        result["next_action"] = "none"

    # -------------------------
    # entities
    # -------------------------

    if not isinstance(result["entities"], dict):

        result["entities"] = {}

    # -------------------------
    # escalation
    # -------------------------

    result["should_escalate"] = bool(
        result["should_escalate"]
    )

    return result
