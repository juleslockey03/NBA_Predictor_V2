# NBA_Predictor v2: plan

Written 2026-10-21, the 2026-27 season tipped off yesterday, so the clock on the live record is already running.

## The one-line pitch

A pipeline that runs every day of the 2026-27 season on its own, pulls last night's results and today's odds, rebuilds the features with dbt, predicts tonight's games and commits them to GitHub before tip-off (so the git timestamp proves they were made in advance), then scores itself the next morning against what happened and against the bookmakers' de-vigged closing line, and shows the running record on a public page.

v1 was "a model I trained once and backtested", v2 is "a model with a live, pre-registered, timestamped track record against the market", and that second sentence is the one that gets a reaction in an interview.

## What v1 got right and what v2 fixes

Checked against the v1 repo today:

| v1 | v2 |
|---|---|
| Rolling features `.shift(1)`-ed within team and season, the leakage story | Keep it, and make it a dbt test so it can't regress (a row's features may only use games with an earlier date) |
| "Validated on a fully held-out season" | **That season was the first ~3 weeks of 2025-26, 240 team-rows, so 120 games, not a full season.** Fix the v1 README wording now, then do it properly in v2 with walk-forward validation across 4+ seasons |
| Bookmaker overround not removed, so EV is optimistic | De-vig every price (proportional, plus Shin as a comparison) before comparing |
| No baseline other than "bookmakers sit around 0.70 AUC" | Three explicit baselines: home team always, Elo, de-vigged market. The model has to beat Elo to be worth anything and is scored honestly against the market |
| `DAYS_SINCE_LAST_GAME` grouped by team only, so the first game of each season sees a ~180 day gap | Cap it, and add a proper "season opener" flag |
| No injuries or lineups | Phase 3, availability of top players by minutes |
| CSVs, scripts run by hand | DuckDB warehouse, dbt models with tests, scheduled daily run, monitoring |
| Accuracy, AUC, log loss, Brier | Same, plus calibration curve, and **closing line value (CLV)**, the metric sports trading desks actually care about |

## Stack (all free)

Python 3.12 with `uv`, `nba_api` for stats, the-odds-api for odds (the key you already have), DuckDB as the warehouse (one file), dbt Core with `dbt-duckdb`, scikit-learn plus LightGBM, Streamlit for the page, GitHub for code and the timestamped predictions.

**Orchestration decision:** start with a plain `make daily` run by macOS `launchd` so the live record starts this week, then wrap the same steps in Airflow in week 2. Airflow first would cost three evenings of Docker yak-shaving while real games go unpredicted, and nobody is impressed by a beautiful DAG with no track record.

**Runs on the Mac, not in the cloud,** because stats.nba.com blocks most cloud IPs. Short sleeps between requests.

## Repo layout

```
NBA_Predictor_v2/
  src/nba_predictor_v2/        the Python package (src layout, from uv init)
    ingest/      games.py, odds.py, backfill.py  (raw, idempotent loads into DuckDB)
    model/       features.py, train.py, predict.py, evaluate.py
    monitor/     score.py, drift alert
  dbt/           staging/, marts/, tests/
  predictions/   one committed CSV per day, the pre-registration
  app/           Streamlit page
  dags/          Airflow DAG (week 2)
  Makefile       make backfill / make daily / make train
  .env           ODDS_API_KEY, git-ignored
```

## Phases

### Phase 1: live by the weekend (evenings 1-4)

1. **Setup.** New public GitHub repo `NBA_Predictor_v2`, `uv` env, `.env`, `.gitignore`, Makefile skeleton. Fix the v1 README "fully held-out season" line while you're in there.
2. **Ingest results.** `ingest/games.py` pulls a date's games via `LeagueGameFinder`, writes raw rows into DuckDB keyed on `GAME_ID + TEAM_ID`, upsert so running it twice changes nothing. Same script handles backfill from **2018-19** onward (skipping the 2019-20 bubble games from training, or flagging them).
3. **Ingest odds.** `ingest/odds.py` stores today's h2h prices from UK and EU books with the fetch timestamp. Two fetches a day: one in the morning (the price you bet at) and one just before the first tip-off (your proxy for the closing line). That's about 60 requests a month, well inside the free tier.
4. **Quick model, first live predictions.** Port v1's features into SQL marts (`team_form` with 3/5/10 rolling windows, rest, back-to-backs, home), add an **Elo** rating, train logistic regression and LightGBM, and start committing `predictions/2026-10-xx.csv` daily before tip-off. Ugly is fine, the point is the record starts.

### Phase 2: make it rigorous (evenings 5-9)

5. **dbt properly.** Staging models per raw table, marts `games`, `team_form`, `elo`, `odds_devigged`, `features`. Tests: unique game IDs, no null scores, both teams present per game, dates in range, and the **no-future-data test** on every feature.
6. **Walk-forward validation.** Train on seasons up to N, test on N+1, rolling through 2021-22 to 2025-26. Report each season and the average, with Elo and home-team baselines beside the model. This replaces v1's 120-game test.
7. **Calibration done right.** Compare raw, Platt and isotonic on a separate calibration fold (v1 found Platt made the honest model worse, so keep that finding and test it properly rather than assuming).
8. **Monitoring.** Each morning `monitor/score.py` joins predictions to results: running accuracy, log loss, Brier, calibration buckets, model vs de-vigged market, and CLV (did the price move towards your number between your fetch and close). Warn if the last 30 games' Brier is clearly worse than the season-to-date.
9. **Airflow.** Wrap ingest results, ingest odds, dbt run, dbt test, predict, commit, score as a DAG with retries on the API steps. Keep `make daily` as the fallback.

### Phase 3: signal and polish (evenings 10-14)

10. **Player availability.** Pull the official injury report (or minutes from box scores to infer who sat), weight by each player's share of team minutes or on/off impact, add "missing minutes-weighted rating" as a feature. This is where v1 said the remaining signal probably sits, so test it in walk-forward and report whether it helped, honestly either way.
11. **Paper staking.** Flat stake and fractional Kelly on games where model edge after de-vig clears a threshold, logged as a paper P&L, explicitly not real money.
12. **Streamlit page.** Tonight's predictions, season record vs market, calibration chart, CLV over time. Deploy on Streamlit Community Cloud reading a DuckDB export committed by the daily run (the app reads, the Mac writes, so the cloud IP block doesn't matter).
13. **README.** Pipeline diagram, how pre-registration works, the live record so far, the walk-forward table, and an "honest limitations" section like v1's, because that section is half of why v1 lands in interviews.

### Phase 4, later: "Ask the NBA"

Read-only SQL views over the marts, a Claude tool-use loop that answers questions against them, a 30-50 question eval set with known answers. Only once Phases 1-3 are done.

## Definition of done for the first sprint

By **Sunday 2026-10-25**: repo public, backfill loaded, daily predictions committed before tip-off for at least two match days, Elo and model both predicting. Everything after that improves a thing that's already running.

## Watch out for

- **Historical odds are paid** on the-odds-api, so the market comparison is live-only from now. Fine, that's the point of the live record, but say so in the README rather than implying a backtest against the market.
- **Pre-registration only counts if it's honest:** never edit a committed predictions file, if something breaks, log the miss.
- **Early season form is noisy** with 1-3 games played, so carry last season's Elo with regression to the mean rather than starting from zero.
- **Sample size:** by Christmas you'll have ~450 games, enough to say something about calibration, not enough to claim you beat the market. Write it that way.

## CV line once it's real (only after it's true)

"Built a daily dbt and Airflow pipeline on DuckDB that pre-registers NBA predictions before tip-off and scores them against de-vigged closing odds; X games live, log loss Y vs market Z, walk-forward validated across five seasons."
