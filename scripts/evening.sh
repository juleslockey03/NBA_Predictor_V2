#!/bin/zsh
# Evening job: odds snapshot just before the first tip-off (the "closing" price).
cd /Users/juleslockey/code/NBA_Predictor_v2

echo "=== evening run $(date -u '+%Y-%m-%d %H:%M UTC') ==="
/opt/homebrew/bin/uv run python -m nba_predictor_v2.ingest.odds
