#!/bin/zsh
# Morning job: odds snapshot, then last night's results.
cd /Users/juleslockey/Documents/NBA_Predictor_v2

echo "=== morning run $(date -u '+%Y-%m-%d %H:%M UTC') ==="
/opt/homebrew/bin/uv run python -m nba_predictor_v2.ingest.odds
/opt/homebrew/bin/uv run python -m nba_predictor_v2.ingest.games
