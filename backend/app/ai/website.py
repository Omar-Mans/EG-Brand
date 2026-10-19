"""Reads the text of a business website for the discovery step. Best effort, never fatal."""

import html
import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx

MAX_BYTES = 2_000_000
MAX_CHARS = 6000


class WebsiteError(Exception):
    pass


def _public_host(host: str) -> bool:
    """Blocks loopback, private, link-local and reserved addresses (no fetching the server's own network)."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False
    return True


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg|template)[^>]*>.*?</\1>", " ", raw)
    title = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw)
    meta = re.search(r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', raw)
    text = re.sub(r"(?s)<[^>]+>", " ", raw)
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    head = " | ".join(html.unescape(x.group(1).strip()) for x in (title, meta) if x)
    return (f"{head} | {text}" if head else text)[:MAX_CHARS]


def fetch_text(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url):
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise WebsiteError("الرابط مش صحيح")
    try:
        with httpx.Client(timeout=15, follow_redirects=False, headers={"User-Agent": "EGBrandBot/1.0"}) as c:
            for _ in range(4):  # follow redirects manually so every hop is checked
                host = urlparse(url).hostname or ""
                if not _public_host(host):
                    raise WebsiteError("الرابط ده مش متاح للقراءة")
                r = c.get(url)
                if r.is_redirect and r.headers.get("location"):
                    url = str(r.next_request.url) if r.next_request else r.headers["location"]
                    continue
                break
    except httpx.HTTPError as exc:
        raise WebsiteError(f"مقدرناش نفتح الموقع: {exc.__class__.__name__}") from exc
    if r.status_code >= 400:
        raise WebsiteError(f"الموقع رجّع {r.status_code}")
    if "html" not in r.headers.get("content-type", ""):
        raise WebsiteError("الرابط مش صفحة ويب")
    return html_to_text(r.content[:MAX_BYTES].decode(r.encoding or "utf-8", errors="ignore"))
