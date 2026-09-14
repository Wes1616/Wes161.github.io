from datetime import date, datetime
from pathlib import Path

from src.models import ApplicationRecord
from src.tracker import Tracker


def make_record(job_id: str = "job-1") -> ApplicationRecord:
    return ApplicationRecord(
        job_id=job_id,
        title="Technicien Réseau",
        company="ACME Networks",
        source="france_travail",
        date_posted=date(2026, 9, 10),
        date_applied=datetime(2026, 9, 14, 10, 0, 0),
        status="sent",
        match_score=82,
        cv_path="output/cv_job-1.pdf",
    )


def test_unknown_job_is_not_known(tmp_path: Path) -> None:
    tracker = Tracker(tmp_path / "app.db")
    assert tracker.is_known("job-1") is False
    tracker.close()


def test_record_then_known_and_no_duplicate(tmp_path: Path) -> None:
    tracker = Tracker(tmp_path / "app.db")
    tracker.record(make_record("job-1"))

    assert tracker.is_known("job-1") is True

    # Ré-enregistrer la même offre ne doit pas créer de doublon
    tracker.record(make_record("job-1"))
    rows = tracker.list_all()
    assert len(rows) == 1
    tracker.close()


def test_persists_across_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "app.db"
    with Tracker(db_path) as tracker:
        tracker.record(make_record("job-2"))

    with Tracker(db_path) as tracker:
        assert tracker.is_known("job-2") is True
        assert tracker.is_known("job-3") is False
