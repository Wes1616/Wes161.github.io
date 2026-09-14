"""Orchestration CLI du pipeline complet de candidature."""
from __future__ import annotations

import argparse
import logging
from datetime import datetime

from config import settings
from src.ats_optimizer import AtsOptimizer
from src.doc_generator import DocGenerator
from src.job_fetcher import JobFetcher
from src.job_sources.fixture import FixtureJobSource
from src.job_sources.france_travail import FranceTravailSource
from src.mail_dispatcher import MailDispatcher
from src.models import ApplicationRecord, CandidateProfile
from src.tracker import Tracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("network_job_hunter")


def run(dry_run: bool, limit: int | None) -> None:
    profile = CandidateProfile.from_yaml(settings.PROFILE_PATH)
    tracker = Tracker(settings.DATABASE_PATH)

    has_france_travail_creds = bool(
        settings.FRANCE_TRAVAIL_CLIENT_ID and settings.FRANCE_TRAVAIL_CLIENT_SECRET
    )
    if has_france_travail_creds:
        source = FranceTravailSource()
    elif dry_run:
        log.warning(
            "Identifiants France Travail absents : utilisation des offres de démonstration "
            "(data/sample_offers.json) pour ce dry-run."
        )
        source = FixtureJobSource(settings.BASE_DIR / "data" / "sample_offers.json")
    else:
        raise RuntimeError(
            "FRANCE_TRAVAIL_CLIENT_ID / FRANCE_TRAVAIL_CLIENT_SECRET manquants dans .env — "
            "requis pour une exécution réelle. Utilise --dry-run pour tester sans ces identifiants."
        )
    fetcher = JobFetcher(sources=[source], tracker=tracker)
    optimizer = AtsOptimizer()
    doc_generator = DocGenerator()
    dispatcher = MailDispatcher()

    log.info("Recherche des offres alternance 'infrastructure réseau' publiées ≤ %s jours...", settings.POSTED_WITHIN_DAYS)
    offers = fetcher.fetch_new_offers()
    if limit:
        offers = offers[:limit]
    log.info("%d nouvelle(s) offre(s) pertinente(s) trouvée(s).", len(offers))

    for offer in offers:
        log.info("Traitement : %s — %s", offer.title, offer.company)

        optimized = optimizer.optimize(offer, profile)
        log.info("  Score de correspondance ATS : %d/100", optimized.match_score)

        docx_path = doc_generator.build(profile, optimized, offer)
        pdf_path = doc_generator.convert_to_pdf(docx_path)
        log.info("  CV généré : %s", pdf_path)

        if not offer.contact_email:
            log.warning("  Aucune adresse email de contact sur l'offre — candidature non envoyée.")
            status = "skipped_no_email"
            sent = False
        elif dry_run:
            log.info("  [DRY-RUN] Email non envoyé à %s.", offer.contact_email)
            status = "dry_run"
            sent = False
        else:
            sent = dispatcher.send(
                offer, profile, offer.contact_email, pdf_path, optimized, dry_run=False
            )
            status = "sent" if sent else "failed"
            log.info("  Email envoyé à %s.", offer.contact_email)

        if not dry_run:
            tracker.record(
                ApplicationRecord(
                    job_id=offer.job_id,
                    title=offer.title,
                    company=offer.company,
                    source=offer.source,
                    date_posted=offer.date_posted,
                    date_applied=datetime.now(),
                    status=status,
                    match_score=optimized.match_score,
                    cv_path=str(pdf_path),
                )
            )

    tracker.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatisation de candidatures — Infrastructure Réseau")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Exécute le pipeline complet")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ne fetch/génère/envoie rien réellement : simule le pipeline et journalise chaque étape.",
    )
    run_parser.add_argument(
        "--limit", type=int, default=None, help="Nombre maximum d'offres à traiter."
    )

    args = parser.parse_args()
    if args.command == "run":
        run(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
