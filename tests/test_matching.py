import numpy as np

from app.face.service import FaceService
from app.matching.policy import decide


def test_cosine_similarity_for_unit_vectors():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([1.0, 0.0], dtype=np.float32)
    assert FaceService.cosine_similarity(a, b) == 1.0


def test_face_similarity_is_acceptance_gate():
    assert decide(0.80, 0.75).verified
    assert not decide(0.60, 0.75).verified
