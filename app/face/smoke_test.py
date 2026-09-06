from __future__ import annotations

import argparse
from pathlib import Path

from .service import FaceService


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a live InsightFace model smoke test")
    parser.add_argument("image", type=Path, help="Path to a local image containing exactly one face")
    args = parser.parse_args()
    embedding = FaceService().embed_image(args.image.read_bytes())
    print(f"InsightFace OK: embedding_dimensions={embedding.vector.size}, detection_score={embedding.det_score:.3f}")


if __name__ == "__main__":
    main()
