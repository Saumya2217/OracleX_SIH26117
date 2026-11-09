import json
import re
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_compose_is_pinned_and_network_is_internal():
    compose_text = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)

    assert compose["networks"]["private"]["internal"] is True
    assert "ollama-init" not in compose["services"]
    assert "worker" in compose["services"]
    assert compose["services"]["worker"]["command"] == ["python", "-m", "app.workers.ingestion"]
    assert compose["services"]["backend"]["environment"]["WORKER_REQUIRED_FOR_READINESS"] == "true"
    assert "ollama pull" not in compose_text.lower()
    chroma = compose["services"]["chroma"]
    assert chroma["image"] == compose["services"]["backend"]["image"]
    assert "ports" not in chroma
    assert chroma["volumes"] == ["backend_chroma:/app/data/chromadb"]
    for name in ("backend", "worker"):
        service = compose["services"][name]
        assert service["environment"]["CHROMA_HOST"] == "chroma"
        assert service["depends_on"]["chroma"]["condition"] == "service_healthy"
        assert not any("backend_chroma" in volume for volume in service["volumes"])

    for name, service in compose["services"].items():
        image = service.get("image")
        assert image, f"{name} must use a prebuilt image"
        assert ":latest" not in image
        assert re.search(r":[0-9]+(?:\.[0-9]+)+", image), f"{name} image is not version-pinned: {image}"
        assert service.get("pull_policy") == "never"
        assert service.get("networks") == ["private"]


def test_production_frontend_contains_no_package_install():
    dockerfile = (PROJECT_ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8").lower()
    assert "npm " not in dockerfile
    assert "node:" not in dockerfile
    assert "copy dist " in dockerfile


def test_python_lock_is_exact_and_hash_verified():
    lock_lines = [
        line.strip()
        for line in (PROJECT_ROOT / "backend" / "requirements.lock").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#") and not line.startswith("--")
    ]
    assert len(lock_lines) >= 50
    for line in lock_lines:
        assert re.match(r"^[a-z0-9][a-z0-9._-]*==[^ ]+ --hash=sha256:[0-9a-f]{64}$", line), line


def test_frontend_direct_dependencies_are_exact():
    package = json.loads((PROJECT_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    versions = {**package["dependencies"], **package["devDependencies"]}
    assert versions
    assert all(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", version) for version in versions.values())


def test_release_tooling_requires_model_provenance_and_recovery_commands():
    scripts = PROJECT_ROOT / "deployment" / "scripts"
    required_scripts = {
        "build-release.ps1",
        "verify-release.ps1",
        "install.ps1",
        "import-model.ps1",
        "start.ps1",
        "stop.ps1",
        "backup.ps1",
        "restore.ps1",
        "update.ps1",
        "rollback.ps1",
        "diagnostics.ps1",
        "test-network-isolation.ps1",
    }
    assert required_scripts.issubset({item.name for item in scripts.iterdir()})

    importer = (scripts / "import-model.sh").read_text(encoding="utf-8")
    for required in ("model.gguf", "model.sha256", "MODEL-LICENSE.txt", "model-source.json", "Modelfile"):
        assert required in importer
    assert "sha256sum -c" in importer
