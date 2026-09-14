import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from src.ats_optimizer import AtsOptimizer
from src.models import CandidateProfile, JobOffer

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_job() -> JobOffer:
    raw = json.loads((FIXTURE_DIR / "sample_job.json").read_text())
    return JobOffer(
        job_id=raw["job_id"],
        title=raw["title"],
        company=raw["company"],
        description=raw["description"],
        url=raw["url"],
        date_posted=date.fromisoformat(raw["date_posted"]),
        location=raw["location"],
        source=raw["source"],
    )


def load_profile() -> CandidateProfile:
    return CandidateProfile.from_yaml(Path(__file__).parent.parent / "data" / "profile.yaml")


class FakeGeminiModel:
    def __init__(self, response_payload: dict) -> None:
        self.response_payload = response_payload
        self.last_args: tuple | None = None
        self.last_kwargs: dict | None = None

    def generate_content(self, *args, **kwargs):
        self.last_args = args
        self.last_kwargs = kwargs
        return SimpleNamespace(text=json.dumps(self.response_payload))


def make_fake_response_payload() -> dict:
    return {
        "matched_keywords": ["VLAN", "DHCP", "Cisco Packet Tracer"],
        "match_score": 78,
        "prioritized_competence_categories": ["routage_commutation", "supervision_exploitation"],
        "rewritten_summary": "Étudiant BTS SIO SISR avec une expérience concrète en VLAN et DHCP.",
        "rewritten_experiences": [
            {
                "poste": "Projet BTS — Déploiement d'un serveur DHCP et gestion des baux IP",
                "entreprise": "Projet d'études (cas Orange, établissement scolaire)",
                "periode": "2025",
                "lieu": "",
                "bullets": [
                    "Configuration de serveurs DHCP multi-VLAN sur routeurs Cisco",
                ],
            }
        ],
    }


def test_optimize_parses_structured_json_response() -> None:
    job = load_job()
    profile = load_profile()
    fake_model = FakeGeminiModel(make_fake_response_payload())
    optimizer = AtsOptimizer(model=fake_model)

    result = optimizer.optimize(job, profile)

    assert result.match_score == 78
    assert "VLAN" in result.matched_keywords
    assert result.rewritten_experiences[0].poste.startswith("Projet BTS")
    # Le mode JSON doit être forcé (pas de texte libre à parser)
    assert fake_model.last_kwargs["generation_config"]["response_mime_type"] == "application/json"
