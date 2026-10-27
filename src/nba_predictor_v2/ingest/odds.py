"""Snapshot NBA head-to-head odds from the-odds-api into the raw DuckDB table."""

import os

import duckdb
import pandas as pd
import requests
from dotenv import load_dotenv
from nba_predictor_v2.config import DB_PATH

ODDS_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"


def create_table(con):
    con.execute("""
            CREATE TABLE IF NOT EXISTS raw_odds(
                fetched_at  TIMESTAMPTZ,
                event_id    VARCHAR,
                commence_time   TIMESTAMPTZ,
                home_team   VARCHAR,
                away_team   VARCHAR,
                bookmaker_key   VARCHAR,
                market_key  VARCHAR,
                outcome_name    VARCHAR,
                price   DOUBLE,
                PRIMARY KEY     (fetched_at, event_id, bookmaker_key, market_key, outcome_name)
            )
            """)


def fetch_odds(api_key):
    resp = requests.get(
        ODDS_URL,
        params={
            "apiKey": api_key,
            "regions": "uk,eu",
            "markets": "h2h",
            "oddsFormat": "decimal",
        },
        timeout=30
    )
    resp.raise_for_status()
    print(f"Odds API credits remaining: {resp.headers.get('x-requests-remaining')}")
    return resp.json()


def flatten_odds(data, fetched_at):

    rows = []

    for event in data:
        for book in event['bookmakers']:
            for market in book['markets']:
                for outcome in market['outcomes']:
                    rows.append({
                        'fetched_at' : fetched_at,
                        'event_id' : event['id'],
                        'commence_time' : event['commence_time'],
                        'home_team' : event['home_team'],
                        'away_team' : event['away_team'],
                        'bookmaker_key' : book['key'],
                        'market_key' : market['key'],
                        'outcome_name' : outcome['name'],
                        'price' : outcome['price'],
                    })
    return pd.DataFrame(rows)


def load_odds(con, odds):
    con.execute("INSERT INTO raw_odds BY NAME SELECT * FROM odds")


def main():
    load_dotenv()
    api_key = os.getenv("ODDS_API_KEY")
    fetched_at = pd.Timestamp.now(tz="UTC")
    con = duckdb.connect(DB_PATH)
    create_table(con)
    data = fetch_odds(api_key)
    odds = flatten_odds(data, fetched_at)
    load_odds(con, odds)
    total = con.sql("SELECT COUNT(*) FROM raw_odds").fetchone()[0]
    print(f"Loaded {len(odds)} odds rows, table now has {total} rows")
    con.close()


if __name__ == "__main__":
    main()
