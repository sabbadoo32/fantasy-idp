const num = (v) => (v == null ? "—" : Math.round(v));

function Section({ title, note, children }) {
  return (
    <div style={{ marginTop: 26 }}>
      <h2 style={{ fontFamily: "var(--display)", textTransform: "uppercase", fontSize: 16, letterSpacing: ".04em", margin: "0 0 8px" }}>
        {title}{note && <span style={{ fontFamily: "var(--body)", textTransform: "none", letterSpacing: 0, color: "var(--muted)", fontSize: 12, fontWeight: 400 }}> {note}</span>}
      </h2>
      {children}
    </div>
  );
}

export default function Analysis({ data, error }) {
  if (error && !data) return <p className="foot">Analysis unreachable ({error}).</p>;
  if (!data) return <p className="foot">Loading analysis…</p>;

  return (
    <>
      <div className="sub">Through Week {data.week} · season-to-date PPG at league scoring · {data.availability} · {data.generated}</div>

      <Section title="Your roster" note="PPG · L2 · snap · pos rank">
        <div className="scroll">
          <table>
            <thead><tr><th>Slot</th><th style={{ textAlign: "left" }}>Player</th><th>PPG</th><th>L2</th><th>Snap</th><th style={{ textAlign: "left" }}>Rank</th><th style={{ textAlign: "left" }}>Flags</th></tr></thead>
            <tbody>
              {data.roster.map((r, i) => (
                <tr key={i}>
                  <th>{r.slot}</th>
                  <td style={{ textAlign: "left", fontFamily: "var(--body)" }}>{r.name}</td>
                  <td style={{ fontWeight: r.ppg >= 150 ? 600 : 400 }}>{num(r.ppg)}</td>
                  <td>{num(r.l2)}</td>
                  <td>{r.snap}</td>
                  <td style={{ textAlign: "left", color: "var(--muted)" }}>{r.rank}</td>
                  <td style={{ textAlign: "left", color: "var(--opp)", fontFamily: "var(--body)", fontSize: 12 }}>{r.flags}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Start / sit" note="bench outscoring a starter">
        {data.start_sit.length === 0 ? <p className="foot" style={{ border: 0, margin: 0 }}>None.</p> :
          data.start_sit.map((s, i) => (
            <p key={i} style={{ margin: "4px 0", fontSize: 14 }}>
              <b style={{ color: "var(--live)" }}>Start {s.start}</b> over {s.over} — {Math.round(s.ppg)} vs {Math.round(s.vs)} PPG
              <span style={{ color: "var(--live)", fontFamily: "var(--mono)" }}> ({s.delta > 0 ? "+" : ""}{s.delta})</span>
              {s.flags && <span style={{ color: "var(--opp)", fontSize: 12 }}> · {s.flags}</span>}
            </p>
          ))}
      </Section>

      <Section title="Recommended adds" note={`clear +${data.edge} PPG over your weakest starter`}>
        {data.adds.length === 0 ? <p className="foot" style={{ border: 0, margin: 0 }}>None clear.</p> :
          data.adds.map((a, i) => (
            <p key={i} style={{ margin: "4px 0", fontSize: 14 }}>
              <b>{a.name}</b> <span style={{ color: "var(--muted)" }}>({a.team}, {a.grp})</span> over {a.over} —
              <span style={{ fontFamily: "var(--mono)" }}> {Math.round(a.ppg)} vs {Math.round(a.vs)} (+{a.delta})</span>, {a.games} gm
              {a.flags && <span style={{ color: "var(--opp)", fontSize: 12 }}> · {a.flags}</span>}
            </p>
          ))}
      </Section>

      <Section title="DST watch" note="top team defenses to date (yours ★)">
        <div className="scroll">
          <table>
            <thead><tr><th style={{ textAlign: "left" }}>Team</th><th>DST PPG</th><th>L2</th><th>Rank</th></tr></thead>
            <tbody>
              {data.dst_watch.map((d) => (
                <tr key={d.team}>
                  <th className={d.mine ? "mine" : ""}>{d.team}{d.mine ? " ★" : ""}</th>
                  <td>{Math.round(d.ppg)}</td><td>{Math.round(d.l2)}</td><td><span className="r">#{d.rank}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Waiver watch" note="available on your wire, vs your weakest starter">
        {Object.entries(data.waiver).map(([grp, g]) => (
          <div key={grp} style={{ marginBottom: 14 }}>
            <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--muted)", margin: "8px 0 4px" }}>
              {grp}{g.weakest && ` — your weakest: ${g.weakest.name}, ${Math.round(g.weakest.ppg)} PPG`}
            </div>
            <div className="scroll">
              <table>
                <thead><tr><th style={{ textAlign: "left" }}>Player</th><th>Tm</th><th>PPG</th><th>L2</th><th>Snap</th><th>vs yours</th><th style={{ textAlign: "left" }}>Flags</th></tr></thead>
                <tbody>
                  {g.players.map((p, i) => (
                    <tr key={i}>
                      <td style={{ textAlign: "left", fontFamily: "var(--body)" }}>{p.name}</td>
                      <td style={{ color: "var(--muted)" }}>{p.team}</td>
                      <td>{Math.round(p.ppg)}</td><td>{num(p.l2)}</td><td>{p.snap}</td>
                      <td style={{ color: p.delta >= data.edge ? "var(--live)" : "var(--muted)" }}>{p.delta == null ? "" : (p.delta > 0 ? "+" : "") + p.delta}</td>
                      <td style={{ textAlign: "left", color: "var(--opp)", fontFamily: "var(--body)", fontSize: 12 }}>{p.flags}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </Section>

      <p className="foot">
        Season-to-date PPG (early weeks are noise). Waiver watch is filtered to players actually available on your wire.
        Injury feed lags breaking news — confirm every name before acting. Team DST is scored and included.
      </p>
    </>
  );
}
