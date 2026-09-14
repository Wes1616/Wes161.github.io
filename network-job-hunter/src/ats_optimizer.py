"""Optimisation ATS : extrait les mots-clés d'une offre et adapte le profil.

Utilise le SDK `anthropic` avec un appel structuré (tool use) pour garantir
une sortie exploitable directement, sans parsing de texte libre.

Contrainte forte : le modèle ne doit JAMAIS inventer une expérience, une
compétence ou un résultat qui n'existe pas dans le profil de base — il ne
fait que réordonner, sélectionner et reformuler ce qui existe déjà.
"""
from __future__ import annotations

import anthropic

from config import settings
from src.models import CandidateProfile, Experience, JobOffer, OptimizedContent

_TOOL_NAME = "submit_ats_analysis"

_TOOL_SCHEMA = {
    "name": _TOOL_NAME,
    "description": (
        "Soumet l'analyse ATS d'une offre par rapport au profil du candidat : "
        "mots-clés techniques détectés, score de correspondance, et une version "
        "du CV réordonnée/reformulée mettant en avant les éléments pertinents."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "matched_keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Mots-clés techniques de l'offre retrouvés dans le profil (ex: VLAN, DHCP, Cisco, BGP).",
            },
            "match_score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Score de correspondance global entre l'offre et le profil.",
            },
            "prioritized_competence_categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Clés des catégories de compétences du profil à mettre en avant en premier, dans l'ordre.",
            },
            "rewritten_summary": {
                "type": "string",
                "description": "Résumé de profil reformulé (2-3 phrases) mettant en avant l'adéquation avec l'offre, sans inventer de fait nouveau.",
            },
            "rewritten_experiences": {
                "type": "array",
                "description": "Les MÊMES expériences que le profil de base, réordonnées et avec des puces reformulées, jamais inventées.",
                "items": {
                    "type": "object",
                    "properties": {
                        "poste": {"type": "string"},
                        "entreprise": {"type": "string"},
                        "periode": {"type": "string"},
                        "lieu": {"type": "string"},
                        "bullets": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["poste", "entreprise", "periode", "lieu", "bullets"],
                },
            },
        },
        "required": [
            "matched_keywords",
            "match_score",
            "prioritized_competence_categories",
            "rewritten_summary",
            "rewritten_experiences",
        ],
    },
}

_SYSTEM_PROMPT = """Tu es un expert en optimisation de CV pour les systèmes ATS \
(Applicant Tracking System), spécialisé dans les métiers de l'infrastructure \
réseau. On te donne le profil de base d'un candidat (JSON) et le texte d'une \
offre d'emploi. Ta tâche :

1. Identifier les mots-clés techniques de l'offre (protocoles, équipements, \
outils, méthodologies) qui sont EFFECTIVEMENT présents dans le profil du \
candidat.
2. Calculer un score de correspondance honnête entre 0 et 100.
3. Choisir l'ordre des catégories de compétences du profil à mettre en avant.
4. Réécrire le résumé et les puces des expériences pour utiliser le \
vocabulaire exact de l'offre quand c'est fidèle à la réalité du profil.

RÈGLE ABSOLUE : tu ne dois jamais inventer une compétence, un outil, une \
expérience, une responsabilité ou un résultat qui n'apparaît pas dans le \
profil fourni. Tu reformules et priorises, tu n'ajoutes pas de contenu \
factuel nouveau. Si l'offre demande une compétence absente du profil, tu ne \
l'ajoutes pas aux mots-clés retenus.

Réponds uniquement en appelant l'outil {tool_name}.""".format(tool_name=_TOOL_NAME)


class AtsOptimizer:
    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self.client = client or anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def optimize(self, job: JobOffer, profile: CandidateProfile) -> OptimizedContent:
        profile_payload = {
            "summary": profile.summary,
            "competences": profile.competences,
            "experiences": [
                {
                    "poste": e.poste,
                    "entreprise": e.entreprise,
                    "periode": e.periode,
                    "lieu": e.lieu,
                    "bullets": e.bullets,
                }
                for e in profile.experiences
            ],
        }

        message = self.client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Profil du candidat (JSON) :\n{profile_payload}\n\n"
                        f"Offre d'emploi — {job.title} chez {job.company} :\n"
                        f"{job.description}"
                    ),
                }
            ],
        )

        tool_use = next(
            block for block in message.content if getattr(block, "type", None) == "tool_use"
        )
        data = tool_use.input

        return OptimizedContent(
            matched_keywords=data["matched_keywords"],
            match_score=data["match_score"],
            prioritized_competence_categories=data["prioritized_competence_categories"],
            rewritten_summary=data["rewritten_summary"],
            rewritten_experiences=[
                Experience(
                    poste=e["poste"],
                    entreprise=e["entreprise"],
                    periode=e["periode"],
                    lieu=e["lieu"],
                    bullets=e["bullets"],
                )
                for e in data["rewritten_experiences"]
            ],
        )
