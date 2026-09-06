from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class FaceEmbedding:
    vector: np.ndarray
    bbox: tuple[float, float, float, float]
    det_score: float


class FaceService:
    def __init__(self):
        # CPU-first local inference for reproducibility and privacy.
        from insightface.app import FaceAnalysis

        self.app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        self.app.prepare(ctx_id=0, det_size=(640, 640))

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
        embedding = face.normed_embedding.astype(np.float32)
        return FaceEmbedding(
            vector=embedding,
            bbox=tuple(float(x) for x in face.bbox),
            det_score=float(face.det_score),
        )

    def embeddings_in_image(self, image_bytes: bytes) -> list[np.ndarray]:
        array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Candidate is not a decodable image")
        faces = self.app.get(image)
        return [face.normed_embedding.astype(np.float32) for face in faces]

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)
