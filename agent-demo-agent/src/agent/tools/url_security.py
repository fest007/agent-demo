"""URL safety helpers for network-capable tools."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


_BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}
_BLOCKED_SUFFIXES = {".localhost", ".local"}
_BLOCKED_METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("100.100.100.200"),
}


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or ip in _BLOCKED_METADATA_IPS
    )


def validate_public_http_url(url: str) -> str:
    """Validate an outbound URL and return it when it is safe to request."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("只允许访问 http/https URL")
    if not parsed.hostname:
        raise ValueError("URL 缺少 hostname")

    host = parsed.hostname.lower().rstrip(".")
    if host in _BLOCKED_HOSTS or any(host.endswith(suffix) for suffix in _BLOCKED_SUFFIXES):
        raise ValueError("禁止访问 localhost 或本地域名")

    try:
        ip = ipaddress.ip_address(host)
        if _is_blocked_ip(ip):
            raise ValueError("禁止访问内网、回环或 metadata 地址")
        return url
    except ValueError as exc:
        if "禁止访问" in str(exc):
            raise

    try:
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ValueError(f"域名解析失败: {host}") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if _is_blocked_ip(ip):
            raise ValueError("禁止访问解析到内网、回环或 metadata 地址的域名")

    return url
