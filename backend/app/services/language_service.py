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
# Romanized Tamil / Hindi keyword sets
# ---------------------------------------------------
# When users type Tamil or Hindi in Latin script (Tanglish / Hinglish),
# the lingua detector sees only Latin characters and classifies the
# text as English. These keyword sets act as a fast pre-check that
# runs BEFORE lingua so romanized input is routed correctly.

_TAMIL_ROMANIZED = {
    # pronouns / question words
    "ithu", "itha", "avan", "aval", "avanga", "naan", "nee", "naanga",
    "enna", "epdi", "eppadi", "yean", "aen", "yenna", "ethu", "enga",
    "evlo", "evvalo", "engae", "eppo", "eppothu",
    # common verbs / auxiliaries
    "irukku", "irukkaan", "irukkaen", "kaattukirathu", "kaattu",
    "sollu", "solla", "pannunga", "pannrom", "vandha", "vanthu",
    "paarkal", "paartha", "paaru", "paar", "teriyum", "teriyaadhu",
    "mudiyum", "mudiyaadhu", "vendam", "vendum", "kudukka", "kuduppa",
    "kelunga", "kelu", "pesuvom", "pesalaam",
    # common nouns / adjectives
    "mattum", "mattumae", "konjam", "romba", "semma", "nalla", "kettadhu",
    "ungaluku", "ungal", "enakku", "namaskaaram", "vanakkam", "sari",
    "illai", "aamaa", "aamaama", "theriyum", "therinja",
    # numbers / units
    "onnu", "rendu", "moonu", "naalu", "aanju",
}

_HINDI_ROMANIZED = {
    # pronouns / question words
    "mujhe", "humko", "hume", "aapko", "aapka", "tumko", "tumhara",
    "kyun", "kya", "kaise", "kahan", "kab", "kaun",
    # common verbs / auxiliaries
    "chahiye", "batao", "bataiye", "samjho", "karo", "karein",
    "hoga", "hain", "tha", "thi", "the", "nahi", "nahin", "mat",
    "milega", "milta", "milti", "sakte", "sakti",
    # common nouns / phrases
    "abhi", "zaroor", "bilkul", "theek", "shukriya", "dhanyavaad",
    "namaste", "bhai", "behen", "accha", "acha", "yahan", "wahan",
    "lekin", "aur", "phir", "toh",
}


def _count_romanized_hits(words: list, keyword_set: set) -> int:
    return sum(1 for w in words if w in keyword_set)


def _check_romanized(text: str) -> Optional[str]:
    """
    Returns 'ta', 'hi', or None.
    Requires at least 2 keyword hits OR 1 hit in a short message (<=5 words).
    """
    words = re.findall(r"[a-z]+", text.lower())
    threshold = 1 if len(words) <= 5 else 2

    if _count_romanized_hits(words, _TAMIL_ROMANIZED) >= threshold:
        return "ta"

    if _count_romanized_hits(words, _HINDI_ROMANIZED) >= threshold:
        return "hi"

    return None


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

    Detection order:
      1. Unicode script check (instant — covers native Tamil/Hindi script).
      2. Romanized keyword pre-check (covers Tanglish / Hinglish in Latin).
      3. Lingua ML detector (fallback for everything else).
    """

    if not text or not text.strip():
        return LanguageResult(
            language="unknown",
            confidence=0.0,
            source="none",
            script=ScriptType.UNKNOWN,
        )

    script = detect_script(text)

    # ----------------------------------------------------------------
    # Step 1: Native Unicode script → trust it immediately
    # ----------------------------------------------------------------
    if script == ScriptType.TAMIL:
        return LanguageResult(
            language="ta",
            confidence=1.0,
            source="script",
            script=script,
            code_mixed=is_code_mixed(text),
        )

    if script == ScriptType.DEVANAGARI:
        return LanguageResult(
            language="hi",
            confidence=1.0,
            source="script",
            script=script,
            code_mixed=is_code_mixed(text),
        )

    # ----------------------------------------------------------------
    # Step 2: Romanized Tamil/Hindi (Tanglish / Hinglish)
    # ----------------------------------------------------------------
    romanized_lang = _check_romanized(text)
    if romanized_lang:
        return LanguageResult(
            language=romanized_lang,
            confidence=0.85,
            source="romanized_keywords",
            script=ScriptType.LATIN,
            code_mixed=False,
        )

    # ----------------------------------------------------------------
    # Step 3: Lingua ML detector
    # ----------------------------------------------------------------
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