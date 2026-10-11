function Side({ side, which }) {
  return (
    <div className={`col ${which}`}>
      <h2>{side.name}</h2>
      {side.starters.map((r, i) => (
        <div key={i} className={`row ${r.played ? "done" : "todo"}${r.is_dst ? " dst" : ""}`}>
          <span className="slot">{r.slot}</span>
          <span className="nm">{r.name}</span>
          <span className="pt">
            {r.played ? Math.round(r.pts) : "— to play"}
            {r.live && <span className="dot" title="in progress" />}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function Tracker({ data, error }) {
  if (error && !data) return <p className="foot">Live feed unreachable ({error}).</p>;
  if (!data) return <p className="foot">Loading live score…</p>;
  const { me, opp } = data;
  const diff = me.total - opp.total;
  const lead = diff >= 0 ? me : opp;
  const liveN = (me.in_progress || 0) + (opp.in_progress || 0);
  const pend = me.pending + opp.pending;
  return (
    <>
      <div className="sub">Week {data.week} · {data.source || "live"} · updated {data.generated}</div>
      <div className="score">
        <div className="me">
          <div className="team">{me.name}</div>
          <div className="tot" style={{ color: "var(--me)" }}>{Math.round(me.total)}</div>
          <div className="pend">{me.pending} to play</div>
        </div>
        <div className="vs">LIVE</div>
        <div className="opp">
          <div className="team">{opp.name}</div>
          <div className="tot" style={{ color: "var(--opp)" }}>{Math.round(opp.total)}</div>
          <div className="pend">{opp.pending} to play</div>
        </div>
      </div>
      <p className="lead">
        {diff === 0 ? "Tied." : <><b>{lead.name}</b> leads by <b>{Math.abs(Math.round(diff))}</b> ({pend} starters still to play{liveN ? `, ${liveN} in progress` : ""}).</>}
      </p>
      <div className="cols">
        <Side side={me} which="me" />
        <Side side={opp} which="opp" />
      </div>
      <p className="foot">
        Live league scoring from Sleeper (offense, IDP and team DST — per-player first downs and
        three-and-outs / fourth-down stops included); game state from ESPN. A pulsing dot = game in
        progress. nflverse is the exact post-game verifier, so a live figure can differ from the final by a few points.
      </p>
    </>
  );
}
