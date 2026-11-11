# European Conference Intelligence Agent

An AI-powered Python application for discovering, assessing, and monitoring upcoming AI, cloud computing, and cybersecurity conferences across Europe.

## Features

- AI-powered conference discovery using the OpenAI Agents SDK
- Official website evidence assessment
- Conference classification
- Date validation and duplicate detection
- Verified and Not Verified status reporting
- JSON and CSV report generation
- Conference change detection
- GitHub Actions workflow for scheduled monitoring

## Technology Stack

Python 3.13, OpenAI Agents SDK, Pydantic, HTTPX, Beautiful Soup, uv, and GitHub Actions.

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/YOUR_USERNAME/europe-conference-intel-agent.git
cd europe-conference-intel-agent
uv sync --locked
```

Create a `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=your_supported_model
```

Never commit API credentials.

## Run the Agent

```bash
uv run europe-conference-intel-agent --year 2027 --limit 10
```

## Reports

Reports are generated in the `reports/` directory.

Each record includes conference name, category, location, dates, official website, supporting evidence, verification status, and assessment notes.

**Verified:** Sufficient official evidence confirms the conference details.

**Not Verified:** Available evidence is insufficient or inconsistent. This does not necessarily mean the conference is fraudulent.

## Change Detection

The application compares consecutive local reports and identifies newly discovered conferences, updated information, and conferences not seen in the latest search.

## Automation

GitHub Actions can execute scheduled conference discovery. Cross-run historical storage and production scheduling require final validation.

## Security

API credentials are stored outside source control. External website content is treated as untrusted, and verification outcomes are evidence-based.

## Project Status

Version 0.1.0. Development in progress. Final testing and deployment validation pending.
