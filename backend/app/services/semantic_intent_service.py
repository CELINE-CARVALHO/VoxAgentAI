"""
Semantic Intent Detection using Sentence Transformers.
"""

from dataclasses import dataclass
from sentence_transformers import SentenceTransformer, util
import torch

model = SentenceTransformer("all-MiniLM-L6-v2")


@dataclass
class IntentResult:
    intent: str
    confidence: float
    matched_example: str


INTENT_EXAMPLES = {
    "greeting": [
        "hello",
        "good morning",
        "hi there",
        "namaste",
        "vanakkam",
    ],

    "refund": [
        "refund my payment",
        "I want my money back",
        "cancel and refund",
        "return this order",
    ],

    "order_status": [
        "where is my order",
        "track my shipment",
        "parcel not delivered",
        "delivery status",
    ],

    "billing": [
        "payment failed",
        "invoice issue",
        "charged twice",
        "billing problem",
    ],

    "complaint": [
        "worst service",
        "I want to complain",
        "very disappointed",
        "bad experience",
    ],

    "support": [
        "I need help",
        "technical support",
        "cannot login",
        "assist me",
    ],

    "feedback": [
        "I have feedback",
        "I'd like to review",
        "rate my experience",
    ]
}


EXAMPLE_EMBEDDINGS = {}

for intent, examples in INTENT_EXAMPLES.items():
    EXAMPLE_EMBEDDINGS[intent] = model.encode(
        examples,
        convert_to_tensor=True
    )


def detect_intent(text: str) -> IntentResult:

    text_embedding = model.encode(
        text,
        convert_to_tensor=True
    )

    best_intent = "general"

    best_score = -1

    matched = ""

    for intent, embeddings in EXAMPLE_EMBEDDINGS.items():

        similarities = util.cos_sim(
            text_embedding,
            embeddings
        )

        score = float(torch.max(similarities))

        if score > best_score:

            best_score = score

            index = int(torch.argmax(similarities))

            matched = INTENT_EXAMPLES[intent][index]

            best_intent = intent

    return IntentResult(

        intent=best_intent,

        confidence=round(best_score, 3),

        matched_example=matched

    )