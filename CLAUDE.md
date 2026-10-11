# Fantasy IDP tracker — Yahoo league 672352

This repo scores an unusual Yahoo league at its exact settings and tracks a roster
week to week. Claude Code should read this file first every session — it is the memory.

> **LIVE-FIRST — everything live, all of the time.** Never answer from a stale snapshot.
> Before ANY read, refresh to live: `pull.py` for current nflverse data, resync the roster
> and availability from live Yahoo, and during games pull again for in-progress numbers.
> The committed `data/` snapshot is the historical tracking record, NEVER the basis for
> advice. If something can't be refreshed, say so before answering. (owner directive, 2026-10-11)

## The league (why it's different)
- Name: "1 Point per Yard League" (ID# 672352). Full IDP, run 10+ years.
- 1 point per yard on passing, rushing, AND receiving. A 300-yd passing game = 300 pts.
- QB is the throne (top QBs ~275-290 PPG in 2025). After QB, RB1s lead skill.
- Turnovers are nuclear: -35 per INT thrown and per fumble lost (offense);
  +25-35 to defense for forcing them.
- IDP is ~half the starting lineup. Tackle solo 15, sack 20, INT 35, TFL 20, PD 15.
  An elite LB scores like a WR1 (~150-160 PPG) at a fraction of the cost — that's the value seam.
- Full scoring is in `league/scoring.yaml` (verified, do not "simplify" it).

## The team — "Team Work" (manager sabbadoo32)
- Lineup: QB, 2RB, 3WR, TE, W/T, W/R, K, DEF, 3DB, 3DL, 3LB (+ bench + IR).
- Starts a team DEF (Buccaneers) AND 9 IDP. Team DST scoring matters — it is
  captured in scoring.yaml but NOT yet computed (needs team-grain data). See TODO.
- Roster in `league/roster.yaml`, synced from the live Yahoo team page (team id 1).
  The 2026-09-19 screenshot version was 12 players stale — always resync before advice.
- Quote "NO" in YAML (bare NO parses as false).

## Data & method
- Source: nflverse `stats_player_week` (offense + IDP + kicking in one file).
- `src/pull.py <season>` snapshots a season into `data/`. Commit snapshots weekly;
  git history is the tracking record.
- `src/scoring.py` applies scoring.yaml. Verified: Josh Allen 2025 W1 = 485.0 vs box score.
- `src/report.py` writes a weekly report to `reports/`: roster, bench-vs-starter swaps,
  waiver watch limited to players actually available, each compared to my weakest starter.
  Flags: DNP last week; return-yard dependence (return yards score 1/yd, so returners are
  a real value seam here, but the role is fragile — "0 ret yds" means he may have lost it).
- Availability: `league/taken.txt` = every player rostered league-wide (Yahoo status=T).
  Available = not in that list. Refreshed by `tools/yahoo_sync.js` run in Chrome (read-only).
  Yahoo API access was applied for, pending manual review; when approved, only
  `src/availability.py` changes.
- Snap share from nflverse `snap_counts` (pulled by `pull.py`).
- Injury status from nflverse `injuries` + `weekly_rosters` (RES = IR/reserve). IR and
  upcoming-week Out players are excluded from adds and swaps. The feed lags breaking news
  (Achane's season-ending ACL took ~3 days to show), so before recommending ANY name —
  add or start/sit — web-search its current injury news. Never skip this step.

## Standing preferences (owner: Sebastian)
- At awakening, before any player read: re-read this file, roster.yaml, latest report, and
  state data staleness. Verify each player's ACTUAL role/component scoring from the data
  before framing a matchup — never lead with a receiving/positional read. Return yards score
  1/yd: a KR/PR specialist (e.g. Brooks) is scored on return-yards-allowed, not WR coverage.
  Collapse duplicate player-week rows first. (Full: memory/review-before-advice.md)
- Answer-first, terse, AP style. Decisive recommendation over option menus.
- Separate observation / inference / recommendation. Uploaded/rostered data is the universe.
- Small samples (early season) are noise — rank on season-to-date PPG, not one week.
- Show the work: which stat drove the number.

## TODO / roadmap
- [ ] PRODUCT GOAL: multi-user leaguewide app — each member links their own Yahoo team (needs
      Yahoo OAuth approval + hosting, React/Vite/Netlify). Gate: a few weeks of a validation log
      (scoring vs official box scores, did matchup/returns reads predict, sync held) before
      pitching to the league. (memory/productization-goal.md)
- [x] Return-game layer: KR/PR yards-allowed per defense + returner flagging (matchups.py, artifact).
- [ ] Team DST scoring (points-allowed + yards-allowed tiers) from nflverse team stats + schedules.
- [x] Waiver watch filtered by actual Yahoo availability (Chrome sync, 2026-09-30).
- [ ] Weekly automation: cron `pull.py` + `report.py` after Tuesday waiver run.
- [ ] Start/sit optimizer across the IR/bench given matchups.
- [ ] Optional: Yahoo API (OAuth) to auto-sync roster + free agents instead of screenshots.
