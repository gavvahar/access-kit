"""Historical fixture exceptions cannot hide new or verified credentials."""

from copy import deepcopy
import json
import runpy
from types import SimpleNamespace

import pytest


@pytest.fixture
def scanner():
    return runpy.run_path("scripts/scan_secrets.py")


@pytest.fixture
def historical_finding(scanner):
    commit, file, raw = next(iter(scanner["HISTORICAL_FIXTURES"]))
    return {"Verified": False, "DetectorName": "URI", "Raw": raw, "SourceMetadata": {"Data": {"Git": {"commit": commit, "file": file}}}}


def test_only_exact_historical_fixture_can_be_recognized(scanner, historical_finding):
    check = scanner["is_historical_fixture"]
    assert check(historical_finding)
    for key, value in (("Verified", True), ("Raw", "different-credential"), ("DetectorName", "AWS")):
        modified = deepcopy(historical_finding)
        modified[key] = value
        assert not check(modified)
    for key in ("commit", "file"):
        modified = deepcopy(historical_finding)
        modified["SourceMetadata"]["Data"]["Git"][key] = "different"
        assert not check(modified)
    assert not check({})


@pytest.mark.parametrize("code,output,expected", [(0, "", 0), (183, "", 1), (2, "", 1), (0, "invalid-json", 1), (0, "[]", 1), (183, '{"Verified":true}', 1)])
def test_scanner_fails_closed(scanner, monkeypatch, code, output, expected):
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=code, stdout=output))
    assert scanner["main"]() == expected


def test_scanner_accepts_known_fixture_but_never_leaks_it(scanner, historical_finding, monkeypatch, capsys):
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=183, stdout=json.dumps(historical_finding)))
    assert scanner["main"]() == 0
    assert historical_finding["Raw"] not in capsys.readouterr().out


def test_missing_docker_fails(scanner, monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("docker")

    monkeypatch.setattr("subprocess.run", missing)
    assert scanner["main"]() == 1
