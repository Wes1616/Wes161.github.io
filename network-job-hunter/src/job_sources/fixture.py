"""Source d'offres statique (JSON local), utilisée en démonstration / dry-run
quand aucun identifiant France Travail n'est configuré."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from src.job_sources.base import JobSource
from src.models import JobOffer


class FixtureJobSource(JobSource):
    name = "fixture"

    def __init__(self, path: Path) -> None:
        self.path = path

    def fetch(self, keywords: list[str], max_days: int) -> list[JobOffer]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        offers = []
        for i, item in enumerate(raw):
            offers.append(
                JobOffer(
                    job_id=item["job_id"],
                    title=item["title"],
                    company=item["company"],
                    description=item["description"],
                    url=item.get("url", ""),
                    date_posted=date.today() - timedelta(days=i + 1),
                    location=item.get("location", ""),
                    source=self.name,
                    contact_email=item.get("contact_email", ""),
                )
            )
        return offers
