"""Auto-generated SQLAlchemy model for aos table.

This file was automatically generated from the F3 Nation database schema.
Generated on: 2025-08-18 22:17:51 UTC

DO NOT EDIT MANUALLY - Use dev_utilities/generate_models.py to regenerate.
Auto-formatted with toolbelt for consistent code style.
"""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SqlAOModel(Base):
    """SQLAlchemy model for aos table.

    Auto-generated from F3 Nation database schema.

    Table: aos
    Primary Key: ['channel_id']
    """

    __tablename__ = 'aos'

    channel_id: Mapped[str] = mapped_column(
        sa.String(45),
        primary_key=True,
        nullable=False,
    )

    ao: Mapped[str] = mapped_column(
        sa.String(45),
        nullable=False,
    )

    channel_created: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )

    archived: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
    )

    backblast: Mapped[bool | None] = mapped_column(
        sa.Boolean,
        nullable=True,
    )

    def __repr__(self) -> str:
        """Return string representation of the model."""
        return f'<SqlAOModel({self.channel_id})>'
