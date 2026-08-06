"""ORM models package.

Importing the models here ensures they are registered on ``Base.metadata``
before Alembic autogeneration or ``create_all`` runs.
"""

from app.models.datapoint import DataPoint
from app.models.user import User, UserRole

__all__ = ["DataPoint", "User", "UserRole"]
