from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import cv2
import numpy as np


@dataclass(frozen=True)
class FaceEmbedding:
    vector: np.ndarray
    bbox: tuple[float, float, float, float]
    det_score: float


class FaceService:
    def __init__(
        self,
        app: Any | None = None,
        *,
        model_name: str = "buffalo_l",
        detection_size: tuple[int, int] = (640, 640),
        min_detection_score: float = 0.5,
        min_face_size: int = 40,
    ) -> None:
        if min_detection_score < 0.0 or min_detection_score > 1.0:
            raise ValueError("MIN_DETECTION_SCORE_OUT_OF_RANGE")
        if min_face_size <= 0:
            raise ValueError("MIN_FACE_SIZE_INVALID")
        self.min_detection_score = min_detection_score
        self.min_face_size = min_face_size
        if app is not None:
            self.app = app
            return
        try:
            from insightface.app import FaceAnalysis  # type: ignore[import-untyped]

            # CPU-first local inference keeps biometric processing on the host.
            self.app = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
            self.app.prepare(ctx_id=0, det_size=detection_size)
        except Exception as exc:
            raise RuntimeError("INSIGHTFACE_INITIALIZATION_FAILED") from exc

    def embed_image(self, image_bytes: bytes) -> FaceEmbedding:
        array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Input is not a decodable image")
        faces = self.app.get(image)
        if not faces:
            raise ValueError("NO_FACE_FOUND")
        if len(faces) > 1:
            raise ValueError("MULTIPLE_FACES")
        face = faces[0]
        self._validate_quality(face)
        embedding = self._normalize_embedding(face.normed_embedding)
        return FaceEmbedding(
            vector=embedding,
            bbox=cast(tuple[float, float, float, float], tuple(float(x) for x in face.bbox)),
            det_score=float(face.det_score),
        )

    def embeddings_in_image(self, image_bytes: bytes) -> list[np.ndarray]:
        array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Candidate is not a decodable image")
        faces = self.app.get(image)
        embeddings: list[np.ndarray] = []
        for face in faces:
            if not self._passes_quality(face):
                continue
            try:
                embeddings.append(self._normalize_embedding(face.normed_embedding))
            except ValueError:
                continue
        return embeddings

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        first = np.asarray(a, dtype=np.float32).reshape(-1)
        second = np.asarray(b, dtype=np.float32).reshape(-1)
        if first.shape != second.shape or first.size == 0:
            return 0.0
        denom = float(np.linalg.norm(first) * np.linalg.norm(second))
        if denom == 0:
            return 0.0
        similarity = float(np.dot(first, second) / denom)
        return float(np.clip(similarity, -1.0, 1.0))

    def _passes_quality(self, face: Any) -> bool:
        try:
            score = float(face.det_score)
            bbox = tuple(float(value) for value in face.bbox)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
        except (AttributeError, IndexError, TypeError, ValueError):
            return False
        return score >= self.min_detection_score and min(width, height) >= self.min_face_size

    def _validate_quality(self, face: Any) -> None:
        if not self._passes_quality(face):
            raise ValueError("FACE_QUALITY_TOO_LOW")

    @staticmethod
    def _normalize_embedding(embedding: Any) -> np.ndarray:
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if vector.size == 0 or not np.all(np.isfinite(vector)):
            raise ValueError("INVALID_FACE_EMBEDDING")
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            raise ValueError("INVALID_FACE_EMBEDDING")
        return (vector / norm).astype(np.float32)
