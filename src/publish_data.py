"""Produce the JSON the hosted app serves: site-data/live.json and site-data/matchups.json.

Run by the GitHub Action on a cron. live.json is cheap (Sleeper + ESPN, no parquet) and
refreshes often during games; matchups.json needs the nflverse snapshot and refreshes daily.

Usage:
    python src/publish_data.py live     # just the live tracker (frequent)
    python src/publish_data.py grid     # just the matchup grid (daily, after a pull)
    python src/publish_data.py all       # both
"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "site-data"


def _write(name, payload):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(payload))
    print(f"wrote site-data/{name}")


def publish_live():
    from live_matchup import build
    _write("live.json", build())


def publish_grid():
    from matchups import build_grid
    from build_artifact import _build_frames
    data = build_grid()
    data["team_name"], data["week"] = "Team Work", 5
    data["team_week5"] = _build_frames(data)
    _write("matchups.json", data)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("live", "all"):
        publish_live()
    if what in ("grid", "all"):
        publish_grid()
