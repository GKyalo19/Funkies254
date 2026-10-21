from pathlib import Path

from apps.agent.extractors.jsonld import extract_events

FIXTURE = Path(__file__).parent / "fixtures" / "event_page.html"


def test_jsonld_extractor_reads_a_saved_page():
    events = extract_events(FIXTURE.read_text())

    assert events[0]["title"] == "Saturday Debate"
    assert events[0]["registration_link"] == "https://school.example.com/debate"
