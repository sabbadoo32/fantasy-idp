"""Positional offense-vs-defense matchup grid for league 672352, at league scoring.

The old Huddle "offense vs defense by position" report: how many league-scored points
each defense allows to each position per game, ranked, plus a "levels" decomposition so
you can read the frame a player is in — e.g. a back facing a stout run front but a soft
second level will get his points through the air, not on the ground.

Source grain: nflverse stats_player_week (who scored, vs which defense) + stats_team_week
(explosive-play context). Points allowed to position D = sum of league-scored output by
players of that position whose opponent_team == D, averaged per game.

Usage:
    python src/matchups.py            # latest season/week in data/, writes data/matchups_<season>.json
    from matchups import build_grid   # -> dict, same payload the artifact consumes
"""
import sys, json, pathlib
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scoring import load_scoring, POS_GROUP, _n

ROOT = pathlib.Path(__file__).resolve().parents[1]
GRID_POS = ["QB", "RB", "WR", "TE", "K", "IDP-DL", "IDP-LB", "IDP-DB"]
# nflverse team codes that differ from common usage
TEAM_FIX = {"LA": "LAR"}  # stats files use LA for the Rams


def _components(df, cfg):
    """Return rush/rec/pass component points per player-week, for the levels split.
    These sum (plus kicking/idp handled elsewhere) back to pts_off from scoring.py."""
    o = cfg["offense"]
    py, ry, cy = _n(df, "passing_yards"), _n(df, "rushing_yards"), _n(df, "receiving_yards")
    pass_pts = (py * o["passing_yards"] + _n(df, "passing_tds") * o["passing_tds"]
                + _n(df, "passing_interceptions") * o["interceptions"]
                + _n(df, "passing_2pt_conversions") * o["passing_2pt"])
    rush_pts = (ry * o["rushing_yards"] + _n(df, "carries") * o["rushing_attempts"]
                + _n(df, "rushing_tds") * o["rushing_tds"]
                + _n(df, "rushing_first_downs") * o["rushing_first_downs"]
                + _n(df, "rushing_2pt_conversions") * o["rushing_2pt"])
    rec_pts = (cy * o["receiving_yards"] + _n(df, "receptions") * o["receptions"]
               + _n(df, "receiving_tds") * o["receiving_tds"]
               + _n(df, "receiving_first_downs") * o["receiving_first_downs"]
               + _n(df, "receiving_2pt_conversions") * o["receiving_2pt"])
    for yards, tbl, col in [(py, o["bonus_passing"], "pass"), (ry, o["bonus_rushing"], "rush"),
                            (cy, o["bonus_receiving"], "rec")]:
        bonus = sum((yards >= int(thr)) * bp for thr, bp in tbl.items())
        if col == "pass": pass_pts = pass_pts + bonus
        elif col == "rush": rush_pts = rush_pts + bonus
        else: rec_pts = rec_pts + bonus
    return pass_pts, rush_pts, rec_pts


def _latest(season=None):
    files = sorted(ROOT.glob("data/stats_player_week_*.parquet"))
    if season is None:
        season = max(int(f.stem.split("_")[-1]) for f in files)
    return season


def _last_complete_week(season, fallback):
    """Last week with a full slate. The weekly pull can include the live week partially
    (Sunday games in progress), which would skew per-game averages — so drop any trailing
    week that doesn't have most of the league's 32 teams played."""
    tp = ROOT / "data" / f"stats_team_week_{season}.parquet"
    if not tp.exists():
        return fallback
    tw = pd.read_parquet(tp)
    counts = tw.groupby("week")["team"].nunique()
    complete = counts[counts >= 28].index  # 28 of 32 teams = a full or near-full slate
    return int(complete.max()) if len(complete) else fallback


def _returns_allowed(season, through):
    """Kickoff/punt return yards each defense gives up per game — a scored axis (1 pt/yd)
    the position grid misses, because a KR/PR specialist's points come from returns, not
    receiving. From the team file, flipped by opponent_team. Returns (DataFrame, ranks)."""
    tp = ROOT / "data" / f"stats_team_week_{season}.parquet"
    if not tp.exists():
        return None, None
    tw = pd.read_parquet(tp)
    tw = tw[tw["week"] <= through].copy()
    tw["opp"] = tw["opponent_team"].replace(TEAM_FIX)
    games = tw.groupby("opp")["week"].nunique()
    a = pd.DataFrame({
        "kr_yds": tw.groupby("opp")["kickoff_return_yards"].sum() / games,
        "kr_ret": tw.groupby("opp")["kickoff_returns"].sum() / games,
        "pr_yds": tw.groupby("opp")["punt_return_yards"].sum() / games,
    }).round(1)
    a["ret_yds"] = (a["kr_yds"] + a["pr_yds"]).round(1)
    ranks = a[["kr_yds", "pr_yds", "ret_yds"]].rank(ascending=False)  # #1 = most generous
    return a, ranks


def player_returns(season=None, through=None, min_ypg=25.0):
    """Per-player return yards per game (kickoff + punt). Used to flag roster returners so a
    frame scores them on return-yards-allowed, not their listed-position coverage. Returns
    {std-ish player_name: {kr_ypg, pr_ypg, ret_ypg, is_returner}}."""
    season = _latest(season)
    pw = pd.read_parquet(ROOT / "data" / f"stats_player_week_{season}.parquet")
    if through is None:
        through = _last_complete_week(season, int(pw["week"].max()))
    pw = pw[pw["week"] <= through].copy()
    for c in ("kickoff_return_yards", "punt_return_yards"):
        if c not in pw.columns:
            pw[c] = 0
    g = pw.groupby("player_name").agg(
        wk=("week", "nunique"),
        kr=("kickoff_return_yards", "sum"),
        pr=("punt_return_yards", "sum")).reset_index()
    out = {}
    for r in g.itertuples():
        ypg = (r.kr + r.pr) / max(r.wk, 1)
        out[r.player_name] = {"kr_ypg": round(r.kr / max(r.wk, 1), 1),
                              "pr_ypg": round(r.pr / max(r.wk, 1), 1),
                              "ret_ypg": round(ypg, 1), "is_returner": ypg >= min_ypg}
    return out


def build_grid(season=None, through=None):
    cfg = load_scoring()
    season = _latest(season)
    pw = pd.read_parquet(ROOT / "data" / f"stats_player_week_{season}.parquet")
    pw["grp"] = pw["position"].map(POS_GROUP)
    pw = pw[pw["grp"].notna()].copy()
    if through is None:
        through = _last_complete_week(season, int(pw["week"].max()))
    # The weekly player snapshot holds completed weeks only (the live week isn't posted
    # to nflverse yet), so every week present is a full game — include through `through`.
    full = pw[pw["week"] <= through]
    through_full = int(full["week"].max()) if len(full) else through

    from scoring import score_players
    scored = score_players(full, cfg)
    pass_pts, rush_pts, rec_pts = _components(full, cfg)
    scored["pass_c"], scored["rush_c"], scored["rec_c"] = pass_pts, rush_pts, rec_pts
    scored["opp"] = scored["opponent_team"].replace(TEAM_FIX)

    # collapse duplicate player-week rows (mid-week team changes) before aggregating
    keys = ["player_name", "week", "opp", "grp"]
    agg = scored.groupby(keys, as_index=False)[["pts", "pass_c", "rush_c", "rec_c"]].sum()

    games = agg.groupby("opp")["week"].nunique()

    def allowed_per_game(frame, col):
        tot = frame.groupby(["opp", "grp"])[col].sum()
        return (tot / games).unstack("grp")

    grid = allowed_per_game(agg, "pts")[GRID_POS].round(1)
    ranks = grid.rank(ascending=False)  # #1 = most generous; NaN where no data

    # levels: ground vs air allowed to RBs; air allowed to WR/TE
    rb = agg[agg["grp"] == "RB"]
    rb_ground = (rb.groupby("opp")["rush_c"].sum() / games).round(1)
    rb_air = (rb.groupby("opp")["rec_c"].sum() / games).round(1)

    ret, ret_ranks = _returns_allowed(season, through_full)

    defenses = sorted(grid.index)
    payload = {
        "season": season, "through_week": through_full,
        "generated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "positions": GRID_POS,
        "defenses": [],
    }
    for d in defenses:
        row = {"team": d, "allowed": {}, "rank": {}}
        for p in GRID_POS:
            v = grid.loc[d, p]
            row["allowed"][p] = None if pd.isna(v) else float(v)
            r = ranks.loc[d, p]
            row["rank"][p] = None if pd.isna(r) else int(r)
        row["levels"] = {
            "rb_ground": None if d not in rb_ground.index else float(rb_ground[d]),
            "rb_air": None if d not in rb_air.index else float(rb_air[d]),
        }
        if ret is not None and d in ret.index:
            row["returns"] = {
                "kr_yds": float(ret.loc[d, "kr_yds"]), "kr_ret": float(ret.loc[d, "kr_ret"]),
                "pr_yds": float(ret.loc[d, "pr_yds"]), "ret_yds": float(ret.loc[d, "ret_yds"]),
                "kr_rank": int(ret_ranks.loc[d, "kr_yds"]), "ret_rank": int(ret_ranks.loc[d, "ret_yds"]),
            }
        else:
            row["returns"] = None
        payload["defenses"].append(row)
    return payload


if __name__ == "__main__":
    args = [int(x) for x in sys.argv[1:]]
    season = args[0] if args else None
    through = args[1] if len(args) > 1 else None
    data = build_grid(season, through)
    out = ROOT / "data" / f"matchups_{data['season']}.json"
    out.write_text(json.dumps(data, indent=2))
    n = len(data["defenses"])
    print(f"{data['season']} through W{data['through_week']}: {n} defenses -> {out}")
