"""Orchestration de la récupération des offres : agrégation multi-sources,
filtre strict sur la fraîcheur (7 jours) et le domaine réseau, dédoublonnage."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from config import settings
from src.job_sources.base import JobSource
from src.models import JobOffer
from src.tracker import Tracker

log = logging.getLogger(__name__)


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

        # --- Étape 0 : récupération brute, UNE requête par mot-clé ---------
        # Une requête combinant tous les mots-clés en une chaîne séparée par
        # virgules (motsCles="a,b,c") est traitée par l'API France Travail
        # comme un ET logique, pas un OU — d'où des recherches trop
        # restrictives (souvent 0 résultat). On interroge donc chaque source
        # une fois par mot-clé, puis on fusionne les résultats (dédoublonnés
        # par job_id ci-dessous).
        raw_offers: list[JobOffer] = []
        for source in self.sources:
            for keyword in keywords:
                keyword_offers = source.fetch([keyword], self.posted_within_days)
                log.info(
                    "[DEBUG][JobFetcher] source=%s mot-clé=%r -> %d offre(s) brute(s)",
                    source.name,
                    keyword,
                    len(keyword_offers),
                )
                raw_offers.extend(keyword_offers)

        seen_ids: set[str] = set()
        deduped_raw: list[JobOffer] = []
        for offer in raw_offers:
            if offer.job_id not in seen_ids:
                seen_ids.add(offer.job_id)
                deduped_raw.append(offer)
        # TODO(debug temporaire) : nombre brut d'offres avant tout filtre (1/3)
        log.info(
            "[DEBUG][JobFetcher] 1) %d offre(s) brute(s) au total "
            "(toutes sources et mots-clés confondus, doublons retirés)",
            len(deduped_raw),
        )

        # --- Étape 1 : fraîcheur (<= posted_within_days) -------------------
        fresh_offers = [o for o in deduped_raw if self._is_fresh(o)]
        log.info(
            "[DEBUG][JobFetcher] 1bis) %d offre(s) après filtre fraîcheur (<= %d jours)",
            len(fresh_offers),
            self.posted_within_days,
        )

        # --- Étape 2 : DOMAIN_KEYWORDS --------------------------------------
        # TODO(debug temporaire) : nombre après filtre DOMAIN_KEYWORDS (2/3)
        domain_offers = [o for o in fresh_offers if self._is_network_domain(o)]
        log.info(
            "[DEBUG][JobFetcher] 2) %d offre(s) après filtre DOMAIN_KEYWORDS",
            len(domain_offers),
        )

        # --- Étape 3 : dédoublonnage SQLite (job_id déjà vu) ----------------
        # TODO(debug temporaire) : nombre après dédoublonnage SQLite (3/3)
        if self.tracker is not None:
            new_offers = [o for o in domain_offers if not self.tracker.is_known(o.job_id)]
        else:
            new_offers = domain_offers
        log.info(
            "[DEBUG][JobFetcher] 3) %d offre(s) après dédoublonnage SQLite (job_id déjà connu du tracker)",
            len(new_offers),
        )

        return new_offers

    def _is_fresh(self, offer: JobOffer) -> bool:
        cutoff = date.today() - timedelta(days=self.posted_within_days)
        return offer.date_posted >= cutoff

    def _is_network_domain(self, offer: JobOffer) -> bool:
        haystack = f"{offer.title} {offer.description}".lower()
        return any(keyword in haystack for keyword in self.domain_keywords)
