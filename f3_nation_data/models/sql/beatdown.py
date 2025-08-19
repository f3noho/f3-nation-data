"""Auto-generated SQLAlchemy model for beatdowns table.

This file was automatically generated from the F3 Nation database schema.
Generated on: 2025-08-18 22:17:51 UTC

DO NOT EDIT MANUALLY - Use dev_utilities/generate_models.py to regenerate.
Auto-formatted with toolbelt for consistent code style.
"""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SqlBeatDownModel(Base):
    """SQLAlchemy model for beatdowns table.

    Auto-generated from F3 Nation database schema.

    Table: beatdowns
    Primary Key: ['ao_id', 'bd_date', 'q_user_id']
    """

    __tablename__ = 'beatdowns'

    timestamp: Mapped[str | None] = mapped_column(
        sa.String(45),
        nullable=True,
    )

    ts_edited: Mapped[str | None] = mapped_column(
        sa.String(45),
        nullable=True,
    )

    ao_id: Mapped[str] = mapped_column(
        sa.String(45),
        primary_key=True,
        nullable=False,
    )

    bd_date: Mapped[Any] = mapped_column(
        sa.DATE,
        primary_key=True,
        nullable=False,
    )

    q_user_id: Mapped[str] = mapped_column(
        sa.String(45),
        primary_key=True,
        nullable=False,
    )

    coq_user_id: Mapped[str | None] = mapped_column(
        sa.String(45),
        nullable=True,
    )

    pax_count: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
    )

    backblast: Mapped[str | None] = mapped_column(
        LONGTEXT,
        nullable=True,
    )

    backblast_parsed: Mapped[str | None] = mapped_column(
        LONGTEXT,
        nullable=True,
    )

    fngs: Mapped[str | None] = mapped_column(
        sa.String(45),
        nullable=True,
    )

    fng_count: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
    )

    json: Mapped[dict[str, Any] | None] = mapped_column(
        sa.JSON,
        nullable=True,
    )

    def __repr__(self) -> str:
        """Return string representation of the model."""
        return f'<SqlBeatDownModel(ao_id={self.ao_id}, bd_date={self.bd_date}, q_user_id={self.q_user_id})>'
