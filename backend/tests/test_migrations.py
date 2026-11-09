from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.config import settings


BACKEND_DIR = Path(__file__).resolve().parents[1]
BUSINESS_TABLES = {
    "companies",
    "departments",
    "roles",
    "users",
    "workflows",
    "adaptation_proposals",
    "approval_requests",
    "audit_logs",
    "documents",
    "feedback_records",
    "tasks",
    "document_chunks",
    "document_versions",
    "ingestion_jobs",
    "outbox_events",
    "service_heartbeats",
    "conversations",
    "conversation_messages",
    "agent_runs",
    "agent_run_citations",
    "business_requests",
    "business_request_versions",
    "business_request_events",
    "internal_notifications",
}


def migration_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


def test_initial_migration_upgrade_check_and_reapply(tmp_path, monkeypatch):
    database_path = tmp_path / "migration-test.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)
    config = migration_config()

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        assert BUSINESS_TABLES <= set(inspect(engine).get_table_names())
        expected_head = ScriptDirectory.from_config(config).get_current_head()
        with engine.connect() as connection:
            current_head = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert current_head == expected_head

        # Fails if the ORM metadata and migration history have drifted apart.
        command.check(config)

        command.downgrade(config, "base")
        assert not (BUSINESS_TABLES & set(inspect(engine).get_table_names()))

        # Prove the history can be applied cleanly again after rollback.
        command.upgrade(config, "head")
        assert BUSINESS_TABLES <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_repairs_earlier_m06_conversation_table(tmp_path, monkeypatch):
    database_path = tmp_path / "earlier-m06.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)
    config = migration_config()
    command.upgrade(config, "b7d2c4e91f60")

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE conversations DROP COLUMN retention_until"))
            connection.execute(text("ALTER TABLE conversations DROP COLUMN next_sequence"))
        command.upgrade(config, "head")
        columns = {column["name"] for column in inspect(engine).get_columns("conversations")}
        assert {"retention_until", "next_sequence"} <= columns
        command.check(config)
    finally:
        engine.dispose()
