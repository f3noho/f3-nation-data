from pydantic import BaseModel


class ParsedBeatdown(BaseModel):
    """Application model for a complete BeatDown with parsed data and metadata.

    This is the primary application model for representing a beatdown workout event
    with fully parsed backblast content and computed metadata fields. It combines
    the core beatdown identifiers with structured parsed data and analytical fields
    needed for application features like reporting, analysis, and rich UI displays.

    This model is used throughout the application for:
    - Processing and displaying beatdown data in the UI
    - Generating reports and statistics from workout data
    - Building rich beatdown detail views and summaries
    - Performing analysis on workout content and participation
    - Validating and enriching beatdown data during processing

    Attributes:
        # Core beatdown identifiers
        timestamp: Unique timestamp identifier for the beatdown (primary key).
        last_edited: Optional timestamp when the beatdown was last modified.
        raw_backblast: The complete raw backblast text content containing all workout details.

        # Parsed backblast content
        title: Title of the beatdown extracted from the first line of the backblast.
        q_user_id: User ID of the Q (workout leader).
        coq_user_id: List of user IDs for Co-Qs (co-leaders), if any.
        pax: List of registered PAX user IDs who attended the workout.
        non_registered_pax: List of non-registered participant names.
        fngs: List of FNG (Friendly New Guy) names who attended.
        warmup: Description of the warmup activities.
        thang: Description of the main workout (The Thang).
        mary: Description of the Mary (cool-down/abs) activities.
        announcements: Any announcements made during the workout.
        cot: Circle of Trust (closing thoughts/prayers/reflections).
        raw_text: All remaining text content after the COUNT line.

        # Analytical properties
        bd_date: The actual workout date (YYYY-MM-DD format).
        workout_type: Type of workout (e.g., "bootcamp", "ruck", "2nd F", "special event").
        day_of_week: Day of the week the workout occurred (e.g., "Monday", "Tuesday").
        has_announcements: Whether the backblast includes announcements section.
        has_cot: Whether the backblast includes Circle of Trust content.
        word_count: Approximate word count of the backblast content.

        # Computed metrics
        pax_count: Total count of PAX who attended the beatdown.
        fng_count: Count of FNGs (Friendly New Guys) who attended.

    Note:
        This model represents the complete application view of a beatdown with
        all parsed content and computed fields. It's designed to provide everything
        needed for application features without requiring additional parsing or
        computation at display time.
    """

    # core beatdown identifiers
    timestamp: str
    last_edited: str | None = None
    raw_backblast: str
    ao_id: str  # Added for analytics efficiency

    # Parsed backblast content
    title: str | None = None
    q_user_id: str | None = None
    coq_user_id: list[str] | None = None
    pax: list[str] | None = None
    non_registered_pax: list[str] | None = None
    fngs: list[str] | None = None
    warmup: str | None = None
    thang: str | None = None
    mary: str | None = None
    announcements: str | None = None
    cot: str | None = None

    # Analytical properties
    bd_date: str | None = None
    workout_type: str | None = None
    day_of_week: str | None = None
    has_announcements: bool = False
    has_cot: bool = False
    word_count: int | None = None

    # Enhanced metadata and computed fields
    pax_count: int | None = None
    fng_count: int | None = None
