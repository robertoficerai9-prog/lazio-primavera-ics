#!/usr/bin/env python3
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

TEAM_ID = 340799
BASE = f"https://api.sofascore.com/api/v1/team/{TEAM_ID}/events/next"
OUT = Path("roma-primavera.ics")

def fetch(page):
    req = urllib.request.Request(f"{BASE}/{page}", headers={"User-Agent": "roma-primavera-ics/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def esc(value):
    return str(value).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n").replace("\r", "")

def dt_utc(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")

events = {}
for page in range(0, 5):
    try:
        data = fetch(page)
    except Exception:
        break
    for e in data.get("events", []):
        events[str(e["id"])] = e
    if not data.get("hasNextPage"):
        break

now = datetime.now(timezone.utc)
lines = [
    "BEGIN:VCALENDAR","VERSION:2.0",
    "PRODID:-//Roma Primavera ICS//SofaScore//IT",
    "CALSCALE:GREGORIAN","METHOD:PUBLISH",
    "X-WR-CALNAME:Roma Primavera","X-WR-TIMEZONE:Europe/Rome"
]

for e in sorted(events.values(), key=lambda x: x.get("startTimestamp", 0)):
    ts = e.get("startTimestamp")
    if not ts or datetime.fromtimestamp(ts, tz=timezone.utc) < now - timedelta(days=2):
        continue
    home = e.get("homeTeam", {}).get("name", "Casa")
    away = e.get("awayTeam", {}).get("name", "Trasferta")
    tournament = e.get("tournament", {}).get("name", "Calcio")
    status = e.get("status", {}).get("type", "notstarted")
    event_id = e["id"]
    end = datetime.fromtimestamp(ts, tz=timezone.utc) + timedelta(hours=2)
    venue = e.get("venue") or {}
    venue_name = venue.get("name") if isinstance(venue, dict) else None
    lines += [
        "BEGIN:VEVENT",
        f"UID:sofascore-roma-u20-{event_id}@roma-primavera-ics",
        f"DTSTAMP:{dt_utc(int(now.timestamp()))}",
        f"DTSTART:{dt_utc(ts)}", f"DTEND:{dt_utc(int(end.timestamp()))}",
        f"SUMMARY:{esc(home + ' - ' + away)}",
        f"DESCRIPTION:{esc(tournament + ' | SofaScore event ' + str(event_id))}",
        f"STATUS:{'CANCELLED' if status == 'canceled' else 'CONFIRMED'}",
        f"URL:https://www.sofascore.com/event/{event_id}"
    ]
    if venue_name:
        lines.append(f"LOCATION:{esc(venue_name)}")
    lines.append("END:VEVENT")

lines.append("END:VCALENDAR")
OUT.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
print(f"Generated {OUT} with {len(events)} SofaScore events.")
