"""Canonical client addresses and keyed, irreversible IP identifiers."""

import hashlib, hmac
from collections.abc import Iterable
from ipaddress import ip_address, ip_network

from starlette.requests import Request


def canonical_ip(value: str) -> str:
    """Normalize IP literals, including IPv4-mapped IPv6; reject zone IDs."""
    if "%" in value:
        raise ValueError("scoped IP addresses are not supported")
    address = ip_address(value)
    return str(getattr(address, "ipv4_mapped", None) or address)


def client_ip(request: Request, *, trust_cloudflare: bool = False, trusted_proxies: Iterable[str] = ()) -> str | None:
    """Use CF-Connecting-IP only from an explicitly trusted socket peer.

    Do not enable a server's unconditional forwarded-header rewriting: the peer
    checked here must still be the actual proxy connection, not a claimed client.
    Invalid or duplicate CF headers fall back to the verified peer address.
    """
    if request.client is None:
        return None
    try:
        peer = canonical_ip(request.client.host)
    except ValueError:
        return None
    if trust_cloudflare and any(ip_address(peer) in ip_network(cidr) for cidr in trusted_proxies):
        headers = request.headers.getlist("cf-connecting-ip")
        if len(headers) == 1:
            try:
                return canonical_ip(headers[0])
            except ValueError:
                pass
    return peer


def hash_ip(value: str, salt: str) -> str:
    """HMAC-SHA256 of a canonical IP. Rotate the application-owned salt to unlink."""
    if len(salt.encode()) < 32:
        raise ValueError("IP hash salt must contain at least 32 bytes")
    return hmac.new(salt.encode(), canonical_ip(value).encode(), hashlib.sha256).hexdigest()
