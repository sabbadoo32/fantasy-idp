"""Render the matchup grid JSON into a standalone HTML page (the artifact UI).

The page is pure presentation over data/matchups_<season>.json plus the current roster's
weekly frames; regenerate it each week and republish to the same artifact URL.

Usage: python src/build_artifact.py   # reads data/matchups_<latest>.json (+ optional
       scratch frames payload via --data PATH), writes reports/matchup_grid.html
"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Current-week starters: (slot, name, position group, opponent defense). Resync from the live
# Yahoo team page each week. A returner (flagged from the data) is scored on the opponent's
# return-yards-allowed, not his listed-position coverage — see memory/review-before-advice.md.
FRAMES = [
    ("QB", "Aaron Rodgers", "QB", "IND"), ("RB", "Jahmyr Gibbs", "RB", "ARI"),
    ("RB", "Brian Robinson", "RB", "BAL"), ("WR", "Kalif Raymond", "WR", "GB"),
    ("WR", "Keon Coleman", "WR", "LAR"), ("WR", "Jalen Brooks", "WR", "DET"),
    ("TE", "T.J. Hockenson", "TE", "NO"), ("W/R", "Keaton Mitchell", "RB", "DEN"),
    ("DEF", "Bengals", "DEF", "MIA"),
    ("DL", "David Bailey", "IDP-DL", "CLE"), ("DL", "Chase Young", "IDP-DL", "MIN"),
    ("LB", "Blake Cashman", "IDP-LB", "NO"), ("LB", "Arvell Reese", "IDP-LB", "WAS"),
    ("DB", "Quentin Lake", "IDP-DB", "BUF"), ("DB", "Talanoa Hufanga", "IDP-DB", "LAC"),
    ("DB", "Hezekiah Masses", "IDP-DB", "NE"),
]


def _nfl_key(name):
    """'Jalen Brooks' -> 'J.Brooks' to match nflverse player_name in player_returns()."""
    parts = name.split()
    return f"{parts[0][0]}.{parts[-1]}" if len(parts) >= 2 else name


def _build_frames(data):
    from matchups import player_returns
    by = {d["team"]: d for d in data["defenses"]}
    try:
        rp = player_returns(season=data["season"], through=data["through_week"])
    except Exception:
        rp = {}
    out = []
    for slot, name, grp, opp in FRAMES:
        d = by.get(opp)
        if grp == "DEF":                       # DST streams on what the opponent OFFENSE yields
            da = d.get("dst_against") if d else None
            f = {"slot": slot, "name": name, "grp": grp, "opp": opp,
                 "allowed": (da["pts"] if da else None), "rank": (da["rank"] if da else None),
                 "levels": None}
            out.append(f)
            continue
        f = {"slot": slot, "name": name, "grp": grp, "opp": opp,
             "allowed": (d["allowed"].get(grp) if d else None),
             "rank": (d["rank"].get(grp) if d else None),
             "levels": (d["levels"] if d else None)}
        prof = rp.get(_nfl_key(name))
        if prof and prof["is_returner"] and d and d.get("returns"):
            f["returner"] = {"ret_ypg": prof["ret_ypg"],
                             "allowed": d["returns"]["ret_yds"], "rank": d["returns"]["ret_rank"]}
        out.append(f)
    return out

TEMPLATE = """<title>Matchup Grid</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Oswald:wght@500;600&display=swap">
<style>
/* Layout: a stat-almanac — sticky header, roster frames row, then a ranked heatmap grid. */
:root {
  --bg:#f4f5f7; --surface:#ffffff; --line:#d9dce2; --fg:#15181d; --muted:#5b6472;
  --accent:#b8352b;            /* almanac red */
  --good:#1f8a4c; --good-bg:#d8f0df; --bad:#c0392b; --bad-bg:#f6dcd8; --mid-bg:#eceef1;
  --ring:#1f6feb;
  --display:"Oswald",system-ui,sans-serif;
  --body:"IBM Plex Sans",system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0f1216; --surface:#171b21; --line:#2a2f37; --fg:#e8eaed; --muted:#9aa4b2;
  --accent:#e4584c; --good:#49c47a; --good-bg:#16351f; --bad:#e26a5c; --bad-bg:#3a1a16;
  --mid-bg:#1e232b; --ring:#4b8bff; color-scheme:dark;
}}
:root[data-theme="dark"]{
  --bg:#0f1216; --surface:#171b21; --line:#2a2f37; --fg:#e8eaed; --muted:#9aa4b2;
  --accent:#e4584c; --good:#49c47a; --good-bg:#16351f; --bad:#e26a5c; --bad-bg:#3a1a16;
  --mid-bg:#1e232b; --ring:#4b8bff; color-scheme:dark;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:var(--body);line-height:1.45}
.wrap{max-width:1040px;margin:0 auto;padding-block:20px 56px;padding-inline:16px}
header.top{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);
  padding-block:10px;border-bottom:2px solid var(--fg);margin-bottom:18px}
h1{font-family:var(--display);font-weight:600;font-size:clamp(26px,5vw,40px);letter-spacing:.01em;
  margin:0;text-transform:uppercase;text-wrap:balance}
.sub{color:var(--muted);font-size:13px;margin-top:2px}
.sub b{color:var(--fg)}
h2{font-family:var(--display);font-weight:500;text-transform:uppercase;letter-spacing:.04em;
  font-size:16px;margin:30px 0 10px;display:flex;align-items:baseline;gap:10px}
h2 .note{font-family:var(--body);text-transform:none;letter-spacing:0;color:var(--muted);font-size:12px;font-weight:400}
/* roster frames */
.frames{display:grid;grid-template-columns:repeat(auto-fill,minmax(176px,1fr));gap:8px}
.card{background:var(--surface);border:1px solid var(--line);border-left-width:4px;border-radius:7px;padding:9px 11px}
.card .slot{font-family:var(--mono);font-size:10px;color:var(--muted);letter-spacing:.08em}
.card .name{font-weight:600;font-size:14px;margin:1px 0 4px;line-height:1.2}
.card .vs{font-size:12px;color:var(--muted)}
.card .val{font-family:var(--mono);font-size:13px;margin-top:5px;display:flex;justify-content:space-between;align-items:baseline}
.card .rank{font-size:11px;padding:1px 6px;border-radius:999px;font-family:var(--body)}
.g-good{border-left-color:var(--good)} .g-good .rank{background:var(--good-bg);color:var(--good)}
.g-bad{border-left-color:var(--bad)} .g-bad .rank{background:var(--bad-bg);color:var(--bad)}
.g-mid{border-left-color:var(--muted)} .g-mid .rank{background:var(--mid-bg);color:var(--muted)}
.card .kr{margin-top:6px;padding-top:6px;border-top:1px dashed var(--line);font-size:11px;color:var(--muted);font-family:var(--mono)}
.card .kr b{color:var(--fg)}
.krtag{font-family:var(--mono);font-size:9px;background:var(--accent);color:#fff;padding:1px 4px;border-radius:3px;letter-spacing:.06em;vertical-align:middle}
/* controls */
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:4px 0 10px}
.controls input{flex:1;min-width:140px;background:var(--surface);border:1px solid var(--line);
  color:var(--fg);border-radius:6px;padding:7px 10px;font-family:var(--body);font-size:13px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:6px;overflow:hidden}
.seg button{background:var(--surface);color:var(--muted);border:0;padding:7px 11px;font-family:var(--mono);
  font-size:12px;cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--fg);color:var(--bg)}
/* grid */
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;min-width:620px;font-variant-numeric:tabular-nums}
th,td{padding:7px 9px;text-align:right;font-family:var(--mono);font-size:13px;white-space:nowrap}
thead th{position:sticky;top:0;background:var(--surface);color:var(--muted);font-weight:500;
  font-size:11px;letter-spacing:.04em;cursor:pointer;border-bottom:1px solid var(--line);user-select:none}
thead th:first-child,tbody th{text-align:left;font-family:var(--display);text-transform:uppercase}
tbody th{background:var(--surface);font-size:14px;letter-spacing:.03em;position:sticky;left:0;border-right:1px solid var(--line)}
tbody tr:nth-child(even) th{background:var(--surface)}
td{color:var(--fg)}
td .r{font-size:9px;color:var(--muted);margin-left:5px}
.mine{outline:2px solid var(--ring);outline-offset:-2px}
th.sorted::after{content:" ▾";color:var(--accent)}
.legend{display:flex;gap:14px;align-items:center;color:var(--muted);font-size:12px;margin-top:10px;flex-wrap:wrap}
.chip{display:inline-block;width:22px;height:12px;border-radius:3px;vertical-align:middle;margin-right:5px}
.foot{color:var(--muted);font-size:12px;margin-top:22px;border-top:1px solid var(--line);padding-top:12px}
</style>

<div class="wrap">
  <header class="top">
    <h1>Matchup Grid</h1>
    <div class="sub" id="subtitle"></div>
  </header>

  <h2>__TEAMNAME__ — Week __WEEK__ frames <span class="note">points your player's position has been allowed per game · rank of 32 (green = favorable)</span></h2>
  <div class="frames" id="frames"></div>

  <h2>League grid <span class="note">points allowed to each position per game, league scoring · click a column to sort · RB splits ground / air</span></h2>
  <div class="controls">
    <input id="search" placeholder="filter defenses… (e.g. DET, MIN)" autocomplete="off">
    <div class="seg" id="rbmode" role="group" aria-label="RB view">
      <button data-m="total" aria-pressed="true">RB total</button>
      <button data-m="ground" aria-pressed="false">ground</button>
      <button data-m="air" aria-pressed="false">air</button>
    </div>
  </div>
  <div class="scroll"><table id="grid"><thead></thead><tbody></tbody></table></div>
  <div class="legend">
    <span><span class="chip" style="background:var(--good-bg)"></span>most generous</span>
    <span><span class="chip" style="background:var(--mid-bg)"></span>middle</span>
    <span><span class="chip" style="background:var(--bad-bg)"></span>stingiest</span>
    <span>· cells ringed in blue are __TEAMNAME__'s Week __WEEK__ matchups</span>
  </div>

  <h2>Return game <span class="note">return yards each defense allows per game · 1 pt/yd here, a value seam · click to sort</span></h2>
  <div class="scroll"><table id="rettbl"><thead></thead><tbody></tbody></table></div>

  <div class="foot" id="foot"></div>
</div>

<script>
const DATA = __DATA__;
const POS = DATA.positions;
const LABEL = {"QB":"QB","RB":"RB","WR":"WR","TE":"TE","K":"K","IDP-DL":"DL","IDP-LB":"LB","IDP-DB":"DB","DEF":"DST","KR":"KR","DST":"DST"};
const mineByTeamPos = {};
(DATA.team_week5||[]).forEach(f=>{ mineByTeamPos[f.opp+"|"+f.grp]=f; });

document.getElementById("subtitle").innerHTML =
  `<b>${DATA.team_name}</b> · 1 Point per Yard League (#672352) · through Week ${DATA.through_week} · generated ${DATA.generated}`;

/* roster frames */
function band(rank){ if(rank==null) return "g-mid"; if(rank<=10) return "g-good"; if(rank>=23) return "g-bad"; return "g-mid"; }
const fr = document.getElementById("frames");
(DATA.team_week5||[]).forEach(f=>{
  const ret=f.returner;                       // returners are judged on the return axis
  const useRank = ret? ret.rank : f.rank;
  const d=document.createElement("div"); d.className="card "+band(useRank);
  const val = f.allowed==null? "—" : f.allowed.toFixed(0);
  const rk = f.rank==null? "" : `<span class="rank">#${f.rank}</span>`;
  const krLine = ret? `<div class="kr">↩ KR specialist · ${ret.ret_ypg.toFixed(0)} ret yds/g ·
     ${f.opp} allows <b>${ret.allowed.toFixed(0)}</b>/g <span class="rank">#${ret.rank}</span></div>` : "";
  const badge = ret? ` <span class="krtag">KR</span>` : "";
  d.innerHTML=`<div class="slot">${f.slot} · ${LABEL[f.grp]||f.grp}${badge}</div>
    <div class="name">${f.name}</div>
    <div class="vs">vs ${f.opp}${f.grp==="DEF"?" offense":" defense"}</div>
    <div class="val"><span>${val}<span style="color:var(--muted)">/g</span></span>${rk}</div>
    ${krLine}`;
  fr.appendChild(d);
});

/* grid */
let rbMode="total", sortCol="WR", sortDir=-1, filter="";
const GRIDCOLS = POS.concat(["KR","DST"]);   // all positions + kick-return + stream-a-D axis
function cellValue(def,pos){
  if(pos==="KR") return def.returns? def.returns.kr_yds : null;
  if(pos==="DST") return def.dst_against? def.dst_against.pts : null;  // DST pts this offense yields
  if(pos==="RB" && rbMode!=="total"){
    const lv=def.levels||{}; return rbMode==="ground"? lv.rb_ground : lv.rb_air;
  }
  return def.allowed[pos];
}
function rankFor(def,pos){
  if(pos==="KR") return def.returns? def.returns.kr_rank : null;
  if(pos==="DST") return def.dst_against? def.dst_against.rank : null;
  return def.rank[pos];
}
function colorFor(rank){ // rank 1..32 -> green..red via blend of theme tokens
  if(rank==null) return "transparent";
  const t=(rank-1)/31;            // 0 generous .. 1 stingy
  const good=[216,240,223], mid=[236,238,241], bad=[246,220,216]; // light-mode bg tokens
  const lerp=(a,b,k)=>a.map((x,i)=>Math.round(x+(b[i]-x)*k));
  const c = t<0.5? lerp(good,mid,t*2) : lerp(mid,bad,(t-0.5)*2);
  return `rgb(${c[0]} ${c[1]} ${c[2]} / .55)`;
}
function render(){
  const thead=document.querySelector("#grid thead"), tbody=document.querySelector("#grid tbody");
  thead.innerHTML="<tr><th data-c='team'>Defense</th>"+GRIDCOLS.map(p=>{
    const lab = p==="RB" && rbMode!=="total" ? "RB "+rbMode : (LABEL[p]||p);
    return `<th data-c='${p}' class='${p===sortCol?"sorted":""}'>${lab}</th>`;
  }).join("")+"</tr>";
  let rows=DATA.defenses.filter(d=>!filter || d.team.toLowerCase().includes(filter));
  rows.sort((a,b)=>{
    if(sortCol==="team") return a.team<b.team?-1:1;
    const va=cellValue(a,sortCol)??-1, vb=cellValue(b,sortCol)??-1; return (va-vb)*sortDir;
  });
  tbody.innerHTML=rows.map(d=>{
    const tds=GRIDCOLS.map(p=>{
      const v=cellValue(d,p); const rank=rankFor(d,p);
      const mine = p==="KR" ? retMine.has(d.team)
                 : p==="DST" ? dstMine.has(d.team)
                 : mineByTeamPos[d.team+"|"+p];
      const bg = (p==="RB"&&rbMode!=="total")? "transparent" : colorFor(rank);
      const rk = (p==="RB"&&rbMode!=="total")? "" : (rank!=null?`<span class='r'>#${rank}</span>`:"");
      return `<td class='${mine?"mine":""}' style='background:${bg}'>${v==null?"—":v.toFixed(0)}${rk}</td>`;
    }).join("");
    return `<tr><th>${d.team}</th>${tds}</tr>`;
  }).join("");
}
document.querySelector("#grid thead").addEventListener("click",e=>{
  const c=e.target.closest("th")?.dataset.c; if(!c) return;
  if(c===sortCol) sortDir*=-1; else {sortCol=c; sortDir=-1;} render();
});
document.getElementById("search").addEventListener("input",e=>{filter=e.target.value.trim().toLowerCase();render();});
document.getElementById("rbmode").addEventListener("click",e=>{
  const b=e.target.closest("button"); if(!b) return;
  rbMode=b.dataset.m; [...e.currentTarget.children].forEach(x=>x.setAttribute("aria-pressed",x===b));
  if(rbMode!=="total"){sortCol="RB";sortDir=-1;} render();
});
const dstMine = new Set((DATA.team_week5||[]).filter(f=>f.grp==="DEF").map(f=>f.opp));
/* return matchups table */
const retMine = new Set((DATA.team_week5||[]).filter(f=>f.returner).map(f=>f.opp));
let retSort="kr_yds", retDir=-1;
const RET_COLS=[["kr_yds","KR yds/g"],["kr_ret","KR ret/g"],["pr_yds","PR yds/g"],["ret_yds","Total/g"]];
function renderRet(){
  const rows=DATA.defenses.filter(d=>d.returns);
  const thead=document.querySelector("#rettbl thead"), tbody=document.querySelector("#rettbl tbody");
  thead.innerHTML="<tr><th data-c='team'>Defense</th>"+RET_COLS.map(([k,l])=>
    `<th data-c='${k}' class='${k===retSort?"sorted":""}'>${l}</th>`).join("")+"</tr>";
  rows.sort((a,b)=> retSort==="team"? (a.team<b.team?-1:1) : (a.returns[retSort]-b.returns[retSort])*retDir);
  const maxr=rows.length;
  tbody.innerHTML=rows.map(d=>{
    const tds=RET_COLS.map(([k])=>{
      const bg = k==="ret_yds"? colorFor(d.returns.ret_rank) : "transparent";
      const rk = k==="ret_yds"? `<span class='r'>#${d.returns.ret_rank}</span>` : "";
      return `<td style='background:${bg}'>${d.returns[k].toFixed(k==="kr_ret"?1:0)}${rk}</td>`;
    }).join("");
    return `<tr><th class='${retMine.has(d.team)?"mine":""}'>${d.team}</th>${tds}</tr>`;
  }).join("");
}
document.querySelector("#rettbl thead").addEventListener("click",e=>{
  const c=e.target.closest("th")?.dataset.c; if(!c) return;
  if(c===retSort) retDir*=-1; else {retSort=c; retDir=-1;} renderRet();
});
renderRet();

document.getElementById("foot").innerHTML =
  "Points allowed = sum of every opposing player's league-scored output at that position, per game, through Week "+DATA.through_week+
  ". KR = kickoff-return yards allowed per game (1 pt/yd here). DST = team-defense points that team's OFFENSE "+
  "yields per game (turnovers, sacks, 3-and-outs, return yards surrendered) — the axis to stream a defense on. "+
  "Ground / air split RB points into rushing vs receiving — a soft second level shows up as high RB air. "+
  "IDP columns are position-group totals and run noisier than skill positions. Source: nflverse, live each run.";
render();
</script>
"""


def build(data_path=None):
    season = max(int(f.stem.split("_")[-1]) for f in ROOT.glob("data/matchups_*.json"))
    default = ROOT / "data" / f"matchups_{season}.json"
    data = json.loads(pathlib.Path(data_path or default).read_text())
    data.setdefault("team_name", "Team Work")
    data.setdefault("week", 5)
    data["team_week5"] = _build_frames(data)
    html = (TEMPLATE
            .replace("__DATA__", json.dumps(data))
            .replace("__TEAMNAME__", data["team_name"])
            .replace("__WEEK__", str(data["week"])))
    out = ROOT / "reports" / "matchup_grid.html"
    out.write_text(html)
    print(f"wrote {out} ({len(html)//1024} KB, {len(data['defenses'])} defenses, {len(data['team_week5'])} frames)")
    return out


if __name__ == "__main__":
    arg = None
    if "--data" in sys.argv:
        arg = sys.argv[sys.argv.index("--data") + 1]
    build(arg)
