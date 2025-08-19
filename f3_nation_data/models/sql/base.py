from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models.

    All SQLAlchemy models should inherit from this class.
    It provides the base functionality for the models.
    """
