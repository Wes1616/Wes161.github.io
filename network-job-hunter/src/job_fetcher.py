"""Orchestration de la récupération des offres : agrégation multi-sources,
filtre strict sur la fraîcheur (7 jours) et le domaine réseau, dédoublonnage."""
from __future__ import annotations

from datetime import date, timedelta

from config import settings
from src.job_sources.base import JobSource
from src.models import JobOffer
from src.tracker import Tracker


class JobFetcher:
    def __init__(
        self,
        sources: list[JobSource],
        tracker: Tracker | None = None,
        domain_keywords: list[str] | None = None,
        posted_within_days: int = settings.POSTED_WITHIN_DAYS,
    ) -> None:
        self.sources = sources
        self.tracker = tracker
        self.domain_keywords = [k.lower() for k in (domain_keywords or settings.DOMAIN_KEYWORDS)]
        self.posted_within_days = posted_within_days

    def fetch_new_offers(
        self, keywords: list[str] | None = None
    ) -> list[JobOffer]:
        """Retourne les offres fraîches (<= posted_within_days), pertinentes
        pour le domaine réseau, non déjà connues du tracker, sans doublon."""
        keywords = keywords or settings.DEFAULT_SEARCH_KEYWORDS
        seen_ids: set[str] = set()
        offers: list[JobOffer] = []

        for source in self.sources:
            for offer in source.fetch(keywords, self.posted_within_days):
                if offer.job_id in seen_ids:
                    continue
                if not self._is_fresh(offer):
                    continue
                if not self._is_network_domain(offer):
                    continue
                if self.tracker is not None and self.tracker.is_known(offer.job_id):
                    continue
                seen_ids.add(offer.job_id)
                offers.append(offer)

        return offers

    def _is_fresh(self, offer: JobOffer) -> bool:
        cutoff = date.today() - timedelta(days=self.posted_within_days)
        return offer.date_posted >= cutoff

    def _is_network_domain(self, offer: JobOffer) -> bool:
        haystack = f"{offer.title} {offer.description}".lower()
        return any(keyword in haystack for keyword in self.domain_keywords)
