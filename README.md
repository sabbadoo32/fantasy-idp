# fantasy-idp — league 672352 tracker

A Claude Code project that scores an all-IDP, point-per-yard Yahoo league at its exact
settings, tracks a roster over the season, and flags waiver upgrades.

## Setup
```bash
pip install -r requirements.txt
python src/pull.py 2025 2026      # snapshot data into data/
python src/report.py             # writes reports/week_<season>_<week>.md
```

## Weekly workflow (Tuesday night)
1. Sync Yahoo (Chrome, signed in): Claude runs `tools/yahoo_sync.js` on the league page and
   rewrites `league/taken.txt` and `league/roster.yaml`. Read-only — never adds or drops.
2. ```bash
   python src/pull.py 2026        # stats + snap counts
   python src/report.py           # roster, start/sit, waiver watch vs your starters
   ```
Commit the `data/` snapshot each week — the git history is your season-long tracking record.
Then open the repo in Claude Code and ask for start/sit, trade reads, or waiver priority;
it reads `CLAUDE.md` for the league, your roster, and how you like answers.

## Files
- `league/scoring.yaml` — your exact scoring (verified). Source of truth.
- `league/roster.yaml`  — your team; correct any (verify) teams on first run.
- `src/scoring.py`      — scoring engine (importable). Verified vs a real box score.
- `src/pull.py`         — nflverse weekly pull -> data/.
- `src/report.py`       — weekly markdown report.
- `src/availability.py` — who's on your wire (from league/taken.txt).
- `league/taken.txt`    — every player rostered league-wide, synced from Yahoo.
- `tools/yahoo_sync.js` — the read-only Chrome sync script.
- `CLAUDE.md`           — project memory Claude Code reads first.

## Known limits
- Team DST not yet scored (needs team-grain data) — see CLAUDE.md TODO.
- Availability is only as fresh as the last Chrome sync; the report flags it if >7 days old.
- No injury, bye or matchup data yet — check those before acting on a flag.
- Early-season numbers are small-sample — rankings use season-to-date PPG to damp noise.
