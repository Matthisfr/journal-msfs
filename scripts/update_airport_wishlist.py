#!/usr/bin/env python3
"""Liste d'achats aéroports, pilotée par issues GitHub du propriétaire uniquement."""
import json, os, re
from pathlib import Path
from datetime import datetime, timezone
event=json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
issue=event["issue"]
if issue["user"]["login"].lower() != os.environ["GITHUB_REPOSITORY_OWNER"].lower():
    raise SystemExit("Seul le propriétaire du dépôt peut modifier cette liste")
match=re.fullmatch(r"\[AIRPORT-WISHLIST\] (ADD|REMOVE) ([A-Z0-9]{3,5})",issue["title"].strip())
if not match: raise SystemExit("Titre non reconnu")
action,icao=match.groups()
path=Path("public/airport_wishlist.json")
entries=json.loads(path.read_text()) if path.exists() else []
if not isinstance(entries,list): entries=[]
airports=json.loads(Path("public/airports.json").read_text())
owned={str(x.get("icao","")).upper() for x in airports}
coords=json.loads(Path("public/airport_coordinates.json").read_text())
entry=coords.get(icao,{})
if action=="ADD" and icao not in owned and entry and not any(x["icao"]==icao for x in entries):
    if len(entries)>=30: raise SystemExit("Limite de 30 aéroports atteinte")
    entries.append({"icao":icao,"name":entry.get("name") or icao,"country":entry.get("country_code") or "—"})
if action=="REMOVE": entries=[x for x in entries if x["icao"]!=icao]
entries=[x for x in entries if x["icao"] not in owned]
entries.sort(key=lambda x:x["icao"])
path.write_text(json.dumps(entries,ensure_ascii=False,indent=2)+"\n")
print(action,icao,len(entries))
