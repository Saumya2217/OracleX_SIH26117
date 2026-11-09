from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.company import User
from app.services.retrieval import RetrievalMode, RetrievalService
from app.services.vector_store import vector_store_service


DEFAULT_CASES = Path(__file__).resolve().parents[2] / "evaluation" / "retrieval_cases.json"


def load_cases(path: Path = DEFAULT_CASES) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def evaluate_cases(db: Session, cases: list[dict[str, Any]], mode: RetrievalMode) -> dict[str, Any]:
    details = []
    answerable_total = answerable_hit = 0
    abstention_total = abstention_hit = 0
    access_total = access_hit = 0
    for case in cases:
        user = db.query(User).filter(User.email == case["user_email"]).one()
        results = RetrievalService.retrieve(db, user, case["query"], limit=5, mode=mode)
        titles = [item["title"] for item in results]
        expected_title = case.get("expected_document_title")
        forbidden_title = case.get("forbidden_document_title")
        if case["expected_answerable"]:
            answerable_total += 1
            passed = bool(expected_title and any(expected_title in title for title in titles))
            answerable_hit += int(passed)
            category = "answerable"
        else:
            abstention_total += 1
            passed = len(results) == 0
            abstention_hit += int(passed)
            category = "unanswerable"
        if forbidden_title:
            access_total += 1
            access_passed = not any(forbidden_title in title for title in titles)
            access_hit += int(access_passed)
            passed = passed and access_passed
        details.append({
            "id": case["id"],
            "category": category,
            "passed": passed,
            "retrieved_titles": titles,
            "expected_document_title": expected_title,
            "forbidden_document_title": forbidden_title,
        })
    return {
        "mode": mode,
        "case_count": len(cases),
        "answerable_recall_at_5": answerable_hit / answerable_total if answerable_total else 1.0,
        "abstention_accuracy": abstention_hit / abstention_total if abstention_total else 1.0,
        "access_control_accuracy": access_hit / access_total if access_total else 1.0,
        "passed_cases": sum(1 for item in details if item["passed"]),
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate OracleX retrieval without network access.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = load_cases(args.cases)
    db = SessionLocal()
    try:
        results = {mode: evaluate_cases(db, cases, mode) for mode in ("lexical", "vector", "hybrid")}
    finally:
        db.close()
    hybrid = results["hybrid"]
    gates = {
        "answerable_recall_at_5": 0.90,
        "abstention_accuracy": 0.95,
        "access_control_accuracy": 1.0,
    }
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Synthetic development evaluation using bundled NovaWorks fixtures; not a company-pilot acceptance result.",
        "corpus": "backend/evaluation/retrieval_cases.json" if args.cases == DEFAULT_CASES else str(args.cases),
        "embedding": {
            "model": vector_store_service.EMBEDDING_MODEL,
            "dimensions": vector_store_service.EMBEDDING_DIMENSIONS,
            "network_required": False,
        },
        "acceptance_gates": gates,
        "hybrid_gate_passed": (
            hybrid["answerable_recall_at_5"] >= gates["answerable_recall_at_5"]
            and hybrid["abstention_accuracy"] >= gates["abstention_accuracy"]
            and hybrid["access_control_accuracy"] >= gates["access_control_accuracy"]
        ),
        "results": results,
    }
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
