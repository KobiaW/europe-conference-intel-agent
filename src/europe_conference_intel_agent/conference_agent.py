import argparse
import asyncio
import csv
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from agents import Agent, Runner, WebSearchTool
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from europe_conference_intel_agent.verification import verify_event
from europe_conference_intel_agent.change_detection import latest_comparison

class Conference(BaseModel):
    name: str
    category: str
    country: str
    city: str
    start_date: date
    end_date: date
    official_url: str
    evidence_url: str
    verification_status: str
    verification_notes: str


class ConferenceReport(BaseModel):
    conferences: list[Conference] = Field(default_factory=list)


def valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and "." in parsed.hostname
        and not parsed.username
        and not parsed.password
    )


def validate_conferences(items: list[Conference]) -> list[Conference]:
    today = datetime.now(timezone.utc).date()
    accepted = []
    seen = set()

    for event in items:
        if event.start_date < today:
            continue

        if event.end_date < event.start_date:
            continue

        key = (
            event.name.casefold().strip(),
            event.start_date.isoformat(),
            event.country.casefold().strip(),
        )

        if key in seen:
            continue

        seen.add(key)
        accepted.append(event)

    return sorted(accepted, key=lambda event: event.start_date)


def save_reports(events: list[Conference], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    json_path = directory / f"conferences_{timestamp}.json"
    csv_path = directory / f"conferences_{timestamp}.csv"

    records = [event.model_dump(mode="json") for event in events]

    json_path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    fields = list(Conference.model_fields.keys())

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    print(f"JSON report: {json_path}")
    print(f"CSV report:  {csv_path}")
    print(f"Events retained: {len(events)}")



async def discover(
    year: int,
    limit: int,
    country: str = "All Europe",
    category: str = "All categories",
) -> list[Conference]:
    """Discover conferences using the selected location and category."""

    if not 2026 <= year <= 2100:
        raise ValueError("Invalid conference year")

    if not 1 <= limit <= 50:
        raise ValueError("Conference limit must be between 1 and 50")

    allowed_categories = {
        "All categories": None,
        "AI": "AI",
        "Artificial Intelligence": "AI",
        "Cloud": "Cloud",
        "Cloud Computing": "Cloud",
        "Cybersecurity": "Cybersecurity",
    }

    if category not in allowed_categories:
        raise ValueError("Unsupported conference category")

    selected_category = allowed_categories[category]

    if country == "All Europe":
        location_instruction = "across Europe"
    else:
        if not country or len(country) > 80 or not all(
            character.isalpha() or character in " -'"
            for character in country
        ):
            raise ValueError("Invalid country selection")

        location_instruction = f"in {country}"

    category_instruction = (
        f"specifically covering {selected_category}"
        if selected_category
        else "covering AI, cloud computing, or cybersecurity"
    )

    agent = Agent(
        name="European Conference Intelligence Agent",
        model=os.getenv("OPENAI_MODEL", "gpt-5.4"),
        instructions=(
            "You are a professional conference intelligence analyst. "
            "Search the live web for genuine upcoming technology conferences. "
            "Use official organizer websites as primary evidence. "
            "Never invent conferences, dates, cities, venues, or URLs. "
            "Do not treat event aggregators as proof of authenticity. "
            "Conference dates may be unknown when an event has been "
            "officially announced but its schedule is pending. "
            "Retain preliminary announcements when credible evidence exists. "
            "Use categories AI, Cloud, or Cybersecurity. "
            "Do not claim independent verification based solely on "
            "matching webpage text. "
            "Explain evidence and uncertainty in verification_notes. "
            "The downstream verification engine determines final "
            "verification status."
        ),
        tools=[WebSearchTool()],
        output_type=ConferenceReport,
    )

    result = await Runner.run(
        agent,
        (
            f"Find up to {limit} genuine upcoming conferences "
            f"{location_instruction}, {category_instruction}, "
            f"scheduled for {year}. "
            f"Today is {datetime.now(timezone.utc).date().isoformat()}. "
            "Include official organizer URLs and evidence URLs. "
            "Retain officially announced events whose exact dates "
            "have not yet been published. "
            "Do not include conferences outside the requested country "
            "or year."
        ),
        max_turns=12,
    )

    events = validate_conferences(result.final_output.conferences)

    if country != "All Europe":
        events = [
            event for event in events
            if event.country.strip().casefold() == country.casefold()
        ]

    if selected_category:
        events = [
            event for event in events
            if event.category.strip().casefold()
            == selected_category.casefold()
        ]

    return events[:limit]


    result = await Runner.run(
        agent,
        (
            f"Find up to {limit} genuine European AI, cloud, and "
            f"cybersecurity conferences taking place from {year} onward. "
            f"Today is {datetime.now(timezone.utc).date().isoformat()}. "
            "Search the web and provide traceable official evidence."
        ),
        max_turns=12,
    )

    return validate_conferences(result.final_output.conferences)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover upcoming European technology conferences"
    )
    parser.add_argument("--year", type=int, default=2027)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.year < 2027 or not 1 <= args.limit <= 30:
        parser.error("Year must be 2027 or later; limit must be 1 to 30.")

    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is missing from the environment.")

    print("Starting European conference discovery...")

    events = asyncio.run(discover(args.year, args.limit))

    print("Checking conference evidence...")

    for event in events:
        verification = asyncio.run(verify_event(event))

        event.verification_status = verification["status"]
        event.verification_notes = verification["evidence"]

        print(f"{event.name}: {event.verification_status}")
        print(f"Evidence: {event.verification_notes}")

    save_reports(events, Path("reports"))



    # Compare the latest report with the previous report
    changes = latest_comparison(Path("reports"))

    if changes is not None:
        print("\nConference Intelligence Changes")
        print(f"New: {len(changes['new'])}")
        print(f"Updated: {len(changes['updated'])}")
        print(
            "Not seen in latest search: "
            f"{len(changes['not_seen_in_latest_search'])}"
        )

        Path("reports/latest_changes.json").write_text(
            json.dumps(changes, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    else:
        print("No previous report available for comparison.")


if __name__ == "__main__":
    main()
    

