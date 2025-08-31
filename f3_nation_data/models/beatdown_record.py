from dataclasses import dataclass

from .parsed.beatdown import ParsedBeatdown


@dataclass
class BeatdownRecord:
    """Complete beatdown record for external sync, including parsed data and metadata."""

    backblast: ParsedBeatdown
    timestamp: str
    last_edited: str | None = None
