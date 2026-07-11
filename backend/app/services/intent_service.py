"""
Intent Detection Service

Version 1
Rule-based with confidence.

Future:
SentenceTransformer
Fine-tuned classifier
"""

from dataclasses import dataclass
from typing import List
import re


@dataclass
class IntentResult:
    intent: str
    confidence: float
    matched_keywords: List[str]


INTENTS = {

    "greeting": [
        "hello",
        "hi",
        "hey",
        "good morning",
        "good evening",
        "vanakkam",
        "namaste"
    ],

    "refund": [
        "refund",
        "money back",
        "return",
        "cancel order",
        "cancel my order"
    ],

    "order_status": [
        "order",
        "tracking",
        "track",
        "shipment",
        "where is my order",
        "delivery"
    ],

    "complaint": [
        "complaint",
        "issue",
        "problem",
        "bad",
        "worst",
        "late",
        "angry"
    ],

    "billing": [
        "invoice",
        "bill",
        "payment",
        "charged",
        "amount"
    ],

    "support": [
        "help",
        "support",
        "assist",
        "unable",
        "not working"
    ],

    "feedback": [
        "feedback",
        "review",
        "rating",
        "experience"
    ]
}


def detect_intent(text: str) -> IntentResult:

    text = text.lower()

    best_intent = "general"

    best_score = 0

    matched = []

    for intent, keywords in INTENTS.items():

        score = 0

        current = []

        for keyword in keywords:

            if keyword in text:

                score += 1

                current.append(keyword)

        if score > best_score:

            best_score = score

            best_intent = intent

            matched = current

    confidence = min(1.0, 0.4 + best_score * 0.2)

    return IntentResult(

        intent=best_intent,

        confidence=confidence,

        matched_keywords=matched

    )