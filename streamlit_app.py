"""Streamlit UI for the European Conference Intelligence Agent."""
import asyncio
import csv
import io
import json
from datetime import date
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="European Conference Intelligence", page_icon="🛡️", layout="wide")
st.title("🛡️ European Conference Intelligence")
st.caption("Discover AI, cloud computing and cybersecurity conferences across Europe")

COUNTRIES = [
    "Albania", "Andorra", "Austria", "Belarus", "Belgium", "Bosnia and Herzegovina",
    "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark", "Estonia", "Finland",
    "France", "Germany", "Greece", "Hungary", "Iceland", "Ireland", "Italy",
    "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta",
    "Moldova", "Monaco", "Montenegro", "Netherlands", "North Macedonia", "Norway",
    "Poland", "Portugal", "Romania", "San Marino", "Serbia", "Slovakia", "Slovenia",
    "Spain", "Sweden", "Switzerland", "Ukraine", "United Kingdom", "Vatican City",
]
ALIASES = {"czech republic": "Czechia", "uk": "United Kingdom", "great britain": "United Kingdom", "the netherlands": "Netherlands"}

with st.sidebar:
    st.header("Search settings")
    country = st.selectbox("Location", ["All Europe", *COUNTRIES])
    category = st.selectbox("Conference category", ["All categories", "AI", "Cloud", "Cybersecurity"])
    year = st.number_input("Conference year", min_value=date.today().year, max_value=date.today().year + 8, value=max(2027, date.today().year), step=1)
    limit = st.selectbox("Discovery limit", [5, 10, 20, 30], index=1)
    st.caption("Discovery limit applies before country and category filtering.")
    search = st.button("🔎 Discover conferences", type="primary", use_container_width=True)


def normalize_country(value):
    value = str(value or "").strip()
    return ALIASES.get(value.casefold(), value).casefold()


def record_from_event(event):
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    if isinstance(event, dict):
        return event
    raise TypeError(f"Unsupported conference record: {type(event).__name__}")


def category_matches(value, selected):
    if selected == "All categories":
        return True
    value = str(value or "").casefold()
    keywords = {
        "AI": ("ai", "artificial intelligence", "machine learning", "generative ai"),
        "Cloud": ("cloud", "cloud computing"),
        "Cybersecurity": ("cybersecurity", "cyber security", "infosec", "information security"),
    }
    return value == selected.casefold() or any(word in value for word in keywords[selected])


if search:
    try:
        from europe_conference_intel_agent.conference_agent import discover
        with st.spinner("Researching conferences. This may take a few minutes..."):
            discovered = asyncio.run(
    discover(
        year=int(year),
        limit=int(limit),
        country=country,
        category=category,
    )
)
            records = [record_from_event(item) for item in discovered]
        st.session_state["conference_records"] = records
        st.session_state["searched_year"] = int(year)
        st.success(f"Discovery returned {len(records)} conference records.")
    except Exception as exc:
        st.error("Discovery could not be completed. Confirm your API key, model configuration and network access.")
        with st.expander("Technical details"):
            st.code(f"{type(exc).__name__}: {exc}")

records = st.session_state.get("conference_records", [])
if records:
    filtered = [r for r in records if (country == "All Europe" or normalize_country(r.get("country")) == normalize_country(country)) and category_matches(r.get("category"), category)]
    verified = sum(str(r.get("verification_status", "")).casefold() == "verified" for r in filtered)
    a, b, c = st.columns(3)
    a.metric("Matching conferences", len(filtered))
    b.metric("Verified", verified)
    c.metric("Awaiting verification", len(filtered) - verified)
    if country != "All Europe":
        st.info("Country filtering currently applies to the Europe-wide discovery results. No matches does not mean no conferences exist in that country.")
    if filtered:
        columns = ["name", "category", "country", "city", "start_date", "end_date", "announcement_completeness", "verification_status", "official_url", "evidence_url", "verification_notes"]
        available = [c for c in columns if any(c in r for r in filtered)]
        st.dataframe([{c: r.get(c) for c in available} for r in filtered], hide_index=True, use_container_width=True)
        st.subheader("Conference evidence")
        for event in filtered:
            with st.expander(f"{event.get('name', 'Unnamed conference')} · {event.get('country', 'Country unknown')}"):
                st.write(f"**Status:** {event.get('verification_status', 'Not Verified')}")
                st.write(f"**Evidence notes:** {event.get('verification_notes') or 'No evidence notes provided.'}")
                for key, label in [("official_url", "Official website"), ("evidence_url", "Evidence source")]:
                    url = event.get(key)
                    if isinstance(url, str) and url.startswith("https://"):
                        st.markdown(f"[{label}]({url})")
        st.download_button("Download JSON", data=json.dumps(filtered, indent=2, ensure_ascii=False, default=str), file_name="europe_conferences.json", mime="application/json")
        output = io.StringIO()
        fields = list(dict.fromkeys(k for record in filtered for k in record))
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(filtered)
        st.download_button("Download CSV", data=output.getvalue().encode("utf-8-sig"), file_name="europe_conferences.csv", mime="text/csv")
    else:
        st.warning("No records matched these filters. Try All Europe or a larger discovery limit.")
else:
    st.info("Select your search settings and click Discover conferences to begin.")

st.caption("Verification labels reflect the discovery engine's current evidence assessment. They are not independent guarantees of event authenticity.")
