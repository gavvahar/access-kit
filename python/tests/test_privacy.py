"""Socket-peer trust and pseudonymous IP hashing regressions."""

import hashlib
import hmac

import pytest
from starlette.requests import Request

from access_kit.privacy import canonical_ip, client_ip, hash_ip


def request(peer="203.0.113.10", headers=()):
    return Request({"type": "http", "client": (peer, 123) if peer is not None else None, "headers": list(headers)})


@pytest.mark.parametrize("raw,expected", [("2001:4860:4860:0000::8888", "2001:4860:4860::8888"), ("::ffff:192.0.2.1", "192.0.2.1"), ("8.8.8.8", "8.8.8.8")])
def test_address_canonicalization(raw, expected):
    assert canonical_ip(raw) == expected


@pytest.mark.parametrize("value", ["bad", "fe80::1%eth0", "127.1", ""])
def test_invalid_literals(value):
    with pytest.raises(ValueError):
        canonical_ip(value)


def test_hash_is_hmac_and_salt_rotation_unlinks():
    salt = "s" * 32
    expected = hmac.new(salt.encode(), b"192.0.2.1", hashlib.sha256).hexdigest()
    assert hash_ip("192.0.2.1", salt) == expected
    assert hash_ip("::ffff:192.0.2.1", salt) == expected
    assert hash_ip("192.0.2.1", "other-salt" * 4) != expected
    with pytest.raises(ValueError):
        hash_ip("8.8.8.8", "short")


@pytest.mark.parametrize(
    "trust,proxies,expected", [(False, (), "203.0.113.10"), (True, (), "203.0.113.10"), (True, ("198.51.100.0/24",), "203.0.113.10"), (True, ("203.0.113.0/24",), "8.8.8.8")]
)
def test_cloudflare_requires_opt_in_and_trusted_peer(trust, proxies, expected):
    req = request(headers=[(b"cf-connecting-ip", b"8.8.8.8"), (b"x-forwarded-for", b"1.1.1.1")])
    assert client_ip(req, trust_cloudflare=trust, trusted_proxies=proxies) == expected


@pytest.mark.parametrize("headers", [[], [(b"cf-connecting-ip", b"invalid")], [(b"cf-connecting-ip", b"8.8.8.8"), (b"cf-connecting-ip", b"1.1.1.1")]])
def test_invalid_proxy_header_falls_back_to_peer(headers):
    assert client_ip(request(headers=headers), trust_cloudflare=True, trusted_proxies=("203.0.113.0/24",)) == "203.0.113.10"


@pytest.mark.parametrize("peer", [None, "not-an-ip"])
def test_unknown_peer(peer):
    assert client_ip(request(peer)) is None
