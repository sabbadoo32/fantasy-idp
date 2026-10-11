"""Pull nflverse weekly player stats + snap counts and snapshot them into data/.

Usage:  python src/pull.py 2026        # pull one season
        python src/pull.py 2025 2026   # multiple
Writes data/stats_player_week_, snap_counts_, injuries_ and roster_weekly_<season>.parquet.
Commit these snapshots weekly — the git history is your tracking record.
"""
import sys, pandas as pd, pathlib

REL = "https://github.com/nflverse/nflverse-data/releases/download/"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

def pull(season):
    DATA.mkdir(exist_ok=True)
    df = pd.read_parquet(REL + f"stats_player/stats_player_week_{season}.parquet")
    df = df[df["season_type"] == "REG"].copy()
    out = DATA / f"stats_player_week_{season}.parquet"
    df.to_parquet(out)
    wks = sorted(df["week"].dropna().unique().tolist())
    print(f"{season}: {len(df)} rows, weeks {wks[:1]}..{wks[-1:]} -> {out}")
    try:
        sn = pd.read_parquet(REL + f"snap_counts/snap_counts_{season}.parquet")
        sn = sn[sn["game_type"] == "REG"].copy()
        sn.to_parquet(DATA / f"snap_counts_{season}.parquet")
        print(f"{season}: snap counts, {len(sn)} rows")
    except Exception as e:  # snap counts are a usage signal, not required
        print(f"{season}: snap counts unavailable ({e})")
    # team-week stats: each row is a team's game, with opponent_team — flip by opponent to
    # get points/yards allowed by position (src/matchups.py) and, later, Team DST scoring.
    try:
        tm = pd.read_parquet(REL + f"stats_team/stats_team_week_{season}.parquet")
        tm = tm[tm["season_type"] == "REG"].copy()
        tm.to_parquet(DATA / f"stats_team_week_{season}.parquet")
        wks = sorted(tm["week"].dropna().unique().tolist())
        print(f"{season}: team stats, {len(tm)} rows, weeks {wks[:1]}..{wks[-1:]}")
    except Exception as e:  # team grain powers matchups + DST, not player scoring
        print(f"{season}: team stats unavailable ({e})")
    # play-by-play (slim): powers Team DST — points allowed (final scores), three-and-outs,
    # and fourth-down stops, none of which are in the team-week aggregate.
    try:
        pbp_cols = ["week", "posteam", "defteam", "series", "series_result", "first_down",
                    "fourth_down_failed", "home_team", "away_team", "home_score", "away_score"]
        pbp = pd.read_parquet(REL + f"pbp/play_by_play_{season}.parquet", columns=pbp_cols)
        pbp.to_parquet(DATA / f"pbp_{season}.parquet")
        print(f"{season}: pbp (slim), {len(pbp)} rows")
    except Exception as e:  # DST needs this; player/matchup scoring does not
        print(f"{season}: pbp unavailable ({e})")
    # injury status: official weekly injury reports + weekly roster status (RES = IR/PUP/NFI)
    for name, url in [("injuries", f"injuries/injuries_{season}.parquet"),
                      ("roster_weekly", f"weekly_rosters/roster_weekly_{season}.parquet")]:
        try:
            pd.read_parquet(REL + url).to_parquet(DATA / f"{name}_{season}.parquet")
            print(f"{season}: {name} ok")
        except Exception as e:
            print(f"{season}: {name} unavailable ({e})")
    return df

if __name__ == "__main__":
    seasons = [int(x) for x in sys.argv[1:]] or [2025, 2026]
    for s in seasons:
        pull(s)
