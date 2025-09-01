from dataclasses import dataclass
from datetime import datetime

from .parsed.beatdown import ParsedBeatdown


@dataclass
class BeatdownRecord:
    """Complete beatdown record for external sync, including parsed data and metadata."""

    backblast: ParsedBeatdown
    timestamp: datetime
    last_edited: datetime | None = None
