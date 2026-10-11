from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import get_settings


def _ensure_alembic_version_column_capacity() -> None:
    """Make room for revision ids longer than Alembic's default VARCHAR(32).

    Alembic creates ``alembic_version.version_num`` as VARCHAR(32) on first
    use, which is shorter than some revision ids here. PostgreSQL enforces the
    length, so the table is created wide up front on a fresh database and
    widened on an existing one.
    """

    engine = create_engine(get_settings().database_url)
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(128) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
                """
            )
        )
        connection.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"))


def run_alembic_upgrade_head() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    alembic_ini = root_dir / "alembic.ini"
    _ensure_alembic_version_column_capacity()
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(root_dir / "app" / "db" / "migrations"))
    config.set_main_option("prepend_sys_path", str(root_dir))
    command.upgrade(config, "head")
