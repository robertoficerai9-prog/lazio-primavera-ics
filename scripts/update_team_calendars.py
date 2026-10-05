#!/usr/bin/env python3
import datetime as dt
import json
from pathlib import Path

TEAMS = [
    ("bari-serie-c.ics", "Bari - Serie C", 2712),
    ("barletta-serie-c.ics", "Barletta - Serie C", 25154),
    ("gubbio-serie-c.ics", "Gubbio - Serie C", 2782),
    ("juventus-next-gen-serie-c.ics", "Juventus Next Gen - Serie C", 294884),
    ("lazio-primavera.ics", "Lazio - Primavera", 826821),
    ("roma-primavera.ics", "Roma - Primavera", 340799),
    ("lecce-primavera.ics", "Lecce - Primavera", 826809),
    ("palermo-primavera-2.ics", "Palermo - Primavera 2", 64119),
    ("verona-u15.ics", "Verona - U15", 1233776),
    ("torino-u15.ics", "Torino - U15", 933354),
    ("arezzo-u17.ics", "Arezzo - U17", 933397),
    ("frosinone-primavera-2.ics", "Frosinone - Primavera 2", 170874),
]

def fetch(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
    }
    from curl_cffi import requests
    r = requests.get(url, headers=headers, impersonate="chrome", timeout=30)
    r.raise_for_status()
    return r.json()

def esc(v):
    return str(v or "").replace("\\","\\\\").replace(";","\\;").replace(",","\\,").replace("\n","\\n").replace("\r","")

def utc(ts):
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

now = dt.datetime.now(dt.timezone.utc)
cutoff = now - dt.timedelta(days=2)
stamp = utc(now.timestamp())

for filename, label, team_id in TEAMS:
    events = {}
    for page in range(12):
        data = None
        for host in ("https://www.sofascore.com", "https://api.sofascore.com"):
            try:
                data = fetch(f"{host}/api/v1/team/{team_id}/events/next/{page}")
                break
            except Exception as e:
                print(f"{label}: page {page} failed on {host}: {e}")
        if not data:
            continue
        for e in data.get("events", []):
            if e.get("id"):
                events[e["id"]] = e
        if not data.get("hasNextPage") and not data.get("events"):
            break

    lines = [
        "BEGIN:VCALENDAR","VERSION:2.0",
        f"PRODID:-//{label}//SofaScore//IT",
        "CALSCALE:GREGORIAN","METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc(label)}","X-WR-TIMEZONE:Europe/Rome"
    ]
    count = 0
    for e in sorted(events.values(), key=lambda x: x.get("startTimestamp", 0)):
        ts = e.get("startTimestamp")
        if not ts:
            continue
        start = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
        if start < cutoff:
            continue
        home = e.get("homeTeam", {}).get("name", "Casa")
        away = e.get("awayTeam", {}).get("name", "Trasferta")
        event_id = e["id"]
        status = e.get("status", {}).get("type", "notstarted")
        lines += [
            "BEGIN:VEVENT",
            f"UID:sofascore-{team_id}-{event_id}@lazio-primavera-ics",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{utc(ts)}",
            f"DTEND:{utc(ts + 7200)}",
            f"SUMMARY:{esc(home + ' - ' + away)}",
            f"DESCRIPTION:{esc(label + ' | SofaScore event ' + str(event_id))}",
            f"STATUS:{'CANCELLED' if status == 'canceled' else 'CONFIRMED'}",
            f"URL:https://www.sofascore.com/event/{event_id}",
            "END:VEVENT"
        ]
        count += 1
    lines.append("END:VCALENDAR")
    Path(filename).write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    print(f"Generated {filename}: {count} events")

