"""Source interface. Each source knows how to find real-estate firms in an
area and return them as Firm objects. Sources should fail soft: a missing API
key or a network error logs a warning and yields nothing rather than crashing
the whole run."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Firm


class Source(ABC):
    name: str = "base"

    @abstractmethod
    def available(self) -> bool:
        """True if this source is configured and usable (e.g. key present)."""

    @abstractmethod
    def search(self, area: str) -> list[Firm]:
        """Return firms found for a single area string like 'Harrisburg PA'."""
