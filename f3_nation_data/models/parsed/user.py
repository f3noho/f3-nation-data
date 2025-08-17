from pydantic import BaseModel


class ParsedUser(BaseModel):
    """Parsed and enriched user model for application use.

    This model represents a user with additional computed fields and
    metadata for easier application usage.
    """

    # Core user identifiers (from SQL model)
    user_id: str
    user_name: str
    real_name: str
    phone: str | None = None
    email: str | None = None
    start_date: str | None = None
    app: bool = False
