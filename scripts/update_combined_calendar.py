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

def fetch_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
        "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
    }
    try:
        from curl_cffi import requests as curl_requests
        r = curl_requests.get(url, headers=headers, impersonate="chrome", timeout=30)
        r.raise_for_status()
        return r.text
    except ImportError:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="replace")

def fetch_sofascore_events(team_id):
    events = {}
    for page in range(8):
        for host in ("https://www.sofascore.com", "https://api.sofascore.com"):
            url = f"{host}/api/v1/team/{team_id}/events/next/{page}"
            try:
                data = json.loads(fetch_url(url))
                for event in data.get("events", []):
                    eid = event.get("id")
                    if eid:
                        events[eid] = event
                if data.get("events"):
                    break
            except Exception as exc:
                print(f"SofaScore fetch failed team={team_id} page={page}: {exc}")
    return list(events.values())
def esc(value):
    return str(value or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def utc_stamp(ts):
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

now = dt.datetime.now(dt.timezone.utc)
cutoff = now - dt.timedelta(days=2)
all_events = []

for team_name, team_id in TEAMS:
    events = fetch_sofascore_events(team_id)
    print(f"{team_name}: {len(events)} eventi")
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
        all_events.append((ts, team_name, home, away, event_url, event_id, "sofascore"))
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
