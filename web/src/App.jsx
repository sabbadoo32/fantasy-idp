import { useState } from "react";
import { useData } from "./useData.js";
import Tracker from "./Tracker.jsx";
import Grid from "./Grid.jsx";
import Analysis from "./Analysis.jsx";

export default function App() {
  const [tab, setTab] = useState("tracker");
  const live = useData("/data/live.json", 45000);   // poll every 45s during games
  const grid = useData("/data/matchups.json", 600000); // every 10 min (daily data)
  const report = useData("/data/report.json", 600000);

  const stale = (fetchedAt) => fetchedAt && Date.now() - fetchedAt > 180000;

  return (
    <div className="wrap">
      <h1>Team Work</h1>
      <div className="sub">
        1 Point per Yard League · #672352
        {live.error && <span className="stale"> · live feed unreachable</span>}
      </div>

      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "tracker"} onClick={() => setTab("tracker")}>Live Tracker</button>
        <button role="tab" aria-selected={tab === "grid"} onClick={() => setTab("grid")}>Matchup Grid</button>
        <button role="tab" aria-selected={tab === "analysis"} onClick={() => setTab("analysis")}>Analysis</button>
      </div>

      {tab === "tracker" ? <Tracker data={live.data} error={live.error} />
        : tab === "grid" ? <Grid data={grid.data} error={grid.error} />
        : <Analysis data={report.data} error={report.error} />}
    </div>
  );
}
