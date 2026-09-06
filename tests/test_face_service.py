from dataclasses import dataclass

import cv2
import numpy as np
import pytest

from app.face.service import FaceService


@dataclass
class FakeFace:
    normed_embedding: np.ndarray
    bbox: tuple[float, float, float, float] = (10.0, 10.0, 110.0, 110.0)
    det_score: float = 0.99


class FakeAnalysis:
    def __init__(self, faces):
        self.faces = faces

    def get(self, image):
        return self.faces


def image_bytes() -> bytes:
    ok, encoded = cv2.imencode(".png", np.zeros((128, 128, 3), dtype=np.uint8))
    assert ok
    return encoded.tobytes()


def test_embedding_is_normalized_and_candidate_quality_is_filtered():
    faces = [
        FakeFace(np.array([3.0, 4.0], dtype=np.float32)),
        FakeFace(np.array([1.0, 0.0], dtype=np.float32), bbox=(1.0, 1.0, 10.0, 10.0)),
    ]
    service = FaceService(app=FakeAnalysis([faces[0]]), min_face_size=20)
    embedding = service.embed_image(image_bytes())
    service.app = FakeAnalysis(faces)
    candidates = service.embeddings_in_image(image_bytes())

    np.testing.assert_allclose(embedding.vector, np.array([0.6, 0.8], dtype=np.float32))
    assert len(candidates) == 1
    np.testing.assert_allclose(candidates[0], np.array([0.6, 0.8], dtype=np.float32))


def test_input_face_count_and_quality_are_rejected():
    with pytest.raises(ValueError, match="MULTIPLE_FACES"):
        FaceService(app=FakeAnalysis([FakeFace(np.ones(2)), FakeFace(np.ones(2))])).embed_image(
            image_bytes()
        )

    low_quality = FakeFace(np.ones(2), det_score=0.1)
    with pytest.raises(ValueError, match="FACE_QUALITY_TOO_LOW"):
        FaceService(app=FakeAnalysis([low_quality])).embed_image(image_bytes())


def test_cosine_similarity_is_deterministic_for_invalid_inputs():
    assert FaceService.cosine_similarity(np.array([1.0, 0.0]), np.array([1.0])) == 0.0
    assert FaceService.cosine_similarity(np.zeros(2), np.ones(2)) == 0.0
    assert FaceService.cosine_similarity(np.array([1.0, 0.0]), np.array([1.0, 0.0])) == 1.0


def test_configuration_validation():
    with pytest.raises(ValueError, match="MIN_DETECTION_SCORE_OUT_OF_RANGE"):
        FaceService(app=FakeAnalysis([]), min_detection_score=1.1)
    with pytest.raises(ValueError, match="MIN_FACE_SIZE_INVALID"):
        FaceService(app=FakeAnalysis([]), min_face_size=0)
