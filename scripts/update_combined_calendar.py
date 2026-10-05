#!/usr/bin/env python3
import datetime as dt
import html
import json
import re
import urllib.request
from html.parser import HTMLParser

TEAMS = [
    ("Lazio U20", 826821, "sofascore"),
    ("Roma U20", 340799, "sofascore"),
    ("Lecce U20", 826809, "sofascore"),
    ("Bari Serie C", 2712, "sofascore"),
    ("Barletta Serie C", 25154, "sofascore"),
    ("Gubbio Serie C", 2782, "sofascore"),
    ("Juventus Next Gen Serie C", 294884, "sofascore"),
    ("FC Zürich U19", 197188, "asf_u19"),
    ("FC Zürich U17", 1266172, "asf_u17"),
    ("Grasshopper U19", 325671, "asf_u19"),
    ("Grasshopper U17", 1124697, "asf_u17"),
    ("Palermo U20", 64119, "sofascore"),
    ("Hellas Verona U17", 1145924, "tuttocampo_u17_ab_b"),
    ("Torino U17", 1145811, "tuttocampo_u17_ab_a"),
    ("Arezzo U17", 933397, "tuttocampo_u17_c"),
]

OUTPUT = "calendario-completo.ics"

ASF_URLS = {
    "asf_u17": "https://matchcenter.football.ch/default.aspx?a=mag&ln=15061&lng=3&ls=25702&oid=1&s=2027&sg=70083",
    "asf_u19": "https://matchcenter.football.ch/default.aspx?a=mag&ln=15041&lng=3&ls=25704&oid=1&s=2027&sg=70085",
}

TUTTOCAMPO_URLS = {
    "tuttocampo_u17_ab_a": "https://www.tuttocampo.it/Italia/AllieviNazionaliU17/GironeASerieAB/Calendario",
    "tuttocampo_u17_ab_b": "https://www.tuttocampo.it/Italia/AllieviNazionaliU17/GironeBSerieAB/Calendario",
    "tuttocampo_u17_c": "https://www.tuttocampo.it/Italia/AllieviNazionaliU17/GironeCSerieC/Calendario",
}

def fetch_url(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; LazioPrimaveraICS/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def fetch_sofascore_events(team_id):
    events = {}
    for page in range(5):
        url = f"https://www.sofascore.com/api/v1/team/{team_id}/events/next/{page}"
        try:
            data = json.loads(fetch_url(url))
        except Exception:
            continue
        for event in data.get("events", []):
            eid = event.get("id")
            if eid:
                events[eid] = event
    return list(events.values())

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
            self.buf = []

    def handle_data(self, data):
        if self.cell is not None:
            self.buf.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.buf).split()))
            self.cell = None
            self.buf = []
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None

def parse_date_time(text, current_year):
    patterns = [
        r"(\d{2})[./-](\d{2})[./-](\d{4}).*?(\d{1,2}):(\d{2})",
        r"(\d{2})[./-](\d{2}).*?(\d{1,2}):(\d{2})",
    ]
    for p in patterns:
        m = re.search(p, text)
        if not m:
            continue
        if len(m.groups()) == 5:
            day, month, year, hour, minute = map(int, m.groups())
        else:
            day, month, hour, minute = map(int, m.groups())
            year = current_year
        try:
            return dt.datetime(year, month, day, hour, minute, tzinfo=dt.timezone.utc)
        except ValueError:
            return None
    return None

def fetch_tuttocampo_events(source_key, wanted_team):
    url = TUTTOCAMPO_URLS[source_key]
    try:
        page = fetch_url(url)
    except Exception:
        return []

    parser = TableParser()
    parser.feed(html.unescape(page))
    out = []
    current_year = dt.datetime.now().year

    for row in parser.rows:
        text = " | ".join(row)
        if wanted_team.lower() not in text.lower():
            continue
        when = parse_date_time(text, current_year)
        if not when:
            continue

        teams = []
        for cell in row:
            if "-" in cell:
                parts = [p.strip() for p in re.split(r"\s+-\s+", cell) if p.strip()]
                if len(parts) == 2:
                    teams = parts
                    break
        if len(teams) != 2:
            continue

        event_key = f"{source_key}:{when.isoformat()}:{teams[0]}:{teams[1]}"
        out.append({
            "id": event_key,
            "startTimestamp": int(when.timestamp()),
            "homeTeam": {"name": teams[0]},
            "awayTeam": {"name": teams[1]},
            "url": url,
        })
    return out

def fetch_asf_events(source_key, wanted_team):
    try:
        page = fetch_url(ASF_URLS[source_key])
    except Exception:
        return []

    parser = TableParser()
    parser.feed(html.unescape(page))
    out = []
    current_year = dt.datetime.now().year

    for row in parser.rows:
        text = " | ".join(row)
        if wanted_team.lower() not in text.lower():
            continue
        if "Grasshopper" in wanted_team:
            team_match = "Grasshopper Club Zürich"
        else:
            team_match = "FC Zürich"
        if team_match.lower() not in text.lower():
            continue

        when = parse_date_time(text, current_year)
        if not when:
            continue

        names = []
        for cell in row:
            if team_match.lower() in cell.lower():
                parts = [p.strip() for p in re.split(r"\s+-\s+", cell) if p.strip()]
                if len(parts) == 2:
                    names = parts
                    break
        if len(names) != 2:
            continue

        event_key = f"{source_key}:{when.isoformat()}:{names[0]}:{names[1]}"
        out.append({
            "id": event_key,
            "startTimestamp": int(when.timestamp()),
            "homeTeam": {"name": names[0]},
            "awayTeam": {"name": names[1]},
            "url": ASF_URLS[source_key],
        })
    return out

def esc(value):
    return str(value or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def utc_stamp(ts):
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

now = dt.datetime.now(dt.timezone.utc)
cutoff = now - dt.timedelta(days=2)
all_events = []

for team_name, team_id, source in TEAMS:
    if source == "sofascore":
        events = fetch_sofascore_events(team_id)
        source_url = None
    elif source.startswith("asf_"):
        events = fetch_asf_events(source, team_name)
        source_url = ASF_URLS[source]
    else:
        events = fetch_tuttocampo_events(source, team_name)
        source_url = TUTTOCAMPO_URLS[source]

    # Fallback per resilienza: se la fonte speciale non restituisce dati,
    # manteniamo comunque il calendario aggiornato tramite SofaScore.
    if not events and source != "sofascore":
        events = fetch_sofascore_events(team_id)
        source_url = None

    for event in events:
        ts = event.get("startTimestamp")
        if not ts:
            continue
        start = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
        if start < cutoff:
            continue
        home = event.get("homeTeam", {}).get("name", "Casa")
        away = event.get("awayTeam", {}).get("name", "Trasferta")
        event_id = event["id"]
        event_url = event.get("url") or f"https://www.sofascore.com/event/{event_id}"
        all_events.append((ts, team_name, home, away, event_url, event_id, source))

all_events.sort(key=lambda x: (x[0], x[1], str(x[5])))

lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Roberto Ficerai//Calendario Calcio Giovanile Completo//IT",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Calcio Giovanile - Calendario Completo",
    "X-WR-TIMEZONE:Europe/Rome",
]

stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

for ts, team_name, home, away, event_url, event_id, source in all_events:
    uid = f"{team_name.lower().replace(' ', '-').replace('ü','u')}-{event_id}@lazio-primavera-ics"
    summary = f"[{team_name}] {home} - {away}"
    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{esc(uid)}",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{utc_stamp(ts)}",
        f"DTEND:{utc_stamp(ts + 7200)}",
        f"SUMMARY:{esc(summary)}",
        f"CATEGORIES:{esc(team_name)}",
        f"URL:{event_url}",
        f"X-SOURCE:{esc(source)}",
        "END:VEVENT",
    ])

lines.append("END:VCALENDAR")

with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")

print(f"Generated {OUTPUT}: {len(all_events)} events")
