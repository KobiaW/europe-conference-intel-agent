"""European Conference Intelligence Agent: styled Streamlit interface.

Run: uv run streamlit run streamlit_app.py
Requires the project's discover(year, limit, country, category) backend.
"""
import asyncio
import csv
import io
import json
from datetime import date
from urllib.parse import urlsplit

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="European Conference Intelligence Agent", page_icon="🌍", layout="wide", initial_sidebar_state="collapsed")

COUNTRIES = [
    "Albania", "Andorra", "Austria", "Belarus", "Belgium", "Bosnia and Herzegovina",
    "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark", "Estonia", "Finland",
    "France", "Germany", "Greece", "Hungary", "Iceland", "Ireland", "Italy",
    "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta",
    "Moldova", "Monaco", "Montenegro", "Netherlands", "North Macedonia", "Norway",
    "Poland", "Portugal", "Romania", "San Marino", "Serbia", "Slovakia", "Slovenia",
    "Spain", "Sweden", "Switzerland", "Ukraine", "United Kingdom", "Vatican City",
]
ALIASES = {"czech republic": "czechia", "uk": "united kingdom", "great britain": "united kingdom", "the netherlands": "netherlands"}

st.markdown("""
<style>
.stApp {background: #f4f7fc; color: #10234b;}
.block-container {max-width: 1540px; padding-top: 1rem; padding-bottom: 2rem;}
.hero {background: radial-gradient(circle at 91% 18%,#135fa4 0%,transparent 28%),linear-gradient(115deg,#061532,#082755 72%,#041126);border-radius:19px;padding:30px 38px;color:white;margin-bottom:22px;box-shadow:0 10px 30px #0c2b5722;}
.hero-title {font-size:clamp(26px,3vw,47px);font-weight:800;line-height:1.12;letter-spacing:-1.1px;margin:0;}
.hero-title span {color:#22c9f5;}
.hero-sub {font-size:clamp(14px,1.5vw,20px);color:#e0efff;margin-top:12px;}
.section-head {font-size:22px;font-weight:800;color:#0a2352;margin:18px 0 8px;}
.stButton > button[kind="primary"] {background:linear-gradient(105deg,#0760e7,#0a49ca);border:0;border-radius:12px;font-weight:750;min-height:45px;box-shadow:0 5px 14px #1457c62a;}
.stButton > button[kind="primary"]:hover {background:#0747ba;}
[data-testid="stMetric"] {background:white;border:1px solid #d9e5f6;border-radius:15px;padding:16px 18px;box-shadow:0 3px 10px #1c448013;}
[data-testid="stMetricLabel"] {color:#36517a;}
[data-testid="stMetricValue"] {color:#08295f;font-weight:800;}
[data-testid="stDataFrame"] {border:1px solid #cbdcf3;border-radius:13px;overflow:hidden;}
[data-testid="stExpander"] {background:#fff;border:1px solid #d9e5f6;border-radius:11px;}
[data-testid="stAlert"] {border-radius:12px;}
[data-testid="stDownloadButton"] button {border-radius:10px;}
.footer {background:#071b3e;color:#dcecff;padding:16px 24px;border-radius:12px;margin-top:25px;font-size:13px;}
.small-note {color:#5b6c89;font-size:13px;}
</style>
""", unsafe_allow_html=True)

st.markdown('''<div class="hero"><div class="hero-title">🤖 European <span>Conference Intelligence</span> Agent 🌍</div><div class="hero-sub">Discover AI, Cloud Computing and Cybersecurity conferences across Europe, with traceable organizer evidence.</div></div>''', unsafe_allow_html=True)


def normalize_country(value):
    text = str(value or "").strip().casefold()
    return ALIASES.get(text, text)


def category_matches(value, selected):
    if selected == "All categories":
        return True
    normalized = str(value or "").strip().casefold()
    options = {
        "AI": ("ai", "artificial intelligence", "machine learning", "generative ai"),
        "Cloud": ("cloud", "cloud computing"),
        "Cybersecurity": ("cybersecurity", "cyber security", "infosec", "information security"),
    }
    return normalized in options[selected]


def record_from_event(event):
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    if isinstance(event, dict):
        return event
    raise TypeError("Unsupported conference record")


def safe_link(url):
    if not isinstance(url, str):
        return None
    try:
        parsed = urlsplit(url.strip())
        if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password:
            return url.strip()
    except ValueError:
        pass
    return None


with st.form("conference_search", border=True):
    a, b, c, d = st.columns([1.35, 1.3, .8, .8], gap="medium")
    with a:
        country = st.selectbox("🌍 Country / Region", ["All Europe", *COUNTRIES], index=0)
    with b:
        category = st.selectbox("🛡️ Category", ["All categories", "Cybersecurity", "AI", "Cloud"])
    with c:
        year = st.selectbox("📅 Conference year", list(range(max(2027, date.today().year), date.today().year + 9)))
    with d:
        limit = st.selectbox("📋 Max results", [5, 10, 20, 30], index=1)
    search = st.form_submit_button("🔎 Discover Conferences", type="primary", use_container_width=True)

if search:
    try:
        from europe_conference_intel_agent.conference_agent import discover
        with st.spinner(f"Researching {category.lower()} conferences in {country} for {year}…"):
            found = asyncio.run(discover(year=int(year), limit=int(limit), country=country, category=category))
            records = [record_from_event(event) for event in found]
        st.session_state["conference_results"] = records
        st.session_state["conference_query"] = {"country": country, "category": category, "year": year, "limit": limit}
    except Exception as exc:
        st.error("Discovery failed. Check the server configuration, network connection, and API access.")
        # Do not reveal API keys, request headers, or provider error payloads to users.
        st.session_state.pop("conference_results", None)
        st.session_state.pop("conference_query", None)

records = st.session_state.get("conference_results")
query = st.session_state.get("conference_query", {})
if records is not None:
    # Defense in depth: retain only results matching the original search, not current unsent controls.
    filtered = [r for r in records if (
        query.get("country") == "All Europe" or normalize_country(r.get("country")) == normalize_country(query.get("country"))
    ) and category_matches(r.get("category"), query.get("category", "All categories"))]
    verified = sum(str(r.get("verification_status", "")).strip().casefold() == "verified" for r in filtered)
    preliminary = sum(str(r.get("announcement_completeness", "")).strip().casefold() == "preliminary" for r in filtered)
    st.success(f"Search completed · {len(filtered)} matching conferences for {query.get('country')} in {query.get('year')}.")
    st.markdown('<div class="section-head">📊 Research Results</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3, gap="medium")
    m1.metric("Conferences found", len(filtered))
    m2.metric("Verified by backend", verified)
    m3.metric("Preliminary announcements", preliminary)
    if filtered:
        st.markdown('<div class="section-head">📍 Conference Directory</div>', unsafe_allow_html=True)
        display = []
        for r in filtered:
            display.append({
                "Conference": r.get("name") or "Unnamed",
                "Category": r.get("category") or "Unknown",
                "Country": r.get("country") or "Unknown",
                "City": r.get("city") or "TBA",
                "Start": r.get("start_date") or "TBA",
                "End": r.get("end_date") or "TBA",
                "Announcement": r.get("announcement_completeness") or "Unknown",
                "Verification": r.get("verification_status") or "Not Verified",
                "Official website": safe_link(r.get("official_url")),
            })
        st.dataframe(display, hide_index=True, use_container_width=True,
                     column_config={"Official website": st.column_config.LinkColumn("Official website", display_text="Visit official site")})
        st.markdown('<div class="section-head">🔍 Organizer Evidence</div>', unsafe_allow_html=True)
        for event in filtered:
            name = event.get("name") or "Unnamed conference"
            with st.expander(f"{name} · {event.get('country') or 'Country unknown'}"):
                st.write("**Verification:**", event.get("verification_status") or "Not Verified")
                st.write("**Announcement completeness:**", event.get("announcement_completeness") or "Unknown")
                st.write("**Evidence notes:**", event.get("verification_notes") or "No evidence notes supplied.")
                for field, label in (("official_url", "Official conference website"), ("evidence_url", "Evidence source")):
                    url = safe_link(event.get(field))
                    if url:
                        st.link_button(label, url)
        st.markdown('<div class="section-head">⬇️ Export Research</div>', unsafe_allow_html=True)
        x, y = st.columns(2)
        with x:
            st.download_button("Download JSON", json.dumps(filtered, indent=2, ensure_ascii=False, default=str),
                               "europe_conferences.json", "application/json", use_container_width=True)
        with y:
            buffer = io.StringIO()
            fields = list(dict.fromkeys(key for record in filtered for key in record))
            writer = csv.DictWriter(buffer, fieldnames=fields)
            writer.writeheader()
            writer.writerows(filtered)
            st.download_button("Download CSV", buffer.getvalue().encode("utf-8-sig"),
                               "europe_conferences.csv", "text/csv", use_container_width=True)
    else:
        st.warning("No matching conferences were returned. This does not establish that none exist. Try a broader search.")
else:
    st.info("Select your search criteria above, then click Discover Conferences to begin.")

st.markdown('<div class="small-note">Verification status reflects the backend evidence assessment, not a guarantee of event authenticity. Preliminary announcements may have unpublished dates or venues.</div>', unsafe_allow_html=True)
st.markdown('<div class="footer">🌍 European Conference Intelligence Agent &nbsp; | &nbsp; Powered by Python · OpenAI Agents SDK · Streamlit</div>', unsafe_allow_html=True)
