import { useMemo, useState } from "react";

const LABEL = { QB: "QB", RB: "RB", WR: "WR", TE: "TE", K: "K", "IDP-DL": "DL", "IDP-LB": "LB", "IDP-DB": "DB", DEF: "DST", KR: "KR", DST: "DST" };

function colorFor(rank) {
  if (rank == null) return "transparent";
  const t = (rank - 1) / 31;
  const good = [216, 240, 223], mid = [236, 238, 241], bad = [246, 220, 216];
  const lerp = (a, b, k) => a.map((x, i) => Math.round(x + (b[i] - x) * k));
  const c = t < 0.5 ? lerp(good, mid, t * 2) : lerp(mid, bad, (t - 0.5) * 2);
  return `rgb(${c[0]} ${c[1]} ${c[2]} / .55)`;
}
const band = (rank) => (rank == null ? "g-mid" : rank <= 10 ? "g-good" : rank >= 23 ? "g-bad" : "g-mid");

function Frames({ data }) {
  const frames = data.team_week5 || [];
  return (
    <div className="frames" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(176px,1fr))", gap: 8, marginBottom: 20 }}>
      {frames.map((f, i) => {
        const ret = f.returner, rank = ret ? ret.rank : f.rank;
        const b = band(rank);
        const color = b === "g-good" ? "var(--live)" : b === "g-bad" ? "var(--opp)" : "var(--muted)";
        return (
          <div key={i} style={{ background: "var(--surface)", border: "1px solid var(--line)", borderLeft: `4px solid ${color}`, borderRadius: 7, padding: "9px 11px" }}>
            <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--muted)", letterSpacing: ".08em" }}>
              {f.slot} · {LABEL[f.grp] || f.grp}{ret && <span style={{ fontFamily: "var(--mono)", fontSize: 9, background: "var(--opp)", color: "#fff", padding: "1px 4px", borderRadius: 3, marginLeft: 6 }}>KR</span>}
            </div>
            <div style={{ fontWeight: 600, fontSize: 14, margin: "1px 0 4px" }}>{f.name}</div>
            <div style={{ fontSize: 12, color: "var(--muted)" }}>vs {f.opp}{f.grp === "DEF" ? " offense" : " defense"}</div>
            <div style={{ fontFamily: "var(--mono)", fontSize: 13, marginTop: 5, display: "flex", justifyContent: "space-between" }}>
              <span>{f.allowed == null ? "—" : Math.round(f.allowed)}<span style={{ color: "var(--muted)" }}>/g</span></span>
              {f.rank != null && <span style={{ fontSize: 11, color }}>#{f.rank}</span>}
            </div>
            {ret && <div style={{ marginTop: 6, paddingTop: 6, borderTop: "1px dashed var(--line)", fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono)" }}>↩ {Math.round(ret.ret_ypg)} ret yds/g · {f.opp} allows <b style={{ color: "var(--fg)" }}>{Math.round(ret.allowed)}</b> #{ret.rank}</div>}
          </div>
        );
      })}
    </div>
  );
}

export default function Grid({ data, error }) {
  const [sortCol, setSortCol] = useState("WR");
  const [sortDir, setSortDir] = useState(-1);
  const [filter, setFilter] = useState("");
  const [rbMode, setRbMode] = useState("total");

  const cellValue = (d, pos) => {
    if (pos === "KR") return d.returns ? d.returns.kr_yds : null;
    if (pos === "DST") return d.dst_against ? d.dst_against.pts : null;
    if (pos === "RB" && rbMode !== "total") return (d.levels || {})[rbMode === "ground" ? "rb_ground" : "rb_air"];
    return d.allowed[pos];
  };
  const rankFor = (d, pos) => {
    if (pos === "KR") return d.returns ? d.returns.kr_rank : null;
    if (pos === "DST") return d.dst_against ? d.dst_against.rank : null;
    return d.rank[pos];
  };

  const { cols, rows, mineByTeamPos, retMine, dstMine } = useMemo(() => {
    if (!data) return { cols: [], rows: [], mineByTeamPos: {}, retMine: new Set(), dstMine: new Set() };
    const cols = data.positions.concat(["KR", "DST"]);
    const mbp = {}, rm = new Set(), dm = new Set();
    (data.team_week5 || []).forEach((f) => {
      if (f.returner) rm.add(f.opp);
      else if (f.grp === "DEF") dm.add(f.opp);
      else mbp[f.opp + "|" + f.grp] = true;
    });
    let rows = data.defenses.filter((d) => !filter || d.team.toLowerCase().includes(filter));
    rows = [...rows].sort((a, b) => {
      if (sortCol === "team") return a.team < b.team ? -1 : 1;
      const va = cellValue(a, sortCol) ?? -1, vb = cellValue(b, sortCol) ?? -1;
      return (va - vb) * sortDir;
    });
    return { cols, rows, mineByTeamPos: mbp, retMine: rm, dstMine: dm };
  }, [data, filter, sortCol, sortDir, rbMode]);

  if (error && !data) return <p className="foot">Grid data unreachable ({error}).</p>;
  if (!data) return <p className="foot">Loading grid…</p>;

  const click = (c) => { if (c === sortCol) setSortDir((d) => -d); else { setSortCol(c); setSortDir(-1); } };

  return (
    <>
      <div className="sub">Through Week {data.through_week} · points allowed to each position per game, league scoring</div>
      <Frames data={data} />
      <div className="controls">
        <input placeholder="filter defenses… (e.g. DET, MIN)" value={filter} onChange={(e) => setFilter(e.target.value.trim().toLowerCase())} />
        <div className="seg" role="group" aria-label="RB view">
          {["total", "ground", "air"].map((m) => (
            <button key={m} aria-pressed={rbMode === m} onClick={() => { setRbMode(m); if (m !== "total") { setSortCol("RB"); setSortDir(-1); } }}>{m === "total" ? "RB total" : m}</button>
          ))}
        </div>
      </div>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th onClick={() => click("team")}>Defense</th>
              {cols.map((p) => (
                <th key={p} className={p === sortCol ? "sorted" : ""} onClick={() => click(p)}>
                  {p === "RB" && rbMode !== "total" ? "RB " + rbMode : LABEL[p] || p}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.team}>
                <th>{d.team}</th>
                {cols.map((p) => {
                  const v = cellValue(d, p), rank = rankFor(d, p);
                  const mine = p === "KR" ? retMine.has(d.team) : p === "DST" ? dstMine.has(d.team) : mineByTeamPos[d.team + "|" + p];
                  const flat = p === "RB" && rbMode !== "total";
                  return (
                    <td key={p} className={mine ? "mine" : ""} style={{ background: flat ? "transparent" : colorFor(rank) }}>
                      {v == null ? "—" : Math.round(v)}
                      {!flat && rank != null && <span className="r">#{rank}</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="foot">
        KR = kickoff-return yards allowed/g (1 pt/yd). DST = team-defense points that team's offense yields/g
        (turnovers, sacks, 3-and-outs, return yards) — the axis to stream a defense on. RB splits ground / air.
        Cells ringed in blue are your Week {data.week || ""} matchups. Source: nflverse.
      </p>
    </>
  );
}
