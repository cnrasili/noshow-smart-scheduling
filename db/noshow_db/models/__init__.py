# Import all model modules so Alembic sees every table
from noshow_db.models import admin, core, dataset, service

__all__ = ["admin", "core", "dataset", "service"]
