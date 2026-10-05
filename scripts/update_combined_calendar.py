#!/usr/bin/env python3
import datetime as dt
import urllib.request
import json

TEAMS = [
    ("Lazio U20", 826821),
    ("Roma U20", 340799),
    ("Lecce U20", 826809),
    ("Bari Serie C", 2712),
    ("Barletta Serie C", 25154),
    ("Gubbio Serie C", 2782),
    ("Juventus Next Gen Serie C", 294884),
    ("FC Zürich U19", 197188),
    ("FC Zürich U17", 1266172),
    ("Grasshopper U19", 325671),
    ("Grasshopper U17", 1124697),
    ("Palermo U20", 64119),
    ("Hellas Verona U17", 1145924),
    ("Torino U17", 1145811),
    ("Arezzo U17", 933397),
    # Fonte: SofaScore per tutte le squadre non gestite da ASF/Tuttocampo.
]

OUTPUT = "calendario-completo.ics"

def fetch_events(team_id):
    events = {}
    for page in range(5):
        url = f"https://www.sofascore.com/api/v1/team/{team_id}/events/next/{page}"
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                data = json.load(r)
        except Exception:
            continue
        for event in data.get("events", []):
            eid = event.get("id")
            if eid:
                events[eid] = event
    return list(events.values())

def esc(value):
    return str(value or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def utc_stamp(ts):
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

now = dt.datetime.now(dt.timezone.utc)
cutoff = now - dt.timedelta(days=2)
all_events = []

for team_name, team_id in TEAMS:
    for event in fetch_events(team_id):
        ts = event.get("startTimestamp")
        if not ts:
            continue
        start = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
        if start < cutoff:
            continue
        home = event.get("homeTeam", {}).get("name", "Casa")
        away = event.get("awayTeam", {}).get("name", "Trasferta")
        event_url = f"https://www.sofascore.com/event/{event['id']}"
        all_events.append((ts, team_name, home, away, event_url, event["id"]))

all_events.sort(key=lambda x: (x[0], x[1], x[5]))

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

for ts, team_name, home, away, event_url, event_id in all_events:
    start = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
    end = start + dt.timedelta(hours=2)
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
        "END:VEVENT",
    ])

lines.append("END:VCALENDAR")

with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")

print(f"Generated {OUTPUT}: {len(all_events)} events")
