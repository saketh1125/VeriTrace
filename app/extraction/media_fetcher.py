from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

MAX_BYTES = 15 * 1024 * 1024
TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def _assert_safe_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS media URLs are accepted")
    host = parsed.hostname
    if not host:
        raise ValueError("Media URL has no hostname")
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Media hostname could not be resolved") from exc
    for *_, sockaddr in addresses:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Private/internal media destinations are blocked")


async def fetch_bytes(url: str) -> tuple[bytes, str]:
    _assert_safe_url(url)
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
        async with client.stream("GET", url, headers={"User-Agent": "hh-goa-face-chain/0.1"}) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
            if not content_type.startswith(("image/", "video/")):
                raise ValueError(f"Unsupported media content type: {content_type}")
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > MAX_BYTES:
                    raise ValueError("Media exceeds configured size limit")
            return bytes(content), content_type
