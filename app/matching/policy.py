from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchDecision:
    verified: bool
    reason: str


def decide(face_similarity: float, face_threshold: float) -> MatchDecision:
    """Face correspondence is the acceptance gate.

    Image similarity is deliberately NOT a hard gate because a user selfie and a
    social post can depict the same person under different framing/backgrounds.
    """
    if face_similarity < face_threshold:
        return MatchDecision(False, "FACE_MATCH_LOW")
    return MatchDecision(True, "VERIFIED_MATCH")
