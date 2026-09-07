from __future__ import annotations

from abc import ABC, abstractmethod

from .models import DiscoveryQuery, Platform, SocialPost


class SocialContentProvider(ABC):
    """Platform-facing interface. Everything downstream is platform-agnostic."""

    platform: Platform

    @abstractmethod
    def discover(self, query: DiscoveryQuery) -> list[SocialPost]:
        raise NotImplementedError
