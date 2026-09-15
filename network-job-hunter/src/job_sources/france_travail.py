"""Adaptateur JobSource pour l'API officielle France Travail (ex Pôle Emploi).

Documentation : https://francetravail.io/produits-partenaires/catalogue/offres-emploi
Authentification : OAuth2 client_credentials (Client ID/Secret créés sur
francetravail.io). Nécessite les scopes "api_offresdemploiv2 o2dsoffre".
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime

import requests

from config import settings
from src.job_sources.base import JobSource
from src.models import JobOffer

log = logging.getLogger(__name__)


class FranceTravailSource(JobSource):
    name = "france_travail"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.client_id = client_id or settings.FRANCE_TRAVAIL_CLIENT_ID
        self.client_secret = client_secret or settings.FRANCE_TRAVAIL_CLIENT_SECRET
        self.session = session or requests.Session()
        self._token: str | None = None
        self._token_expiry: float = 0.0

    def _get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expiry:
            return self._token

        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "FRANCE_TRAVAIL_CLIENT_ID / FRANCE_TRAVAIL_CLIENT_SECRET manquants "
                "dans .env — voir https://francetravail.io pour créer une application."
            )

        response = self.session.post(
            settings.FRANCE_TRAVAIL_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": settings.FRANCE_TRAVAIL_SCOPE,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        self._token = payload["access_token"]
        # marge de sécurité de 30s avant expiration réelle
        self._token_expiry = time.monotonic() + payload.get("expires_in", 1200) - 30
        return self._token

    def fetch(self, keywords: list[str], max_days: int) -> list[JobOffer]:
        if len(keywords) > 1:
            # motsCles="a,b,c" est traité par l'API comme un ET logique, pas
            # un OU : ça restreint la recherche au lieu de l'élargir (voire
            # 0 résultat). L'appelant (JobFetcher) est censé appeler fetch()
            # une fois par mot-clé — un appel avec plusieurs mots-clés ici
            # reproduirait le bug qu'on vient de corriger.
            log.warning(
                "[DEBUG][FranceTravail] fetch() appelé avec %d mots-clés combinés (%r) — "
                "motsCles utilisera un ET logique côté API, ce qui restreint trop la "
                "recherche. Préférer un appel par mot-clé.",
                len(keywords),
                keywords,
            )

        token = self._get_token()
        params = {
            "motsCles": ",".join(keywords),
            "publieeDepuis": max_days,
            "sort": 1,  # tri par date de publication décroissante
        }
        if settings.ALTERNANCE_ONLY:
            # Paramètre booléen dédié (distinct de typeContrat) — voir
            # https://francetravail.io/produits-partenaires/catalogue/offres-emploi/documentation
            params["alternance"] = "true"

        # TODO(debug temporaire) : nombre brut d'offres retournées par l'API (1/3)
        log.info("[DEBUG][FranceTravail] requête search avec params=%s", params)
        response = self.session.get(
            settings.FRANCE_TRAVAIL_SEARCH_URL,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        log.info(
            "[DEBUG][FranceTravail] réponse HTTP %s — Content-Range=%s",
            response.status_code,
            response.headers.get("Content-Range", "absent"),
        )
        # 204 = aucune offre trouvée
        if response.status_code == 204:
            log.info("[DEBUG][FranceTravail] 0 offre brute (204 No Content)")
            return []
        if response.status_code >= 400:
            raise requests.HTTPError(
                f"France Travail search a échoué ({response.status_code}) — "
                f"params={params} — corps de la réponse: {response.text}",
                response=response,
            )

        results = response.json().get("resultats", [])
        log.info("[DEBUG][FranceTravail] %d offre(s) brute(s) reçue(s) de l'API", len(results))
        return [self._to_job_offer(item) for item in results]

    @staticmethod
    def _to_job_offer(item: dict) -> JobOffer:
        raw_date = item.get("dateCreation", "")
        try:
            date_posted = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).date()
        except ValueError:
            date_posted = date.today()

        entreprise = item.get("entreprise", {}) or {}
        lieu = item.get("lieuTravail", {}) or {}
        origine = item.get("origineOffre", {}) or {}
        contact = item.get("contact", {}) or {}

        return JobOffer(
            job_id=item["id"],
            title=item.get("intitule", ""),
            company=entreprise.get("nom", "Entreprise non précisée"),
            description=item.get("description", ""),
            url=origine.get("urlOrigine", ""),
            date_posted=date_posted,
            location=lieu.get("libelle", ""),
            source=FranceTravailSource.name,
            contact_email=contact.get("courriel", ""),
        )
