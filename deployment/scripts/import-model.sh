#!/bin/sh
set -eu

required="/models/model.gguf /models/model.sha256 /models/MODEL-LICENSE.txt /models/model-source.json /models/Modelfile"
for item in $required; do
  if [ ! -s "$item" ]; then
    echo "Required approved model artifact is missing or empty: $item" >&2
    exit 2
  fi
done

cd /models
sha256sum -c model.sha256

case "${OLLAMA_DEFAULT_MODEL:-}" in
  ""|*:latest)
    echo "OLLAMA_DEFAULT_MODEL must be an explicit non-latest tag." >&2
    exit 2
    ;;
esac

echo "Importing verified local model as ${OLLAMA_DEFAULT_MODEL}"
ollama create "${OLLAMA_DEFAULT_MODEL}" -f /models/Modelfile
ollama show "${OLLAMA_DEFAULT_MODEL}" >/dev/null
echo "Local model import complete."
