#!/usr/bin/env python3
import json, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

TEAM_ID = 325671
BASE = f"https://api.sofascore.com/api/v1/team/{TEAM_ID}/events/next"
OUT = Path("grasshopper-u19.ics")

def fetch(page):
    req = urllib.request.Request(f"{BASE}/{page}", headers={"User-Agent": "grasshopper-u19-ics/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def esc(v):
    return str(v).replace("\\","\\\\").replace(";","\\;").replace(",","\\,").replace("\n","\\n").replace("\r","")

def dt(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")

events={}
for page in range(5):
    try: data=fetch(page)
    except Exception: break
    for e in data.get("events",[]): events[str(e["id"])]=e
    if not data.get("hasNextPage"): break

now=datetime.now(timezone.utc)
lines=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Grasshopper Zürich U19 ICS//SofaScore//IT","CALSCALE:GREGORIAN","METHOD:PUBLISH","X-WR-CALNAME:Grasshopper Zürich U19","X-WR-TIMEZONE:Europe/Zurich"]
for e in sorted(events.values(), key=lambda x:x.get("startTimestamp",0)):
    ts=e.get("startTimestamp")
    if not ts or datetime.fromtimestamp(ts,tz=timezone.utc)<now-timedelta(days=2): continue
    home=e.get("homeTeam",{}).get("name","Casa"); away=e.get("awayTeam",{}).get("name","Trasferta")
    tournament=e.get("tournament",{}).get("name","Calcio"); status=e.get("status",{}).get("type","notstarted"); eid=e["id"]
    lines += ["BEGIN:VEVENT",f"UID:sofascore-grasshopper-u19-{eid}@lazio-primavera-ics",f"DTSTAMP:{dt(int(now.timestamp()))}",f"DTSTART:{dt(ts)}",f"DTEND:{dt(ts+7200)}",f"SUMMARY:{esc(home+' - '+away)}",f"DESCRIPTION:{esc(tournament+' | SofaScore event '+str(eid))}",f"STATUS:{'CANCELLED' if status=='canceled' else 'CONFIRMED'}",f"URL:https://www.sofascore.com/event/{eid}","END:VEVENT"]
lines.append("END:VCALENDAR")
OUT.write_text("\r\n".join(lines)+"\r\n",encoding="utf-8")
print(f"Generated {OUT} with {len(events)} SofaScore events.")
