from __future__ import annotations

import email
import hashlib
import sys
import zipfile
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: generate-python-lock.py WHEELHOUSE OUTPUT")
    wheelhouse = Path(sys.argv[1])
    output = Path(sys.argv[2])
    packages: dict[str, tuple[str, str]] = {}

    for wheel in sorted(wheelhouse.glob("*.whl")):
        with zipfile.ZipFile(wheel) as archive:
            metadata_name = next(
                (name for name in archive.namelist() if name.endswith(".dist-info/METADATA")),
                None,
            )
            if metadata_name is None:
                raise RuntimeError(f"No package metadata in {wheel.name}")
            metadata = email.message_from_bytes(archive.read(metadata_name))
        name = metadata["Name"]
        version = metadata["Version"]
        key = name.lower().replace("_", "-")
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        existing = packages.get(key)
        if existing and existing[0] != version:
            raise RuntimeError(f"Multiple versions found for {name}: {existing[0]} and {version}")
        packages[key] = (version, digest)

    lines = [
        "# Generated for OracleX linux/amd64, CPython 3.11.",
        "# Refresh only through the controlled Milestone 03 release workflow.",
        "--only-binary=:all:",
        "",
    ]
    for name in sorted(packages):
        version, digest = packages[name]
        lines.append(f"{name}=={version} --hash=sha256:{digest}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
