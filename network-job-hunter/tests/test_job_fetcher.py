from datetime import date, timedelta

from src.job_fetcher import JobFetcher
from src.job_sources.base import JobSource
from src.models import JobOffer


class FakeSource(JobSource):
    name = "fake"

    def __init__(self, offers: list[JobOffer]) -> None:
        self._offers = offers

    def fetch(self, keywords: list[str], max_days: int) -> list[JobOffer]:
        return self._offers


def offer(job_id: str, days_ago: int, title: str = "Technicien Réseau", description: str = "VLAN, DHCP, Cisco") -> JobOffer:
    return JobOffer(
        job_id=job_id,
        title=title,
        company="ACME",
        description=description,
        url="https://example.com",
        date_posted=date.today() - timedelta(days=days_ago),
        location="Paris",
        source="fake",
    )


def test_filters_out_offers_older_than_7_days() -> None:
    offers = [offer("recent", 3), offer("old", 10)]
    fetcher = JobFetcher(sources=[FakeSource(offers)])

    result = fetcher.fetch_new_offers()

    ids = {o.job_id for o in result}
    assert ids == {"recent"}


def test_filters_out_offers_outside_network_domain() -> None:
    offers = [
        offer("network", 1, title="Technicien Réseau", description="Configuration VLAN et DHCP"),
        offer("unrelated", 1, title="Vendeur en boulangerie", description="Accueil client, encaissement"),
    ]
    fetcher = JobFetcher(sources=[FakeSource(offers)])

    result = fetcher.fetch_new_offers()

    ids = {o.job_id for o in result}
    assert ids == {"network"}


def test_deduplicates_offers_seen_across_sources() -> None:
    shared = offer("dup", 1)
    fetcher = JobFetcher(sources=[FakeSource([shared]), FakeSource([shared])])

    result = fetcher.fetch_new_offers()

    assert len(result) == 1


class TrackerStub:
    def __init__(self, known_ids: set[str]) -> None:
        self.known_ids = known_ids

    def is_known(self, job_id: str) -> bool:
        return job_id in self.known_ids


def test_excludes_offers_already_known_to_tracker() -> None:
    offers = [offer("already-applied", 1), offer("new", 1)]
    fetcher = JobFetcher(
        sources=[FakeSource(offers)],
        tracker=TrackerStub(known_ids={"already-applied"}),
    )

    result = fetcher.fetch_new_offers()

    ids = {o.job_id for o in result}
    assert ids == {"new"}
