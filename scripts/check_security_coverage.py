"""Fail CI unless security modules have complete line and branch coverage."""

import argparse
import json
from pathlib import Path

CRITICAL_FILES = (
    "python/src/access_kit/logging.py",
    "python/src/access_kit/privacy.py",
    "python/src/access_kit/session.py",
    "python/src/access_kit/safe_fetch/fetcher.py",
    "python/src/access_kit/safe_fetch/ipcheck.py",
)


def coverage_gaps(report: dict) -> list[str]:
    files = report.get("files", {})
    gaps = []
    for name in CRITICAL_FILES:
        summary = files.get(name, {}).get("summary", {})
        if not summary or summary.get("missing_lines") != 0 or summary.get("missing_branches") != 0 or summary.get("excluded_lines") != 0:
            gaps.append(name)
    return gaps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    gaps = coverage_gaps(json.loads(args.report.read_text()))
    if gaps:
        print("Security coverage must be 100% for: " + ", ".join(gaps))
        return 1
    print("Security coverage: 100% of lines and branches; no excluded lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
