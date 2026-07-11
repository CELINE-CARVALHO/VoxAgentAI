"""
language_service.py

Production-ready language detection service for VoxAgent AI.

Responsibilities:
- Detect English, Hindi and Tamil
- Return confidence score
- Provide a clean API for future Whisper integration
- Detect script information
- Be extendable for code-mixed conversations
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import re

from lingua import Language, LanguageDetectorBuilder


# ---------------------------------------------------
# Supported Languages
# ---------------------------------------------------

SUPPORTED_LANGUAGES = [
    Language.ENGLISH,
    Language.HINDI,
    Language.TAMIL,
]


_detector = LanguageDetectorBuilder.from_languages(
    *SUPPORTED_LANGUAGES
).build()


# ---------------------------------------------------
# Models
# ---------------------------------------------------

class ScriptType(str, Enum):
    LATIN = "latin"
    DEVANAGARI = "devanagari"
    TAMIL = "tamil"
    UNKNOWN = "unknown"


@dataclass
class LanguageResult:
    language: str
    confidence: float
    source: str
    script: ScriptType
    code_mixed: bool = False


# ---------------------------------------------------
# Script Detection
# ---------------------------------------------------

DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")
TAMIL_PATTERN = re.compile(r"[\u0B80-\u0BFF]")
LATIN_PATTERN = re.compile(r"[A-Za-z]")


def detect_script(text: str) -> ScriptType:

    if TAMIL_PATTERN.search(text):
        return ScriptType.TAMIL

    if DEVANAGARI_PATTERN.search(text):
        return ScriptType.DEVANAGARI

    if LATIN_PATTERN.search(text):
        return ScriptType.LATIN

    return ScriptType.UNKNOWN


# ---------------------------------------------------
# Code Mix Detection
# ---------------------------------------------------

def is_code_mixed(text: str) -> bool:
    """
    Very lightweight heuristic.

    Future versions will replace this using
    FastText + Whisper metadata.
    """

    has_latin = bool(LATIN_PATTERN.search(text))
    has_tamil = bool(TAMIL_PATTERN.search(text))
    has_devanagari = bool(DEVANAGARI_PATTERN.search(text))

    count = sum([has_latin, has_tamil, has_devanagari])

    return count > 1


# ---------------------------------------------------
# Language Detection
# ---------------------------------------------------

def detect_language(text: str) -> LanguageResult:
    """
    Detect language from text.
    """

    if not text or not text.strip():
        return LanguageResult(
            language="unknown",
            confidence=0.0,
            source="none",
            script=ScriptType.UNKNOWN,
        )

    script = detect_script(text)

    confidence_values = _detector.compute_language_confidence_values(text)

    if not confidence_values:

        return LanguageResult(
            language="unknown",
            confidence=0.0,
            source="lingua",
            script=script,
            code_mixed=is_code_mixed(text),
        )

    best = confidence_values[0]

    mapping = {
        Language.ENGLISH: "en",
        Language.HINDI: "hi",
        Language.TAMIL: "ta",
    }

    return LanguageResult(
        language=mapping.get(best.language, "unknown"),
        confidence=round(best.value, 4),
        source="lingua",
        script=script,
        code_mixed=is_code_mixed(text),
    )


# ---------------------------------------------------
# Convenience
# ---------------------------------------------------

def language_name(code: str) -> str:

    return {
        "en": "English",
        "hi": "Hindi",
        "ta": "Tamil",
    }.get(code, "Unknown")


# ---------------------------------------------------
# Quick Test
# ---------------------------------------------------

if __name__ == "__main__":

    tests = [
        "Hello, how are you?",
        "வணக்கம் எப்படி இருக்கீங்க?",
        "नमस्ते आप कैसे हैं",
        "Hello வணக்கம்",
    ]

    for t in tests:
        print(detect_language(t))