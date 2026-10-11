"""Yahoo availability for league 672352.

Source of truth: league/taken.txt — every player rostered by any of the 12 teams
(Yahoo players page, status=T, all positions), one std-name key per line. First line
is a comment: '# captured <ISO timestamp> source=<chrome|api>'.

Available = in nflverse data and NOT in taken.txt. Using the taken list (complete,
~27 per team) instead of the free-agent list (thousands, capped by Yahoo's ranking)
means a breakout player Yahoo ranks low is never silently dropped.

Refreshed weekly by tools/yahoo_sync.js run in Chrome (see README). Replace with the
Yahoo API once access is approved — only this file changes.
"""
import pathlib, datetime as dt

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "league" / "taken.txt"
STALE_DAYS = 7
EXPECTED_MIN = 300   # 12 teams x ~27; fewer means the scrape was partial

def std_name(s):
    s = str(s).lower().strip()
    for suf in (" jr.", " jr", " sr.", " sr", " iii", " ii", " iv"):
        if s.endswith(suf):
            s = s[: -len(suf)]
    return "".join(ch for ch in s if ch.isalnum())

def load():
    """Return (taken_keys or None, note). None means availability is unknown."""
    if not PATH.exists():
        return None, "No league/taken.txt — waiver watch is league-wide, not your wire."
    lines = PATH.read_text().splitlines()
    captured = None
    if lines and lines[0].startswith("#"):
        for tok in lines[0][1:].split():
            if tok.startswith("20"):
                try:
                    captured = dt.datetime.fromisoformat(tok)
                except ValueError:
                    pass
    keys = {l.strip() for l in lines if l.strip() and not l.startswith("#")}
    note = f"{len(keys)} rostered players league-wide (Yahoo)"
    if captured:
        note += f", synced {captured:%b %d %I:%M %p}"
        age = (dt.datetime.now(captured.tzinfo) - captured).days
        if age > STALE_DAYS:
            note += f". STALE: {age} days old, resync before acting"
    if len(keys) < EXPECTED_MIN:
        note += f". WARNING: only {len(keys)} taken — sync may be partial"
    return keys, note
