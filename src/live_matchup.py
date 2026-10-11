"""Live, DST-aware score tracker for the current-week matchup.

Unlike report.py/matchups.py (which rank on completed weeks), this scores the LIVE week —
the in-progress slate — so you can watch the matchup in real time. It scores both full
lineups at league settings INCLUDING team DST, marks who has played vs is still to come,
and writes a scoreboard (JSON + reports/live_matchup.html) you republish as an artifact.

Not self-updating: re-run after a fresh pull to refresh. Usage:
    python src/pull.py 2026 && python src/live_matchup.py
"""
import sys, json, pathlib
import pandas as pd, yaml
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from availability import std_name
from live_source import live_week

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _starters(doc):
    for slot, ps in doc["starters"].items():
        for p in ps:
            yield slot, p["name"], p.get("team"), slot == "DEF"


def _score_side(doc, name, lw):
    """Score one lineup off the live feed. 'in'/'post' games show live/final points;
    'pre' (not kicked off) shows as still to play."""
    rows, total, pending, live = [], 0.0, 0, 0
    for slot, pname, team, is_dst in _starters(doc):
        pts = float(lw["dst_pts"].get(team, 0.0)) if is_dst else float(lw["player_pts"].get(std_name(pname), 0.0))
        state = lw["state"].get(team)            # pre | in | post | None
        playing = state in ("in", "post")
        total += pts
        pending += 0 if playing else 1
        live += 1 if state == "in" else 0
        rows.append({"slot": slot, "name": pname, "pts": round(pts, 1),
                     "played": playing, "live": state == "in", "is_dst": is_dst})
    return {"name": name, "total": round(total, 1), "pending": pending, "in_progress": live, "starters": rows}


def build(season=None, week=None):
    if season is None:
        season = max(int(p.stem.split("_")[-1]) for p in (ROOT / "data").glob("stats_player_week_*.parquet"))
    if week is None:
        pw = pd.read_parquet(ROOT / "data" / f"stats_player_week_{season}.parquet")
        week = int(pw["week"].max())             # the live (in-progress) week
    lw = live_week(season, week)                 # Sleeper scoring + ESPN game state

    me = yaml.safe_load(open(ROOT / "league" / "roster.yaml"))
    opp = yaml.safe_load(open(ROOT / "league" / "opponent.yaml"))
    payload = {
        "season": season, "week": week, "source": "Sleeper live + ESPN state",
        "generated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "me": _score_side(me, "Team Work", lw),
        "opp": _score_side(opp, opp.get("name", "Opponent"), lw),
    }
    out = ROOT / "data" / f"live_matchup_{season}.json"
    out.write_text(json.dumps(payload, indent=2))
    m, o = payload["me"], payload["opp"]
    print(f"W{week} LIVE  {m['name']} {m['total']} ({m['pending']} to play)  vs  "
          f"{o['name']} {o['total']} ({o['pending']} to play)  -> {out.name}")
    return payload


if __name__ == "__main__":
    build()
