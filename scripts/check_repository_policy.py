"""Validate repository identity and HACS publication invariants."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_REPOSITORY = "Trusties13/sourdough-manager"
EXPECTED_DOMAIN = "sourdough_manager"
EXPECTED_NAME = "Sourdough Manager"
REQUIRED_MANIFEST_KEYS = {
    "codeowners",
    "documentation",
    "domain",
    "issue_tracker",
    "name",
    "version",
}
REQUIRED_FILES = {
    ROOT / "hacs.json",
    ROOT / "brand" / "icon.png",
    ROOT / "custom_components" / EXPECTED_DOMAIN / "brand" / "icon.png",
}


def _read_json(path: Path) -> dict[str, object]:
    """Read a JSON object from a repository file."""
    with path.open(encoding="utf-8") as file_handle:
        value = json.load(file_handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def main() -> None:
    """Check repository invariants required for supported releases."""
    failures: list[str] = []

    github_repository = os.environ.get("GITHUB_REPOSITORY")
    if github_repository and github_repository != EXPECTED_REPOSITORY:
        failures.append(
            f"Repository identity changed: expected {EXPECTED_REPOSITORY}, "
            f"found {github_repository}"
        )

    integration_root = ROOT / "custom_components"
    integrations = sorted(
        path.name for path in integration_root.iterdir() if path.is_dir()
    )
    if integrations != [EXPECTED_DOMAIN]:
        failures.append(
            f"Expected only custom_components/{EXPECTED_DOMAIN}; found {integrations}"
        )

    manifest_path = integration_root / EXPECTED_DOMAIN / "manifest.json"
    manifest = _read_json(manifest_path)
    missing_keys = sorted(REQUIRED_MANIFEST_KEYS - manifest.keys())
    if missing_keys:
        failures.append(f"manifest.json is missing required keys: {missing_keys}")
    if manifest.get("domain") != EXPECTED_DOMAIN:
        failures.append(f"Integration domain must remain {EXPECTED_DOMAIN}")
    if manifest.get("name") != EXPECTED_NAME:
        failures.append(f"Integration name must remain {EXPECTED_NAME}")
    if manifest.get("codeowners") != ["@Trusties13"]:
        failures.append("Integration ownership must remain assigned to @Trusties13")
    if manifest.get("documentation") != f"https://github.com/{EXPECTED_REPOSITORY}":
        failures.append(
            "Integration documentation URL no longer matches the repository"
        )
    if manifest.get("issue_tracker") != (
        f"https://github.com/{EXPECTED_REPOSITORY}/issues"
    ):
        failures.append("Integration issue tracker no longer matches the repository")

    hacs_manifest = _read_json(ROOT / "hacs.json")
    if hacs_manifest.get("name") != EXPECTED_NAME:
        failures.append(f"hacs.json name must remain {EXPECTED_NAME}")

    for path in sorted(REQUIRED_FILES):
        if not path.is_file() or path.stat().st_size == 0:
            relative_path = path.relative_to(ROOT)
            failures.append(f"Required file is missing or empty: {relative_path}")

    if failures:
        raise SystemExit("Repository policy failed:\n- " + "\n- ".join(failures))

    print("Repository policy passed")


if __name__ == "__main__":
    main()
