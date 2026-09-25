# Import all model modules so Alembic sees every table
from noshow_db.models import core, service

__all__ = ["core", "service"]
