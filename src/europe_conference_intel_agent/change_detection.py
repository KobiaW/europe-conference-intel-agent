import json
from pathlib import Path


def load_report(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def event_key(event: dict) -> tuple:
    """Identify an event without relying on its date."""
    return (
        event["name"].strip().casefold(),
        event["country"].strip().casefold(),
    )


def latest_comparison(directory: Path) -> dict | None:
    """Compare the two most recent timestamped conference reports."""

    reports = sorted(directory.glob("conferences_*.json"))

    if len(reports) < 2:
        return None

    previous = load_report(reports[-2])
    current = load_report(reports[-1])

    previous_events = {
        event_key(event): event for event in previous
    }

    current_events = {
        event_key(event): event for event in current
    }

    new = []
    updated = []
    not_seen = []

    for key, event in current_events.items():
        if key not in previous_events:
            new.append(event)
            continue

        old_event = previous_events[key]

        changed_fields = {}

        for field in (
            "start_date",
            "end_date",
            "city",
            "official_url",
            "verification_status",
        ):
            if old_event.get(field) != event.get(field):
                changed_fields[field] = {
                    "previous": old_event.get(field),
                    "current": event.get(field),
                }

        if changed_fields:
            updated.append({
                "conference": event["name"],
                "changes": changed_fields,
            })

    for key, event in previous_events.items():
        if key not in current_events:
            not_seen.append(event)

    return {
        "previous_report": reports[-2].name,
        "current_report": reports[-1].name,
        "new": new,
        "updated": updated,
        "not_seen_in_latest_search": not_seen,
    }
