// Yahoo league 672352 sync — run in Chrome on any football.fantasysports.yahoo.com
// page while signed in (Claude runs it via the Chrome extension's javascript tool).
// Fetches every rostered player (status=T) across all positions plus your team page,
// using your logged-in session. Read-only: it never adds, drops or changes anything.
//
// Result: window.__sync = {captured, taken:[std keys], mine:[{slot,name,team,pos}]}
// Then read it out in chunks of ~60 keys (tool output truncates ~1,000 chars):
//   window.__sync.taken.slice(0,60).join(',')   ...   window.__sync.mine.map(...)
// and write league/taken.txt + league/roster.yaml.
(async () => {
  const L = 'https://football.fantasysports.yahoo.com/f1/672352';
  const key = n => n.toLowerCase().replace(/ (jr\.?|sr\.?|iii|ii|iv)$/, '').replace(/[^a-z0-9]/g, '');
  const tp = r => [...r.querySelectorAll('span')].map(s => s.textContent.trim())
    .find(t => /^[A-Za-z]{2,4} - [A-Z,\/]+$/.test(t)) || '';
  const doc = async u => new DOMParser().parseFromString(
    await fetch(u, { credentials: 'include' }).then(r => r.text()), 'text/html');
  const taken = new Set();
  for (const pos of ['O', 'DP', 'K', 'DEF']) {
    for (let c = 0; c < 1000; c += 25) {
      const d = await doc(`${L}/players?status=T&pos=${pos}&sort=PR&sdir=1&count=${c}`);
      const names = [...d.querySelectorAll('table tbody tr a.name')].map(a => a.textContent.trim());
      names.forEach(n => taken.add(key(n)));
      if (names.length < 25) break;
    }
  }
  const t = await doc(`${L}/1`);  // Team Work = team 1
  const mine = [...t.querySelectorAll('tr')].map(r => {
    const a = r.querySelector('a.name'); if (!a) return null;
    const [team, pos] = tp(r).split(' - ');
    return { slot: (r.querySelector('td') || {}).textContent.trim().slice(0, 4), name: a.textContent.trim(), team, pos };
  }).filter(Boolean);
  window.__sync = { captured: new Date().toISOString(), taken: [...taken], mine };
  return `taken=${taken.size} mine=${mine.length}`;
})();
