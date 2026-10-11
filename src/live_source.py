"""Live in-game scoring from free APIs, at league 672352 settings.

Sleeper (api.sleeper.app, no key) carries the full league in flat per-stat fields — including
the two things the nflverse aggregate and ESPN's box both miss: per-player first downs
(rush_fd/rec_fd, 5 pts each) and team-DST three-and-outs / fourth-down stops. So Sleeper is
the scoring source; ESPN's scoreboard (also no key) supplies per-team game state (pre/in/post).

Verified 2026 W5: Dallas DST = 219 (matches Yahoo). Offense reuses scoring.score_players by
mapping Sleeper fields to nflverse columns, so one engine scores both live and post-game.

Not self-updating: call live_week() on demand. Sleeper updates during games; nflverse remains
the exact post-game verifier.
"""
import json, urllib.request, pathlib, time
import pandas as pd
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scoring import score_players, load_scoring, _tier
from availability import std_name

ROOT = pathlib.Path(__file__).resolve().parents[1]
SLEEPER = "https://api.sleeper.app/v1"
ESPN_SB = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

# Sleeper stat key -> nflverse column score_players() expects
OFF_MAP = {
    "pass_yd": "passing_yards", "pass_td": "passing_tds", "pass_int": "passing_interceptions",
    "pass_2pt": "passing_2pt_conversions",
    "rush_att": "carries", "rush_yd": "rushing_yards", "rush_td": "rushing_tds",
    "rush_fd": "rushing_first_downs", "rush_2pt": "rushing_2pt_conversions",
    "rec": "receptions", "rec_yd": "receiving_yards", "rec_td": "receiving_tds",
    "rec_fd": "receiving_first_downs", "rec_2pt": "receiving_2pt_conversions",
    "fum_lost": "fumbles_lost_total", "pr_yd": "punt_return_yards", "kr_yd": "kickoff_return_yards",
    "st_td": "special_teams_tds",
    # IDP (~half the lineup) — Sleeper carries these; score_players sums them too
    "idp_tkl_solo": "def_tackles_solo", "idp_tkl_ast": "def_tackle_assists",
    "idp_sack": "def_sacks", "idp_tkl_loss": "def_tackles_for_loss",
    "idp_int": "def_interceptions", "idp_ff": "def_fumbles_forced",
    "idp_fum_rec": "fumble_recovery_opp", "idp_pass_def": "def_pass_defended",
    "idp_def_td": "def_tds", "idp_safe": "def_safeties", "idp_blk_kick": "def_fg_blocks",
    "idp_int_ret_yd": "def_interception_yards", "idp_fum_ret_yd": "fumble_recovery_yards_opp",
}


def _get(url, timeout=25):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def current_week():
    """Live NFL week from Sleeper's state endpoint (no parquet needed)."""
    return int(_get(f"{SLEEPER}/state/nfl")["week"])


def _player_map():
    """std_name -> sleeper player meta (id, team, pos). Cached (~5MB); refreshed weekly."""
    cache = ROOT / "data" / "sleeper_players.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < 7 * 86400:
        players = json.loads(cache.read_text())
    else:
        players = _get(f"{SLEEPER}/players/nfl")
        cache.write_text(json.dumps(players))
    m = {}
    for pid, p in players.items():
        nm = p.get("full_name") or p.get("last_name")
        if not nm:
            continue
        m.setdefault(std_name(nm), {"id": pid, "team": p.get("team"), "pos": p.get("position")})
    return m


def _espn_state(season, week):
    """team abbrev -> game state 'pre' | 'in' | 'post' for the week."""
    try:
        sb = _get(f"{ESPN_SB}?dates={season}&seasontype=2&week={week}")
    except Exception:
        return {}
    st = {}
    for e in sb.get("events", []):
        state = e["status"]["type"]["state"]
        for c in e["competitions"][0]["competitors"]:
            st[c["team"]["abbreviation"]] = state
    return st


def _dst_points(st, cfg):
    g = lambda k: float(st.get(k, 0) or 0)
    ret = g("def_kr_yd") + g("def_pr_yd") + g("int_ret_yd") + g("fum_ret_yd")
    return (g("sack") * cfg["sack"] + g("int") * cfg["interception"]
            + (g("def_st_fum_rec") + g("fum_rec")) * cfg["fumble_recovery"]
            + g("def_td") * cfg["td"] + g("safe") * cfg["safety"]
            + g("tkl_loss") * cfg["tackle_for_loss"] + ret * cfg["return_yards"]
            + g("def_3_and_out") * cfg["three_and_out"] + g("def_4_and_stop") * cfg["fourth_down_stop"]
            + _tier(g("pts_allow"), cfg["points_allowed"]) + _tier(g("yds_allow"), cfg["yards_allowed"]))


# nflverse team codes that differ from Sleeper/ESPN
TEAM_ALIAS = {"LA": "LAR", "WSH": "WAS", "JAC": "JAX"}


def live_week(season, week):
    """Return {player_pts{std_name->pts}, dst_pts{team->pts}, state{team->pre|in|post}}."""
    cfg = load_scoring()
    stats = _get(f"{SLEEPER}/stats/nfl/regular/{season}/{week}")
    pmap = _player_map()
    id2key = {v["id"]: k for k, v in pmap.items()}

    # offense: build an nflverse-shaped frame from Sleeper player rows, then score with the engine
    rows = []
    for pid, st in stats.items():
        key = id2key.get(pid)
        if key is None:                 # DST entries are keyed by team abbrev, handled below
            continue
        row = {"player_display_name": key, "position": pmap[key].get("pos") or "WR"}
        for sk, col in OFF_MAP.items():
            row[col] = st.get(sk, 0) or 0
        rows.append(row)
    player_pts = {}
    if rows:
        df = score_players(pd.DataFrame(rows), cfg)
        player_pts = dict(zip(df["player_display_name"], df["pts"]))

    dcfg = cfg["team_dst"]
    dst_pts = {}
    for t, st in stats.items():
        if t.isalpha() and t.isupper() and len(t) <= 3 and ("pts_allow" in st or "def_3_and_out" in st):
            dst_pts[TEAM_ALIAS.get(t, t)] = round(_dst_points(st, dcfg), 1)

    state = {TEAM_ALIAS.get(t, t): s for t, s in _espn_state(season, week).items()}
    return {"player_pts": player_pts, "dst_pts": dst_pts, "state": state, "week": week, "season": season}


if __name__ == "__main__":
    import sys as _s
    season = int(_s.argv[1]) if len(_s.argv) > 1 else 2026
    week = int(_s.argv[2]) if len(_s.argv) > 2 else 5
    d = live_week(season, week)
    print(f"W{week}: {len(d['player_pts'])} players, {len(d['dst_pts'])} DSTs, {len(d['state'])} game states")
    print("DAL DST:", d["dst_pts"].get("DAL"), "| G.Pickens:", d["player_pts"].get(std_name("George Pickens")))
