"""Destination validation. The validated numeric IP is the connection target."""

import asyncio, socket, httpx
from ipaddress import IPv6Address, ip_address, ip_network


from access_kit.safe_fetch.errors import BlockedDestination

# Reject IPv6 transition mechanisms that can embed otherwise blocked IPv4 IPs.
_TRANSITION = tuple(ip_network(cidr) for cidr in ("64:ff9b::/96", "64:ff9b:1::/48", "2001::/32", "2002::/16"))


def is_public_ip(value: str) -> bool:
    """Return True only for unscoped, unicast, globally reachable literals."""
    if "%" in value:
        return False
    try:
        address = ip_address(value)
    except ValueError:
        return False
    if isinstance(address, IPv6Address):
        if address.ipv4_mapped is not None or any(address in network for network in _TRANSITION):
            return False
    return address.is_global and not address.is_multicast and not address.is_reserved


def validate_url(value: str | httpx.URL) -> httpx.URL:
    """Permit HTTP(S), no credentials, only standard web ports, no local names."""
    text = str(value)
    if len(text) > 8192 or any(ord(char) <= 32 or ord(char) == 127 or char == "\\" for char in text):
        raise BlockedDestination("invalid URL characters or length")
    try:
        url = httpx.URL(value)
        port = url.port
    except (httpx.InvalidURL, ValueError):
        raise BlockedDestination("invalid URL") from None
    hostname = url.host.rstrip(".").lower()
    if url.scheme not in {"http", "https"} or not hostname or "%" in hostname or url.userinfo or (port is not None and port not in {80, 443}):
        raise BlockedDestination("URL scheme, credentials, host or port is not permitted")
    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        raise BlockedDestination("local hostnames are not permitted")
    return url.copy_with(fragment=None)


async def resolve_public(hostname: str, port: int) -> str:
    """Resolve once; reject the entire answer if ANY address is non-public."""
    try:
        ip_address(hostname)
    except ValueError:
        try:
            answers = await asyncio.get_running_loop().getaddrinfo(hostname, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        except OSError:
            raise BlockedDestination("destination could not be resolved") from None
        addresses = list(dict.fromkeys(str(answer[4][0]) for answer in answers))
    else:
        addresses = [hostname]
    if not addresses or not all(is_public_ip(address) for address in addresses):
        raise BlockedDestination("destination contains a non-public address")
    return addresses[0]
