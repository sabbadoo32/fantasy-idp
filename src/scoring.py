"""Apply league 672352 scoring to nflverse weekly player stats.

Verified 2026-09-19: Josh Allen 2025 W1 -> 485.0 (hand-checked vs box score);
Ernest Jones 2025 W13 IDP -> 352.0 (component-decomposed, no double counts).
"""
import pandas as pd, yaml, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

def _n(df, c):
    return pd.to_numeric(df[c], errors="coerce").fillna(0) if c in df.columns else 0

def load_scoring(path=None):
    path = path or ROOT / "league" / "scoring.yaml"
    return yaml.safe_load(open(path))

POS_GROUP = {
    "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE", "K": "K",
    "DL": "IDP-DL", "DE": "IDP-DL", "DT": "IDP-DL", "NT": "IDP-DL",
    "LB": "IDP-LB", "ILB": "IDP-LB", "MLB": "IDP-LB", "OLB": "IDP-LB",
    "DB": "IDP-DB", "CB": "IDP-DB", "S": "IDP-DB", "SAF": "IDP-DB", "FS": "IDP-DB",
}

def score_players(df, cfg=None):
    """Return df with pts_off, pts_idp, pts_k, pts columns added (player-week grain).
    Team DST is scored separately (team grain) — see score_team_dst."""
    cfg = cfg or load_scoring()
    o = cfg["offense"]
    py, ry, cy = _n(df, "passing_yards"), _n(df, "rushing_yards"), _n(df, "receiving_yards")
    off = (
        py * o["passing_yards"] + _n(df, "passing_tds") * o["passing_tds"]
        + _n(df, "passing_interceptions") * o["interceptions"] + _n(df, "passing_2pt_conversions") * o["passing_2pt"]
        + ry * o["rushing_yards"] + _n(df, "carries") * o["rushing_attempts"]
        + _n(df, "rushing_tds") * o["rushing_tds"] + _n(df, "rushing_first_downs") * o["rushing_first_downs"]
        + _n(df, "rushing_2pt_conversions") * o["rushing_2pt"]
        + cy * o["receiving_yards"] + _n(df, "receptions") * o["receptions"]
        + _n(df, "receiving_tds") * o["receiving_tds"] + _n(df, "receiving_first_downs") * o["receiving_first_downs"]
        + _n(df, "receiving_2pt_conversions") * o["receiving_2pt"]
        + _n(df, "fumbles_lost_total") * o["fumbles_lost"]
        + (_n(df, "punt_return_yards") + _n(df, "kickoff_return_yards")) * o["return_yards"]
        + _n(df, "special_teams_tds") * o["return_td"] + _n(df, "fumble_recovery_tds") * o["off_fumble_return_td"]
    )
    for yards, tbl in [(py, o["bonus_passing"]), (ry, o["bonus_rushing"]), (cy, o["bonus_receiving"])]:
        for thr, bp in tbl.items():
            off += (yards >= int(thr)) * bp
    i = cfg["idp"]
    idp = (
        _n(df, "def_tackles_solo") * i["tackle_solo"] + _n(df, "def_tackle_assists") * i["tackle_assist"]
        + _n(df, "def_sacks") * i["sack"] + _n(df, "def_tackles_for_loss") * i["tackle_for_loss"]
        + _n(df, "def_interceptions") * i["interception"] + _n(df, "def_fumbles_forced") * i["fumble_force"]
        + _n(df, "fumble_recovery_opp") * i["fumble_recovery"] + _n(df, "def_pass_defended") * i["pass_defended"]
        + _n(df, "def_tds") * i["def_td"] + _n(df, "def_safeties") * i["safety"]
        + (_n(df, "def_punt_blocks") + _n(df, "def_pat_blocks") + _n(df, "def_fg_blocks")) * i["block_kick"]
        + (_n(df, "def_interception_yards") + _n(df, "fumble_recovery_yards_opp")) * i["turnover_return_yards"]
    )
    k = cfg["kicker"]
    kick = _n(df, "fg_made") * k["fg_made_each"] + _n(df, "fg_made_distance") * k["fg_total_yards"] + _n(df, "pat_made") * k["pat_made"]
    df = df.copy()
    df["pts_off"], df["pts_idp"], df["pts_k"] = off, idp, kick
    df["pts"] = off + idp + kick
    df["grp"] = df["position"].map(POS_GROUP)
    return df

def _tier(v, table):
    """Map a value to its tier points. Keys like 0, '1-6', '35+', 'neg'."""
    for k, pts in table.items():
        ks = str(k)
        if ks == "neg":
            if v < 0:
                return pts
        elif ks.endswith("+"):
            if v >= float(ks[:-1]):
                return pts
        elif "-" in ks:
            lo, hi = ks.split("-")
            if float(lo) <= v <= float(hi):
                return pts
        elif ks.replace(".", "").isdigit() and v == float(ks):
            return pts
    return 0.0


def _pbp_dst(pbp):
    """Per (defteam, week): points allowed (final score), three-and-outs, fourth-down stops."""
    if pbp is None or len(pbp) == 0:
        return {}
    out = {}
    for (team, wk), g in pbp.dropna(subset=["defteam"]).groupby(["defteam", "week"]):
        row = g.iloc[0]
        # points the offense (posteam) put up against this defense = opponent's final score
        pa = row["away_score"] if row["home_team"] == team else row["home_score"]
        ser_res = g.dropna(subset=["series"]).groupby("series")["series_result"].last()
        ser_fd = g.dropna(subset=["series"]).groupby("series")["first_down"].max()
        three_outs = sum(1 for s in ser_res.index
                         if ser_res[s] == "Punt" and not (ser_fd.get(s, 0) or 0))
        stops = int(pd.to_numeric(g["fourth_down_failed"], errors="coerce").fillna(0).sum())
        out[(team, int(wk))] = {"pa": float(pa) if pd.notna(pa) else 0.0,
                                "three_outs": three_outs, "stops": stops}
    return out


def score_team_dst(team_week, pbp=None, cfg=None):
    """Score each team's DEF/ST per week at league 672352 settings (team grain).

    Verified 2026 W5: Dallas (vs TB, lost 16-24) -> ~219, matching Yahoo (within ~1 pt;
    the delta is three-and-out penalty edge cases). Return-yards (1/yd) and the 25-pt big
    plays (sacks, TFL, fourth-down stops) dominate — DST is a WR1-sized category here.

    Needs pbp for points-allowed, three-and-outs, and fourth-down stops; without it those
    components are zero and the total is understated.
    """
    cfg = (cfg or load_scoring())["team_dst"]
    tw = team_week.copy()
    yds = {(r["team"], r["week"]): _n(tw.loc[[i]], "passing_yards").iloc[0] + _n(tw.loc[[i]], "rushing_yards").iloc[0]
           for i, r in tw.iterrows()}  # each team's offensive yards, keyed for the opponent flip
    pbp_map = _pbp_dst(pbp)
    rows = []
    for _, r in tw.iterrows():
        team, wk, opp = r["team"], int(r["week"]), r["opponent_team"]
        ret_yds = (_n(tw.loc[[r.name]], "punt_return_yards").iloc[0]
                   + _n(tw.loc[[r.name]], "kickoff_return_yards").iloc[0]
                   + _n(tw.loc[[r.name]], "def_interception_yards").iloc[0]
                   + _n(tw.loc[[r.name]], "fumble_recovery_yards_opp").iloc[0])
        g = lambda c: _n(tw.loc[[r.name]], c).iloc[0]
        pts = (g("def_sacks") * cfg["sack"] + g("def_interceptions") * cfg["interception"]
               + g("fumble_recovery_opp") * cfg["fumble_recovery"] + g("def_tds") * cfg["td"]
               + g("def_safeties") * cfg["safety"]
               + (g("def_punt_blocks") + g("def_pat_blocks") + g("def_fg_blocks")) * cfg["block_kick"]
               + g("def_tackles_for_loss") * cfg["tackle_for_loss"]
               + ret_yds * cfg["return_yards"] + g("special_teams_tds") * cfg["return_td"])
        yds_allowed = yds.get((opp, r["week"]), 0)
        pbp_d = pbp_map.get((team, wk))
        if pbp_d:
            pts += _tier(pbp_d["pa"], cfg["points_allowed"])
            pts += pbp_d["three_outs"] * cfg["three_and_out"] + pbp_d["stops"] * cfg["fourth_down_stop"]
        pts += _tier(yds_allowed, cfg["yards_allowed"])
        rows.append({"team": team, "week": wk, "opp": opp, "pts_dst": round(pts, 1),
                     "has_pbp": pbp_d is not None})
    return pd.DataFrame(rows)
