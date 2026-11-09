from __future__ import annotations

import argparse
import json

from app.database import SessionLocal
from app.services.ingestion import IngestionService


def main() -> None:
    parser = argparse.ArgumentParser(description="Check or repair OracleX document/index consistency.")
    parser.add_argument("--repair", action="store_true", help="Repair safe index inconsistencies.")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        report = IngestionService.reconcile(db, repair=args.repair)
        print(json.dumps(report, indent=2))
        unresolved = [issue for issue in report["issues"] if not issue["repaired"]]
        if unresolved:
            raise SystemExit(2)
    finally:
        db.close()


if __name__ == "__main__":
    main()
