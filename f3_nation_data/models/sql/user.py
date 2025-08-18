"""Auto-generated SQLAlchemy model for users table.

This file was automatically generated from the F3 Nation database schema.
Generated on: 2025-08-18 22:17:51 UTC

DO NOT EDIT MANUALLY - Use dev_utilities/generate_models.py to regenerate.
Auto-formatted with toolbelt for consistent code style.
"""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SqlUserModel(Base):
    """SQLAlchemy model for users table.

    Auto-generated from F3 Nation database schema.

    Table: users
    Primary Key: ['user_id']
    """

    __tablename__ = 'users'

    user_id: Mapped[str] = mapped_column(
        sa.String(45),
        primary_key=True,
        nullable=False,
    )

    user_name: Mapped[str] = mapped_column(
        sa.String(45),
        nullable=False,
    )

    real_name: Mapped[str] = mapped_column(
        sa.String(45),
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(
        sa.String(45),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        sa.String(45),
        nullable=True,
    )

    start_date: Mapped[Any | None] = mapped_column(
        sa.DATE,
        nullable=True,
    )

    app: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
    )

    json: Mapped[dict[str, Any] | None] = mapped_column(
        sa.JSON,
        nullable=True,
    )

    def __repr__(self) -> str:
        """Return string representation of the model."""
        return f'<SqlUserModel({self.user_id})>'
