#!/usr/bin/env python3
"""Quick script to check what beatdowns exist in the database."""

from sqlalchemy.orm import Session
from f3_nation_data.database import get_sql_engine
from f3_nation_data.fetch import fetch_sql_beatdowns, _timestamp_to_datetime

def main():
    engine = get_sql_engine()
    with Session(engine) as session:
        # Get all beatdowns
        beatdowns = fetch_sql_beatdowns(session)
        print(f"Total beatdowns found: {len(beatdowns)}")
        
        if beatdowns:
            # Show first few beatdown timestamps
            for i, beatdown in enumerate(beatdowns[:5]):
                timestamp_dt = _timestamp_to_datetime(beatdown.timestamp)
                print(f"Beatdown {i+1}: {beatdown.timestamp} -> {timestamp_dt}")
                
            # Show date range
            timestamps = [_timestamp_to_datetime(bd.timestamp) for bd in beatdowns]
            earliest = min(timestamps)
            latest = max(timestamps)
            print(f"Date range: {earliest} to {latest}")

if __name__ == "__main__":
    main()
