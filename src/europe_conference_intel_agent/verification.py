import asyncio
import ipaddress
import re
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

MAX_BYTES = 2_000_000


def public_https_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        return False
    try:
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(item[4][0]).is_global for item in addresses)
    except (OSError, ValueError):
        return False


def normalized(text: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', text.casefold())).strip()


def date_signals(day) -> list[str]:
    return [day.isoformat(), f'{day.day} {day.strftime("%B")} {day.year}', f'{day.strftime("%B")} {day.day} {day.year}', f'{day.day} {day.strftime("%b")} {day.year}', f'{day.strftime("%b")} {day.day} {day.year}']


async def verify_event(event) -> dict:
    result = {'status': 'Not Verified', 'http_status': None, 'checked_at': datetime.now(timezone.utc).isoformat(), 'evidence': '', 'evidence_url': event.official_url}
    if not await asyncio.to_thread(public_https_url, event.official_url):
        result['evidence'] = 'Official URL is invalid, unsafe, or not publicly resolvable'
        return result
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
            async with client.stream('GET', event.official_url) as response:
                result['http_status'] = response.status_code
                if response.status_code != 200:
                    result['evidence'] = f'Official URL returned HTTP {response.status_code}; redirects are not automatically followed'
                    return result
                if 'text/html' not in response.headers.get('content-type', '').lower():
                    result['evidence'] = 'Official URL did not return HTML'
                    return result
                chunks = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        result['evidence'] = 'Official page exceeded the download size limit'
                        return result
                    chunks.append(chunk)
                html = b''.join(chunks).decode(response.encoding or 'utf-8', errors='replace')
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer']):
            tag.decompose()
        text = normalized(' '.join(soup.stripped_strings))
        name_tokens = [word for word in normalized(event.name).split() if len(word) >= 4 and word not in {'conference', 'summit', 'europe', 'international', 'annual'}]
        name_match = bool(name_tokens) and sum(token in text for token in name_tokens) >= min(2, len(name_tokens))
        start_match = any(normalized(value) in text for value in date_signals(event.start_date))
        end_match = any(normalized(value) in text for value in date_signals(event.end_date))
        location_match = bool(event.city.strip()) and normalized(event.city) in text
        # Organizer identity cannot be inferred reliably from arbitrary page text.
        # This conservative check does not award Verified without independent organizer evidence.
        signals = f'name={name_match}, start_date={start_match}, end_date={end_match}, city={location_match}'
        result['evidence'] = f'Official-page evidence: {signals}. Organizer identity and authenticity require independent confirmation.'
        return result
    except (httpx.HTTPError, UnicodeError, ValueError) as exc:
        result['evidence'] = f'Official-page request failed: {type(exc).__name__}'
        return result
