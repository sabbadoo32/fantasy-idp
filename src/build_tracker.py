"""Render the live matchup JSON into a scoreboard page (reports/live_matchup.html).

Republish as an artifact after each run. It's a snapshot stamped with its data time, not
self-updating. Usage: python src/live_matchup.py && python src/build_tracker.py
"""
import sys, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

TEMPLATE = """<title>Matchup Tracker</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=Oswald:wght@500;600&display=swap">
<style>
/* Layout: a live scoreboard — two team totals head to head, then their starters side by side. */
:root{
  --bg:#f4f5f7; --surface:#fff; --line:#d9dce2; --fg:#15181d; --muted:#5b6472;
  --me:#1f6feb; --opp:#b8352b; --live:#1f8a4c; --pending:#9aa4b2; --dst:#8a5a1f; --dst-bg:#f3e6cf;
  --display:"Oswald",system-ui,sans-serif; --body:"IBM Plex Sans",system-ui,sans-serif; --mono:"IBM Plex Mono",ui-monospace,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0f1216; --surface:#171b21; --line:#2a2f37; --fg:#e8eaed; --muted:#9aa4b2;
  --me:#4b8bff; --opp:#e4584c; --live:#49c47a; --pending:#5b6472; --dst:#d9a85a; --dst-bg:#33260f; color-scheme:dark;
}}
:root[data-theme="dark"]{
  --bg:#0f1216; --surface:#171b21; --line:#2a2f37; --fg:#e8eaed; --muted:#9aa4b2;
  --me:#4b8bff; --opp:#e4584c; --live:#49c47a; --pending:#5b6472; --dst:#d9a85a; --dst-bg:#33260f; color-scheme:dark;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:var(--body);line-height:1.4}
.wrap{max-width:860px;margin:0 auto;padding-block:20px 48px;padding-inline:16px}
h1{font-family:var(--display);text-transform:uppercase;font-size:clamp(24px,5vw,36px);margin:0;letter-spacing:.01em}
.sub{color:var(--muted);font-size:13px;margin:2px 0 18px}
.score{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:10px;
  background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:8px}
.score .team{font-family:var(--display);text-transform:uppercase;font-size:15px;letter-spacing:.03em}
.score .me .team{color:var(--me)} .score .opp{text-align:right} .score .opp .team{color:var(--opp)}
.score .tot{font-family:var(--mono);font-weight:600;font-size:clamp(30px,8vw,52px);font-variant-numeric:tabular-nums;line-height:1}
.score .vs{font-family:var(--display);color:var(--muted);font-size:13px}
.score .pend{font-size:11px;color:var(--muted);font-family:var(--mono)}
.lead{font-size:12px;color:var(--muted);text-align:center;margin-bottom:18px}
.lead b{color:var(--fg)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media (max-width:560px){.cols{grid-template-columns:1fr}}
.col h2{font-family:var(--display);text-transform:uppercase;font-size:13px;letter-spacing:.04em;margin:0 0 6px;padding-bottom:4px;border-bottom:2px solid var(--line)}
.col.me h2{color:var(--me)} .col.opp h2{color:var(--opp)}
.row{display:grid;grid-template-columns:2.2em 1fr auto;gap:8px;align-items:baseline;padding:5px 2px;border-bottom:1px solid var(--line);font-size:13px}
.row .slot{font-family:var(--mono);font-size:10px;color:var(--muted)}
.row .nm{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.row .pt{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right}
.row.done .pt{color:var(--live);font-weight:600}
.row.todo{opacity:.55} .row.todo .pt{color:var(--pending);font-size:11px}
.row.dst .nm::after{content:"DST";font-family:var(--mono);font-size:9px;background:var(--dst-bg);color:var(--dst);padding:1px 4px;border-radius:3px;margin-left:6px}
.foot{color:var(--muted);font-size:12px;margin-top:20px;border-top:1px solid var(--line);padding-top:12px}
</style>
<div class="wrap">
  <h1>Matchup Tracker</h1>
  <div class="sub" id="sub"></div>
  <div class="score">
    <div class="me"><div class="team" id="mName"></div><div class="tot" id="mTot" style="color:var(--me)"></div><div class="pend" id="mPend"></div></div>
    <div class="vs">LIVE</div>
    <div class="opp"><div class="team" id="oName"></div><div class="tot" id="oTot" style="color:var(--opp)"></div><div class="pend" id="oPend"></div></div>
  </div>
  <div class="lead" id="lead"></div>
  <div class="cols">
    <div class="col me"><h2 id="mH"></h2><div id="mRows"></div></div>
    <div class="col opp"><h2 id="oH"></h2><div id="oRows"></div></div>
  </div>
  <div class="foot" id="foot"></div>
</div>
<script>
const D=__DATA__;
const g=id=>document.getElementById(id);
g("sub").innerHTML=`1 Point per Yard League (#672352) · Week ${D.week} live · banked points only · updated ${D.generated}`;
function fill(side,nm,tot,pend,h,rows){
  g(nm).textContent=side.name; g(tot).textContent=side.total.toFixed(0);
  g(pend).textContent=`${side.pending} to play`; g(h).textContent=side.name;
  g(rows).innerHTML=side.starters.map(r=>{
    const cls="row "+(r.played?"done":"todo")+(r.is_dst?" dst":"");
    const pt=r.played? r.pts.toFixed(0) : "— to play";
    return `<div class="${cls}"><span class="slot">${r.slot}</span><span class="nm">${r.name}</span><span class="pt">${pt}</span></div>`;
  }).join("");
}
fill(D.me,"mName","mTot","mPend","mH","mRows");
fill(D.opp,"oName","oTot","oPend","oH","oRows");
const diff=D.me.total-D.opp.total, lead=diff>=0?D.me:D.opp;
g("lead").innerHTML = diff===0? "Tied on banked points." :
  `<b>${lead.name}</b> leads by <b>${Math.abs(diff).toFixed(0)}</b> on points already in the books `+
  `(${D.me.pending+D.opp.pending} starters still to play).`;
g("foot").innerHTML="Banked = league-scored output of starters whose games are in the nflverse feed, team DST included. "+
  "Players yet to play show \\u201c\\u2014 to play.\\u201d Snapshot, not self-updating \\u2014 re-run pull + tracker to refresh.";
</script>
"""

def build():
    season = max(int(p.stem.split("_")[-1]) for p in (ROOT/"data").glob("live_matchup_*.json"))
    data = json.loads((ROOT/"data"/f"live_matchup_{season}.json").read_text())
    html = TEMPLATE.replace("__DATA__", json.dumps(data))
    out = ROOT/"reports"/"live_matchup.html"
    out.write_text(html)
    print(f"wrote {out} (W{data['week']}: {data['me']['total']} vs {data['opp']['total']})")
    return out

if __name__ == "__main__":
    build()
