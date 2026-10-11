"""Weekly report: score everyone at league 672352 settings, place my roster, and rank
the players actually available on my Yahoo wire against my weakest starter at each slot.

Usage: python src/report.py            # latest season/week in data/
       python src/report.py 2026 3     # specific season, through week

Ranking metric: season-to-date PPG (CLAUDE.md: early weeks are noise). L2 PPG and snap
share are shown as trend signals, not used to rank. Writes reports/week_<season>_<week>.md.
"""
import sys, pathlib, yaml, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scoring import score_players
from availability import std_name, load as load_taken

ROOT = pathlib.Path(__file__).resolve().parents[1]
SLOT_GRP = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE", "K": "K",
            "DB": "IDP-DB", "DL": "IDP-DL", "LB": "IDP-LB"}
WATCH = ["QB", "RB", "WR", "TE", "IDP-LB", "IDP-DB", "IDP-DL", "K"]
MIN_GAMES = 2
EDGE = 15  # PPG margin over weakest starter before calling it an upgrade

def load_roster():
    r = yaml.safe_load(open(ROOT / "league" / "roster.yaml"))
    rows = []
    for slot, ps in r["starters"].items():
        for p in ps:
            rows.append({"key": std_name(p["name"]), "name": p["name"], "slot": slot,
                         "role": "start", "roster_team": p.get("team")})
    for role in ("bench", "ir"):
        for p in r.get(role, []):
            rows.append({"key": std_name(p["name"]), "name": p["name"], "slot": role.upper(),
                         "role": role, "roster_team": p.get("team")})
    return pd.DataFrame(rows)


def dst_table(season, through):
    """Team DST season-to-date at league scoring: PPG, L2, games, rank by team."""
    tp = ROOT / "data" / f"stats_team_week_{season}.parquet"
    if not tp.exists():
        return None
    from scoring import score_team_dst
    tw = pd.read_parquet(tp)
    tw = tw[tw["week"] <= through]
    pp = ROOT / "data" / f"pbp_{season}.parquet"
    pbp = pd.read_parquet(pp) if pp.exists() else None
    d = score_team_dst(tw, pbp)
    g = d.groupby("team").agg(games=("pts_dst", "size"),
                              ppg=("pts_dst", "mean"),
                              l2=("pts_dst", lambda s: s.tail(2).mean())).round(1)
    g["rank"] = g["ppg"].rank(ascending=False).astype(int)
    return g

def snaps(season, through):
    p = ROOT / "data" / f"snap_counts_{season}.parquet"
    if not p.exists():
        return None
    s = pd.read_parquet(p)
    s = s[s["week"] <= through].copy()
    s["key"] = s["player"].map(std_name)
    s["pct"] = s[["offense_pct", "defense_pct"]].max(axis=1) * 100
    last = s[s["week"] == through].groupby("key")["pct"].max().rename("snap_last")
    avg = s.groupby("key")["pct"].mean().rename("snap_avg")
    return pd.concat([last, avg], axis=1).reset_index()

def health(season, through):
    """Per-player status for the coming week, from nflverse. Lags real news by a day or
    more (Achane's season-ending ACL wasn't coded 3 days later), so every recommended
    name still gets a news check before acting — see CLAUDE.md."""
    d = ROOT / "data"
    rp, ip = d / f"roster_weekly_{season}.parquet", d / f"injuries_{season}.parquet"
    if not rp.exists():
        return None
    ros = pd.read_parquet(rp)[["gsis_id", "week", "status", "status_description_abbr"]]
    latest_wk = int(ros["week"].max())
    last = ros.sort_values("week").groupby("gsis_id").tail(1).set_index("gsis_id")
    st = pd.DataFrame(index=last.index)
    st["roster_status"] = last["status"]
    st["roster_wk"] = last["week"]
    st["latest_wk"] = latest_wk
    if ip.exists():
        inj = pd.read_parquet(ip)
        inj = inj[inj["week"] >= through].sort_values("week").groupby("gsis_id").tail(1).set_index("gsis_id")
        st = st.join(inj[["week", "report_status", "report_primary_injury", "practice_status"]].rename(
            columns={"week": "inj_wk"}), how="outer")
    return st.reset_index().rename(columns={"index": "player_id", "gsis_id": "player_id"})

def status_tag(x):
    """Return (tag, unavailable_bool)."""
    rs, rep = x.get("roster_status"), x.get("report_status")
    if rs == "RES":
        return "IR/reserve", True
    upcoming = pd.notna(x.get("inj_wk")) and x["inj_wk"] > x.get("through", 0)
    if isinstance(rep, str) and rep in ("Out", "Doubtful") and upcoming:
        return f"{rep} W{int(x['inj_wk'])} ({x.get('report_primary_injury')})", rep == "Out"
    if rs in ("CUT", "RET", "EXE"):
        return f"roster status {rs}", True
    if pd.notna(x.get("roster_wk")) and x["roster_wk"] < x["latest_wk"]:
        return f"not on W{int(x['latest_wk'])} roster — check news", False
    tags = []
    if isinstance(rep, str):
        tags.append(f"{rep} W{int(x['inj_wk'])} ({x.get('report_primary_injury')})")
    elif isinstance(x.get("practice_status"), str) and "Full" not in x["practice_status"]:
        tags.append(f"{x['practice_status'].replace(' Participation in Practice', '')} practice ({x.get('report_primary_injury') or 'injury'})")
    return "; ".join(tags), False

def season_table(df, through):
    df = score_players(df[df["week"] <= through])
    df = df[df["grp"].notna()]
    keys = ["player_id", "player_display_name", "position", "grp"]
    df = df.assign(ret_pts=df["punt_return_yards"].fillna(0) + df["kickoff_return_yards"].fillna(0))
    agg = df.groupby(keys).agg(games=("week", "nunique"), pts=("pts", "sum"), ret=("ret_pts", "sum"),
                               last_wk=("week", "max"), team=("team", "last")).reset_index()
    last_ret = df[df["week"] == through].groupby("player_id")["ret_pts"].sum().rename("ret_last")
    agg = agg.merge(last_ret, on="player_id", how="left")
    agg["ret_pct"] = (100 * agg["ret"] / agg["pts"].where(agg["pts"] > 0)).fillna(0).round(0)
    agg["ppg"] = (agg["pts"] / agg["games"]).round(1)
    l2 = df[df["week"] > through - 2].groupby("player_id")["pts"].mean().round(1).rename("l2")
    agg = agg.merge(l2, on="player_id", how="left")
    agg["key"] = agg["player_display_name"].map(std_name)
    agg["pos_rank"] = agg.groupby("grp")["ppg"].rank(ascending=False, method="min").astype(int)
    return agg

def flags(x, week):
    f = [x["health"]] if x.get("health") else []
    if x.get("last_wk", week) < week:
        f.append(f"DNP W{week}")
    if x.get("ret_pct", 0) >= 40:
        f.append(f"{x['ret_pct']:.0f}% returns" + (" — 0 ret yds W%d" % week if not x.get("ret_last") else ""))
    return "; ".join(f)

def fmt_snap(x):
    if pd.isna(x.get("snap_last")):
        return "-"
    d = x["snap_last"] - x["snap_avg"]
    arrow = " ↑" if d >= 10 else (" ↓" if d <= -10 else "")
    return f"{x['snap_last']:.0f}%{arrow}"

def main(season=None, week=None):
    if season is None:
        season = max(int(p.stem.split("_")[-1]) for p in (ROOT / "data").glob("stats_player_week_*.parquet"))
    df = pd.read_parquet(ROOT / "data" / f"stats_player_week_{season}.parquet")
    if week is None:
        # The pull can include the live week partially (Sunday games in progress); ranking on
        # it skews season-to-date. Default to the last full slate (matchups.py's guard).
        from matchups import _last_complete_week
        week = _last_complete_week(season, int(df["week"].max()))
    agg = season_table(df, week)
    sn = snaps(season, week)
    if sn is not None:
        agg = agg.merge(sn, on="key", how="left")
    hs = health(season, week)
    if hs is not None:
        agg = agg.merge(hs, on="player_id", how="left")
        agg["through"] = week
        tags = agg.apply(status_tag, axis=1, result_type="expand")
        agg["health"], agg["unavailable"] = tags[0], tags[1].astype(bool)
    else:
        agg["health"], agg["unavailable"] = "", False
    roster = load_roster()
    taken, avail_note = load_taken()
    agg["mine"] = agg["key"].isin(set(roster["key"]))
    agg["available"] = ~agg["mine"] & (~agg["key"].isin(taken) if taken is not None else True)

    out = [f"# Week {week} report — {season} (league 672352)\n",
           f"Through Week {week}. Rank = season-to-date PPG at league scoring (min {MIN_GAMES} games for waiver adds). "
           f"L2 = average of last two weeks. Snap = last-week snap share; ↑/↓ = 10+ points vs his season average.\n",
           f"Availability: {avail_note}.\n",
           "Injury status: nflverse injury reports + roster status (IR/reserve and Out players are excluded "
           "from adds and swaps). It lags breaking news by a day or more — confirm every name below before acting.\n"]

    # --- my roster
    mine = roster.merge(agg, on="key", how="left")
    out.append("## Your roster\n")
    out.append("| Slot | Player | PPG | L2 | Snap | Pos rank | Flags |\n|---|---|---|---|---|---|---|")
    order = {s: i for i, s in enumerate(list(SLOT_GRP) + ["W/T", "W/R", "DEF", "BENCH", "IR"])}
    dstt = dst_table(season, week)
    for _, x in mine.sort_values(by="slot", key=lambda s: s.map(order).fillna(99)).iterrows():
        if x["slot"] == "DEF" and dstt is not None and x.get("roster_team") in dstt.index:
            r = dstt.loc[x["roster_team"]]
            out.append(f"| DEF | {x['name']} | {r['ppg']} | {r['l2']} | - | DST #{int(r['rank'])} | |")
            continue
        if pd.isna(x.get("ppg")):
            out.append(f"| {x['slot']} | {x['name']} | - | - | - | no games yet | |")
            continue
        l2 = "-" if pd.isna(x["l2"]) else x["l2"]
        out.append(f"| {x['slot']} | {x['name']} | {x['ppg']} | {l2} | {fmt_snap(x)} | {x['grp']} #{int(x['pos_rank'])} | {flags(x, week)} |")

    # --- weakest starter per slot group
    floor = {}
    st = mine[(mine["role"] == "start") & mine["slot"].isin(SLOT_GRP)]
    for slot, grp in SLOT_GRP.items():
        s = st[st["slot"] == slot].dropna(subset=["ppg"])
        if len(s):
            w = s.sort_values("ppg").iloc[0]
            floor[grp] = (w["name"], w["ppg"])

    # --- bench vs starters (free upgrades, no transaction needed)
    out.append("\n## Start/sit — bench players outscoring a starter\n")
    bench = mine[(mine["role"] == "bench")].dropna(subset=["ppg"])
    swaps = []
    for _, b in bench.iterrows():
        if b.get("unavailable") is True:
            continue
        fl = floor.get(b["grp"])
        if fl and b["ppg"] - fl[1] >= EDGE:
            swaps.append(f"- **Start {b['name']}** over {fl[0]}: {b['ppg']} vs {fl[1]} PPG "
                         f"({b['ppg'] - fl[1]:+.1f}), L2 {b['l2']}, snap {fmt_snap(b)}. {flags(b, week)}")
    out.extend(swaps or ["None."])

    # --- waiver watch
    pool = agg[agg["available"] & (agg["games"] >= MIN_GAMES) & ~agg["unavailable"]]
    adds = []
    out.append("\n## Waiver watch — available on your wire\n")
    for grp in WATCH:
        sub = pool[pool["grp"] == grp].sort_values("ppg", ascending=False).head(6)
        if not len(sub):
            continue
        fl = floor.get(grp)
        hdr = f"\n### {grp}" + (f" — your weakest starter: {fl[0]}, {fl[1]} PPG" if fl else "")
        out.append(hdr)
        out.append("| Player | Team | PPG | L2 | Snap | Pos rank | vs your starter | Flags |\n|---|---|---|---|---|---|---|---|")
        for _, x in sub.iterrows():
            delta = round(x["ppg"] - fl[1], 1) if fl else None
            out.append(f"| {x['player_display_name']} | {x['team']} | {x['ppg']} | {x['l2']} | {fmt_snap(x)} | "
                       f"#{x['pos_rank']} | {'' if delta is None else f'{delta:+}'} | {flags(x, week)} |")
            if delta is not None and delta >= EDGE:
                adds.append((delta, grp, x, fl))

    # --- DST streaming watch (DST is a WR1-sized category in this league)
    if dstt is not None:
        mine_def = set(mine[mine["slot"].isin(["DEF", "BENCH"])]["roster_team"].dropna())
        top = dstt.sort_values("ppg", ascending=False).head(8)
        out.append("\n## DST watch — top team defenses to date (yours marked ★)\n")
        out.append("| Team | DST PPG | L2 | Rank |\n|---|---|---|---|")
        for tm, r in top.iterrows():
            mark = " ★" if tm in mine_def else ""
            out.append(f"| {tm}{mark} | {r['ppg']} | {r['l2']} | #{int(r['rank'])} |")

    # --- recommendation
    out.append("\n## Recommended adds\n")
    if not adds:
        out.append(f"None clear {EDGE}+ PPG over your weakest starter at any slot.")
    for delta, grp, x, fl in sorted(adds, key=lambda a: -a[0])[:6]:
        out.append(f"- **{x['player_display_name']}** ({x['team']}, {grp}) over {fl[0]}: "
                   f"{x['ppg']} vs {fl[1]} PPG ({delta:+}), {int(x['games'])} games, L2 {x['l2']}, snap {fmt_snap(x)}. {flags(x, week)}")
    out.append("\nNot accounted for: byes, Week " + str(week + 1) + " matchups. "
               "Injury news newer than the nflverse feed — check each name.")

    dst = ROOT / "reports"; dst.mkdir(exist_ok=True)
    path = dst / f"week_{season}_{week}.md"
    path.write_text("\n".join(out) + "\n")
    print("wrote", path)
    return path

if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]
    main(*(a or [None]))
