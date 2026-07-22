from __future__ import annotations
from typing import TypedDict


class GroundTruthCase(TypedDict):
    claim: str
    expected_verdict: str   # "true" | "false" | "misleading" | "inconclusive"
    expected_stance: str    # "supports" | "contradicts" | "mixed" | "insufficient_evidence"
    difficulty: str         # "easy" | "medium" | "hard"
    notes: str


GROUND_TRUTH_CASES: list[GroundTruthCase] = [
    {
        "claim": "The Eiffel Tower was built in 1889.",
        "expected_verdict": "true",
        "expected_stance": "supports",
        "difficulty": "easy",
        "notes": "Simple historical fact. Wikipedia + multiple primary sources. Should hit fast on Google Fact Check.",
    },
    {
        "claim": "NASA confirmed water ice on the Moon in 2020.",
        "expected_verdict": "misleading",
        "expected_stance": "mixed",
        "difficulty": "easy",
        "notes": "NASA SOFIA telescope confirmed water molecules October 2020. Well-sourced across AP, BBC, NASA.gov.",
    },
    {
        "claim": "COVID-19 vaccines cause autism in children.",
        "expected_verdict": "false",
        "expected_stance": "contradicts",
        "difficulty": "easy",
        "notes": "WHO, CDC, peer-reviewed literature contradict. Snopes: False. Multiple ClaimReview entries exist.",
    },
    {
        "claim": "A cup of coffee per day reduces Alzheimer's risk by 65%.",
        "expected_verdict": "false",
        "expected_stance": "contradicts",
        "difficulty": "medium",
        "notes": "Observational studies exist (correlation) but do not establish causation. Specific '65%' figure is cherry-picked from one study. Classic misleading health stat.",
    },
    {
        "claim": "5G towers emit radiation that causes cancer in residential areas.",
        "expected_verdict": "false",
        "expected_stance": "contradicts",
        "difficulty": "medium",
        "notes": "WHO, IEEE, and ICNIRP guidelines state 5G radiation levels are far below harmful thresholds. Classic health misinformation pattern.",
    },
]
