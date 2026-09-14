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


class FakeMessages:
    def __init__(self, tool_input: dict) -> None:
        self.tool_input = tool_input
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        tool_use_block = SimpleNamespace(type="tool_use", input=self.tool_input)
        return SimpleNamespace(content=[tool_use_block])


class FakeAnthropicClient:
    def __init__(self, tool_input: dict) -> None:
        self.messages = FakeMessages(tool_input)


def make_fake_tool_response() -> dict:
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


def test_optimize_parses_structured_tool_response() -> None:
    job = load_job()
    profile = load_profile()
    fake_client = FakeAnthropicClient(make_fake_tool_response())
    optimizer = AtsOptimizer(client=fake_client)

    result = optimizer.optimize(job, profile)

    assert result.match_score == 78
    assert "VLAN" in result.matched_keywords
    assert result.rewritten_experiences[0].poste.startswith("Projet BTS")
    # Le tool_choice doit forcer l'appel de l'outil structuré (pas de texte libre à parser)
    assert fake_client.messages.last_kwargs["tool_choice"]["name"] == "submit_ats_analysis"
