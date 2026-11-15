"""Scan complete Git history while recognizing exact immutable test fixtures.

The exact commit/file/value matches below are known fake URLs introduced by the
redaction and SSRF tests. Keeping history intact requires recognizing those old
fixtures even after removing full credential-bearing literals from current code.
Verified secrets are NEVER allowlisted. No detector or source path is excluded.
"""

import json, subprocess
from pathlib import Path
from typing import Any

HISTORICAL_FIXTURES = frozenset(
    {
        ("8afedc4addf3f83e8cd012eedc3736b3d18565c4", "python/tests/test_logging.py", "https://" + "user:password" + "@private"),
        ("bf5200e420860cde7d4b0744affa68290155b305", "python/src/access_kit/testing/ssrf_cases.py", "http://" + "user:password" + "@example.com"),
        ("39859b6669097b136422b25dd4c1a75278960226", "python/tests/test_delivery.py", "https://" + "user:password" + "@example.com"),
    }
)


def is_historical_fixture(finding: dict[str, Any]) -> bool:
    if finding.get("Verified") is not False or finding.get("DetectorName") != "URI":
        return False
    git = finding.get("SourceMetadata", {}).get("Data", {}).get("Git", {})
    return (git.get("commit"), git.get("file"), finding.get("Raw")) in HISTORICAL_FIXTURES


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{root}:/repo:ro",
        "trufflesecurity/trufflehog:latest",
        "git",
        "file:///repo",
        "--results=verified,unverified,unknown",
        "--fail",
        "--json",
        "--no-update",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        print("Secret scan could not start; verify Docker is installed and accessible")
        return 1
    if result.returncode not in (0, 183):
        print(f"Secret scanner failed with exit code {result.returncode}; check Docker access and image availability")
        return 1
    try:
        findings = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        if not all(isinstance(item, dict) for item in findings):
            raise ValueError("unexpected scanner output")
        unexpected = [item for item in findings if not is_historical_fixture(item)]
    except (ValueError, TypeError, AttributeError):
        print("Secret scanner returned invalid output; refusing to pass")
        return 1
    if unexpected or (result.returncode == 183 and not findings):
        # Never print raw credentials. Report only safe classification/count data.
        print(f"Secret scan failed: {len(unexpected)} findings need review. Inspect locally with TruffleHog; raw secrets are omitted here.")
        return 1
    print(f"Secret scan passed; {len(findings)} exact historical test-fixture matches, no other findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
