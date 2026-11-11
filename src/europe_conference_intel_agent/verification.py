import asyncio
import ipaddress
import re
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


def is_public_host(hostname: str) -> bool:
    """Reject hosts that resolve to private or reserved addresses."""
    try:
        addresses = socket.getaddrinfo(
            hostname, 443, type=socket.SOCK_STREAM
        )
        return bool(addresses) and all(
            ipaddress.ip_address(item[4][0]).is_global
            for item in addresses
        )
    except (OSError, ValueError):
        return False


async def verify_event(event) -> dict:
    """Check whether an official event page is accessible and relevant."""
    result = {
        "status": "unverified",
        "http_status": None,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "evidence": "",
    }

    url = event.official_url
    parsed = urlparse(url)

    if parsed.scheme != "https" or not parsed.hostname:
        result["evidence"] = "Invalid official website URL"
        return result

    if not await asyncio.to_thread(is_public_host, parsed.hostname):
        result["evidence"] = "Website host is not publicly resolvable"
        return result

    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = await client.get(url)

        result["http_status"] = response.status_code

        if response.status_code != 200:
            result["evidence"] = (
                f"Website returned HTTP {response.status_code}"
            )
            return result

        if len(response.content) > 2_000_000:
            result["evidence"] = "Website response exceeds size limit"
            return result

        content_type = response.headers.get("content-type", "").lower()

        if "text/html" not in content_type:
            result["evidence"] = "Website did not return HTML"
            return result

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        text = " ".join(soup.stripped_strings).lower()

        year = str(event.start_date.year)
        name_words = [
            word.lower()
            for word in re.findall(r"[a-zA-Z]{4,}", event.name)
            if word.lower() not in {"conference", "summit", "europe"}
        ]

        name_match = bool(name_words) and sum(
            word in text for word in name_words
        ) >= min(2, len(name_words))

        year_match = year in text

        if name_match and year_match:
            result["status"] = "page_match"
            result["evidence"] = (
                "Official URL is accessible and page contains "
                "conference-name terms and the event year. "
                "Exact dates and organizer authenticity remain unconfirmed."
            )
        else:
            result["evidence"] = (
                "Page accessible, but conference name or year "
                "could not be corroborated."
            )

    except httpx.HTTPError as exc:
        result["evidence"] = (
            f"Website request failed: {type(exc).__name__}"
        )

    return result
