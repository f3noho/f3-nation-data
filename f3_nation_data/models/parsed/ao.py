from pydantic import BaseModel


class ParsedAO(BaseModel):
    """Parsed and enriched AO model for application use.

    This model represents an AO (workout location) with additional
    computed fields and metadata for easier application usage.
    """

    # Core AO identifiers (from SQL model)
    channel_id: str
    ao: str
    channel_created: int
    archived: bool
    backblast: bool | None = None
    site_q_user_id: str | None = None
