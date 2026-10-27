"""Load NBA team box scores from stats.nba.com into the raw DuckDB table."""

import sys
import duckdb
import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder
from nba_predictor_v2.config import DB_PATH


def create_table(con):
    con.execute("""
            CREATE TABLE IF NOT EXISTS raw_team_games(
                SEASON_ID   VARCHAR,
                TEAM_ID     VARCHAR,
                TEAM_ABBREVIATION VARCHAR,
                TEAM_NAME   VARCHAR,
                GAME_ID     VARCHAR,
                GAME_DATE   DATE,
                MATCHUP     VARCHAR,
                WL          VARCHAR,
                MIN         INTEGER,
                PTS         INTEGER,
                FGM         INTEGER,
                FGA         INTEGER,
                FG_PCT      DOUBLE,
                FG3M        INTEGER,
                FG3A        INTEGER,
                FG3_PCT     DOUBLE,
                FTM         INTEGER,
                FTA         INTEGER,
                FT_PCT      DOUBLE,
                OREB        INTEGER,
                DREB        INTEGER,
                REB         INTEGER,
                AST         INTEGER,
                STL         INTEGER,
                BLK         INTEGER,
                TOV         INTEGER,
                PF          INTEGER,
                PLUS_MINUS  INTEGER,
                INGESTED_AT TIMESTAMPTZ,
                PRIMARY KEY (GAME_ID, TEAM_ID)
            )
            """)

def fetch_games(date):
    finder = leaguegamefinder.LeagueGameFinder(
        league_id_nullable="00",
        season_type_nullable="Regular Season",
        date_from_nullable=date,
        date_to_nullable=date,
    )
    df = finder.get_data_frames()[0]
    df['TEAM_ID'] = df['TEAM_ID'].astype(str)
    df['INGESTED_AT'] = pd.Timestamp.now(tz="UTC")
    return df

def load_games(con, df):
    con.execute("INSERT OR REPLACE INTO raw_team_games BY NAME SELECT * FROM df")

def main():
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        yesterday = pd.Timestamp.now(tz='America/New_York') - pd.Timedelta(days=1)
        date = yesterday.strftime('%m/%d/%Y')
    con = duckdb.connect(DB_PATH)
    create_table(con)
    df = fetch_games(date)
    load_games(con, df)
    total = con.sql("SELECT COUNT(*) FROM raw_team_games").fetchone()[0]
    print(f"Loaded {len(df)} rows for {date}, table now has {total} rows")
    con.close()

if __name__ == "__main__":
    main()
