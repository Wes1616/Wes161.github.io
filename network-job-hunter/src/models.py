"""Dataclasses partagées par le pipeline de candidature."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class JobOffer:
    job_id: str
    title: str
    company: str
    description: str
    url: str
    date_posted: date
    location: str = ""
    source: str = ""
    contact_email: str = ""

    @property
    def age_days(self) -> int:
        return (date.today() - self.date_posted).days


@dataclass
class Formation:
    diplome: str
    etablissement: str
    periode: str
    details: str = ""


@dataclass
class Experience:
    poste: str
    entreprise: str
    periode: str
    lieu: str
    bullets: list[str]


@dataclass
class CandidateProfile:
    full_name: str
    target_title: str
    email: str
    phone: str
    location: str
    summary: str
    formation: list[Formation]
    competences: dict[str, list[str]]
    experiences: list[Experience]
    certifications: list[str] = field(default_factory=list)
    langues: list[dict[str, str]] = field(default_factory=list)
    linkedin: str = ""
    github: str = ""

    @classmethod
    def from_yaml(cls, path: Path) -> "CandidateProfile":
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
        identity = raw["identity"]
        return cls(
            full_name=identity["full_name"],
            target_title=identity.get("target_title", ""),
            email=identity.get("email", ""),
            phone=identity.get("phone", ""),
            location=identity.get("location", ""),
            linkedin=identity.get("linkedin", ""),
            github=identity.get("github", ""),
            summary=raw.get("summary", "").strip(),
            formation=[Formation(**f) for f in raw.get("formation", [])],
            competences=raw.get("competences", {}),
            experiences=[Experience(**e) for e in raw.get("experiences", [])],
            certifications=raw.get("certifications", []) or [],
            langues=raw.get("langues", []) or [],
        )


@dataclass
class OptimizedContent:
    """Résultat de l'AtsOptimizer pour une offre donnée."""

    matched_keywords: list[str]
    match_score: int  # 0-100
    prioritized_competence_categories: list[str]
    rewritten_experiences: list[Experience]
    rewritten_summary: str


@dataclass
class ApplicationRecord:
    job_id: str
    title: str
    company: str
    source: str
    date_posted: date
    date_applied: datetime
    status: str
    match_score: int
    cv_path: str
