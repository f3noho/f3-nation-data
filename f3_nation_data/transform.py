from f3_nation_data.models import BeatdownRecord, SqlBeatDownModel
from f3_nation_data.parsing.backblast import parse_backblast


def transform_sql_to_beatdown_record(
    sql_bd: SqlBeatDownModel,
) -> BeatdownRecord:
    """Transform a SQL beatdown row into BeatdownRecord.

    Args:
        sql_bd (SqlBeatDownModel): The SQL beatdown model instance.

    Returns:
        BeatdownRecord: The transformed beatdown record.
    """
    parsed_bd = parse_backblast(sql_bd.backblast or '')

    # Use AO ID from backblast if available, otherwise use SQL model AO ID
    if not parsed_bd.ao_id:
        parsed_bd.ao_id = sql_bd.ao_id

    return BeatdownRecord(
        backblast=parsed_bd,
        timestamp=sql_bd.timestamp or '',
        last_edited=sql_bd.ts_edited,
    )
