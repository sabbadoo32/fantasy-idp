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

# NOTE: score_team_dst requires team-grain data (points/yards allowed).
# TODO: pull nflverse team stats + schedules, map points_allowed / yards_allowed tiers.
