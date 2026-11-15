"""Package policy and security CI must hold independently of implementation."""

import runpy
from pathlib import Path

import access_kit


def test_all_package_initializers_are_empty():
    root = Path(access_kit.__file__).parent
    assert all(path.read_bytes() == b"" for path in root.rglob("__init__.py"))


def test_security_coverage_gate_rejects_missing_lines_branches_and_exclusions():
    checker = runpy.run_path("scripts/check_security_coverage.py")
    names = checker["CRITICAL_FILES"]
    report = {"files": {name: {"summary": {"missing_lines": 0, "missing_branches": 0, "excluded_lines": 0}} for name in names}}
    check = checker["coverage_gaps"]
    assert check(report) == []
    for field in ("missing_lines", "missing_branches", "excluded_lines"):
        report["files"][names[0]]["summary"][field] = 1
        assert check(report) == [names[0]]
        report["files"][names[0]]["summary"][field] = 0
    assert check({}) == list(names)
