from __future__ import annotations

from abc import ABC, abstractmethod

from .models import DiscoveryQuery, SocialPost


class SocialContentProvider(ABC):
    """Platform-facing interface. Everything downstream is platform-agnostic."""

    platform: str

    @abstractmethod
    def discover(self, query: DiscoveryQuery) -> list[SocialPost]:
        raise NotImplementedError
