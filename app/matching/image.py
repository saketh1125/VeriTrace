from __future__ import annotations

from io import BytesIO

from PIL import Image
import imagehash


def perceptual_similarity(a: bytes, b: bytes) -> float:
    img_a = Image.open(BytesIO(a)).convert("RGB")
    img_b = Image.open(BytesIO(b)).convert("RGB")
    hash_a = imagehash.phash(img_a)
    hash_b = imagehash.phash(img_b)
    distance = hash_a - hash_b
    return max(0.0, 1.0 - distance / max(len(hash_a.hash.flatten()), 1))
