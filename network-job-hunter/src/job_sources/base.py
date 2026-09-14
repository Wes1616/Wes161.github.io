"""Interface abstraite pour toute source d'offres d'emploi."""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.models import JobOffer


class JobSource(ABC):
    """Une source d'offres (API, RSS, scraping...) doit implémenter fetch()."""

    name: str = "unknown"

    @abstractmethod
    def fetch(self, keywords: list[str], max_days: int) -> list[JobOffer]:
        """Retourne les offres correspondant aux mots-clés, publiées il y a
        au plus `max_days` jours. L'implémentation doit appliquer le filtre
        de date côté source quand c'est possible (paramètre natif de l'API),
        le JobFetcher revérifie ensuite systématiquement côté client."""
        raise NotImplementedError
