"""Generate a checked-in TypeScript view of the backend OpenAPI schemas."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
TARGET = BACKEND.parent / "frontend" / "src" / "types" / "openapi.generated.ts"


def ts_type(schema: dict) -> str:
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return f"ApiSchemas[{json.dumps(name)}]"
    if "enum" in schema:
        return " | ".join(json.dumps(value, ensure_ascii=False) for value in schema["enum"])
    if "const" in schema:
        return json.dumps(schema["const"], ensure_ascii=False)
    for composite, separator in (("anyOf", " | "), ("oneOf", " | "), ("allOf", " & ")):
        if composite in schema:
            return separator.join(f"({ts_type(part)})" for part in schema[composite])
    kind = schema.get("type")
    if isinstance(kind, list):
        return " | ".join(ts_type({**schema, "type": part}) for part in kind)
    if kind == "array":
        return f"Array<{ts_type(schema.get('items', {}))}>"
    if kind == "object" or "properties" in schema or "additionalProperties" in schema:
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        fields = " ".join(
            f"{json.dumps(name, ensure_ascii=False)}{'?' if name not in required else ''}: {ts_type(value)};"
            for name, value in properties.items()
        )
        object_type = "{ " + fields + " }" if properties else None
        additional = schema.get("additionalProperties")
        if additional is not None and additional is not False:
            value_type = ts_type(additional) if isinstance(additional, dict) else "unknown"
            record = f"Record<string, {value_type}>"
            return f"({object_type} & {record})" if object_type else record
        return object_type or "Record<string, unknown>"
    if kind in ("integer", "number"):
        return "number"
    if kind == "string":
        return "Blob" if schema.get("format") == "binary" else "string"
    if kind == "boolean":
        return "boolean"
    if kind == "null":
        return "null"
    return "unknown"


def render(openapi: dict) -> str:
    spec = json.dumps(openapi, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(spec).hexdigest()
    schemas = openapi["components"]["schemas"]
    lines = [
        "// Generated from backend FastAPI OpenAPI. Do not edit by hand.",
        f"// OpenAPI SHA-256: {digest}",
        "export interface ApiSchemas {",
    ]
    for name in sorted(schemas):
        lines.append(f"  {json.dumps(name)}: {ts_type(schemas[name])};")
    lines.extend(["}", "", "export type ApiSchema<Name extends keyof ApiSchemas> = ApiSchemas[Name];", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the checked-in file differs")
    args = parser.parse_args()

    temporary = Path(tempfile.mkdtemp(prefix="oraclex-openapi-"))
    try:
        os.environ["SECRET_KEY"] = "contract-generation-only-secret-key-32chars"
        os.environ["TESTING"] = "true"
        os.environ["CHROMA_HOST"] = ""
        os.environ["CHROMA_PERSIST_DIR"] = str(temporary / "chroma")
        os.environ["UPLOAD_DIR"] = str(temporary / "uploads")
        sys.path.insert(0, str(BACKEND))
        from app.main import app

        generated = render(app.openapi())
        if args.check:
            if not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != generated:
                print(f"OpenAPI types are out of date: {TARGET}", file=sys.stderr)
                return 1
            print(f"OpenAPI types match: {TARGET}")
            return 0
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(generated, encoding="utf-8")
        print(f"Generated {len(app.openapi()['components']['schemas'])} schemas: {TARGET}")
        return 0
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
