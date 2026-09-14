"""Optimisation ATS : extrait les mots-clés d'une offre et adapte le profil.

Utilise l'API Gemini (`google-generativeai`) en mode JSON forcé
(`response_mime_type="application/json"`) pour garantir une sortie
structurée et exploitable directement, sans parsing de texte libre.

Contrainte forte : le modèle ne doit JAMAIS inventer une expérience, une
compétence ou un résultat qui n'existe pas dans le profil de base — il ne
fait que réordonner, sélectionner et reformuler ce qui existe déjà.
"""
from __future__ import annotations

import json

import google.generativeai as genai

from config import settings
from src.models import CandidateProfile, Experience, JobOffer, OptimizedContent

_RESPONSE_JSON_SHAPE = """{
  "matched_keywords": ["mots-clés techniques de l'offre retrouvés dans le profil, ex: VLAN, DHCP, Cisco"],
  "match_score": 0,
  "prioritized_competence_categories": ["clés des catégories de compétences du profil à mettre en avant en premier, dans l'ordre"],
  "rewritten_summary": "résumé de profil reformulé (2-3 phrases)",
  "rewritten_experiences": [
    {
      "poste": "...",
      "entreprise": "...",
      "periode": "...",
      "lieu": "...",
      "bullets": ["..."]
    }
  ]
}"""

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

Réponds UNIQUEMENT avec un objet JSON valide respectant EXACTEMENT cette \
forme, sans aucun texte avant/après ni bloc markdown :
{shape}""".format(shape=_RESPONSE_JSON_SHAPE)


class AtsOptimizer:
    def __init__(self, model: genai.GenerativeModel | None = None) -> None:
        if model is not None:
            self.model = model
        else:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=_SYSTEM_PROMPT,
            )

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

        response = self.model.generate_content(
            f"Profil du candidat (JSON) :\n{profile_payload}\n\n"
            f"Offre d'emploi — {job.title} chez {job.company} :\n"
            f"{job.description}",
            generation_config={"response_mime_type": "application/json"},
        )

        data = json.loads(response.text)

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
