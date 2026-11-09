from __future__ import annotations

import email
import json
import sys
import zipfile
from pathlib import Path


def python_inventory(wheelhouse: Path) -> list[dict[str, str]]:
    records: dict[tuple[str, str], dict[str, str]] = {}
    for wheel in sorted(wheelhouse.glob("*.whl")):
        with zipfile.ZipFile(wheel) as archive:
            metadata_name = next(
                (name for name in archive.namelist() if name.endswith(".dist-info/METADATA")),
                None,
            )
            if not metadata_name:
                continue
            metadata = email.message_from_bytes(archive.read(metadata_name))
            name = metadata.get("Name", wheel.stem)
            version = metadata.get("Version", "unknown")
            licence = str(metadata.get("License-Expression") or metadata.get("License") or "SEE PACKAGE METADATA")
            source = metadata.get("Home-page") or "https://pypi.org/project/" + name + "/" + version + "/"
            records[(name.lower(), version)] = {
                "name": name,
                "version": version,
                "licence": " ".join(licence.split())[:500],
                "source": source,
                "artifact": wheel.name,
            }
    return sorted(records.values(), key=lambda item: item["name"].lower())


def npm_inventory(node_modules: Path) -> list[dict[str, str]]:
    records: dict[tuple[str, str], dict[str, str]] = {}
    for package_json in node_modules.rglob("package.json"):
        if ".bin" in package_json.parts:
            continue
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        name = data.get("name")
        version = data.get("version")
        if not name or not version:
            continue
        licence = data.get("license") or data.get("licenses") or "SEE PACKAGE METADATA"
        if isinstance(licence, (dict, list)):
            licence = json.dumps(licence, sort_keys=True)
        repository = data.get("repository") or data.get("homepage") or "https://www.npmjs.com/package/" + name
        if isinstance(repository, dict):
            repository = repository.get("url", str(repository))
        records[(name, version)] = {
            "name": name,
            "version": version,
            "licence": str(licence),
            "source": str(repository),
        }
    return sorted(records.values(), key=lambda item: item["name"].lower())


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: generate-dependency-inventory.py WHEELHOUSE NODE_MODULES OUTPUT")
    output = {
        "schema_version": 1,
        "python": python_inventory(Path(sys.argv[1])),
        "npm": npm_inventory(Path(sys.argv[2])),
    }
    Path(sys.argv[3]).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
