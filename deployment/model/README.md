# Approved local model artifact

The release builder deliberately does not download a model. Model selection depends on the company's approved licence and the target host's CPU, RAM, GPU and latency requirements.

Before building a complete release, place these files in this directory:

- `model.gguf` — the approved GGUF artifact.
- `model.sha256` — one line in the form `<sha256>  model.gguf`.
- `MODEL-LICENSE.txt` — the exact licence or legally approved licence notice for this artifact.
- `model-source.json` — source URL, original filename, model/version, quantisation, expected RAM, licence identifier, approval owner and approval date.
- `Modelfile` — the Ollama import definition. The provided file uses the local `model.gguf`.

Run `deployment/scripts/import-model.ps1` after loading the release images. The importer verifies the checksum and refuses to create an Ollama model when any required record is missing.

The configured Ollama tag defaults to `oraclex-approved:1`. Keep `.env`, `model-source.json` and the tag in the `Modelfile` consistent for every release.
