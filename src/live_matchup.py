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
from scoring import score_players, score_team_dst
from availability import std_name

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _starters(doc):
    for slot, ps in doc["starters"].items():
        for p in ps:
            yield slot, p["name"], p.get("team"), slot == "DEF"


def _score_side(doc, name, pts_by_key, dst_by_team, played_keys, dst_teams):
    rows, total, pending = [], 0.0, 0
    for slot, pname, team, is_dst in _starters(doc):
        if is_dst:
            pts = float(dst_by_team.get(team, 0.0)); played = team in dst_teams
        else:
            pts = float(pts_by_key.get(std_name(pname), 0.0)); played = std_name(pname) in played_keys
        total += pts
        pending += 0 if played else 1
        rows.append({"slot": slot, "name": pname, "pts": round(pts, 1),
                     "played": played, "is_dst": is_dst})
    return {"name": name, "total": round(total, 1), "pending": pending, "starters": rows}


def build(season=None):
    if season is None:
        season = max(int(p.stem.split("_")[-1]) for p in (ROOT / "data").glob("stats_player_week_*.parquet"))
    pw = pd.read_parquet(ROOT / "data" / f"stats_player_week_{season}.parquet")
    week = int(pw["week"].max())                     # the live (possibly partial) week
    cur = score_players(pw[pw["week"] == week])
    pts_by_key = cur.assign(k=cur["player_display_name"].map(std_name)).groupby("k")["pts"].sum().to_dict()
    played_keys = set(cur["player_display_name"].map(std_name))

    tw = pd.read_parquet(ROOT / "data" / f"stats_team_week_{season}.parquet")
    pbp = pd.read_parquet(ROOT / "data" / f"pbp_{season}.parquet") if (ROOT / "data" / f"pbp_{season}.parquet").exists() else None
    twk = tw[tw["week"] == week]
    dst = score_team_dst(twk, pbp[pbp["week"] == week] if pbp is not None else None)
    dst_by_team = dict(zip(dst["team"], dst["pts_dst"]))
    dst_teams = set(twk["team"])

    me = yaml.safe_load(open(ROOT / "league" / "roster.yaml"))
    opp = yaml.safe_load(open(ROOT / "league" / "opponent.yaml"))
    me_name = "Team Work"
    payload = {
        "season": season, "week": week,
        "generated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "me": _score_side(me, me_name, pts_by_key, dst_by_team, played_keys, dst_teams),
        "opp": _score_side(opp, opp.get("name", "Opponent"), pts_by_key, dst_by_team, played_keys, dst_teams),
    }
    out = ROOT / "data" / f"live_matchup_{season}.json"
    out.write_text(json.dumps(payload, indent=2))
    m, o = payload["me"], payload["opp"]
    print(f"W{week} LIVE  {m['name']} {m['total']} ({m['pending']} to play)  vs  "
          f"{o['name']} {o['total']} ({o['pending']} to play)  -> {out.name}")
    return payload


if __name__ == "__main__":
    build()
