"""Configuration centrale : variables d'environnement et constantes du domaine."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# --- Filtre offres ---------------------------------------------------------
POSTED_WITHIN_DAYS = 7
ALTERNANCE_CONTRACT_TYPE = "E"  # code France Travail pour "Contrat d'apprentissage"

# Mots-clés utilisés pour la recherche ET pour filtrer les offres hors-sujet.
DOMAIN_KEYWORDS = [
    "réseau",
    "reseau",
    "infrastructure",
    "sisr",
    "dhcp",
    "vlan",
    "routeur",
    "switch",
    "commutateur",
    "cisco",
    "routing",
    "switching",
    "netops",
    "supervision réseau",
    "administrateur systèmes et réseaux",
    "technicien réseau",
]

DEFAULT_SEARCH_KEYWORDS = ["technicien réseau", "infrastructure réseau", "SISR"]

# --- France Travail API -----------------------------------------------------
FRANCE_TRAVAIL_CLIENT_ID = _env("FRANCE_TRAVAIL_CLIENT_ID")
FRANCE_TRAVAIL_CLIENT_SECRET = _env("FRANCE_TRAVAIL_CLIENT_SECRET")
FRANCE_TRAVAIL_TOKEN_URL = (
    "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
)
FRANCE_TRAVAIL_SEARCH_URL = (
    "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
)
FRANCE_TRAVAIL_SCOPE = "api_offresdemploiv2 o2dsoffre"

# --- Gemini (Google Generative AI) --------------------------------------------
GEMINI_API_KEY = _env("GEMINI_API_KEY")
GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-2.5-flash")

# --- SMTP ----------------------------------------------------------------------
SMTP_HOST = _env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(_env("SMTP_PORT", "587"))
SMTP_USER = _env("SMTP_USER")
SMTP_PASSWORD = _env("SMTP_PASSWORD")
SENDER_NAME = _env("SENDER_NAME", "Candidat")
SENDER_EMAIL = _env("SENDER_EMAIL", SMTP_USER)

# --- Stockage ------------------------------------------------------------------
DATABASE_PATH = BASE_DIR / _env("DATABASE_PATH", "data/app.db")
PROFILE_PATH = BASE_DIR / "data" / "profile.yaml"
OUTPUT_DIR = BASE_DIR / "output"
EMAIL_TEMPLATE_PATH = BASE_DIR / "templates" / "email_template.txt"
