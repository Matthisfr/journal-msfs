#!/usr/bin/env python3
"""Relier uniquement les fiches produit dont l'ICAO et l'éditeur ont été recoupés.
Ne jamais effacer l'inventaire local, les doublons, ni une URL Aerosoft vérifiée.
Une version datée d'hier n'est PAS vérifiée aujourd'hui.
"""
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse

PUBLIC=Path(__file__).resolve().parents[1]/"public"
airports_path=PUBLIC/"airports.json"
candidates_path=PUBLIC/"airport_source_candidates.json"
today=dt.datetime.now(dt.timezone.utc).date().isoformat()
airports=json.loads(airports_path.read_text(encoding="utf-8"))
if len(airports)!=171:raise RuntimeError("Inventaire des 171 scènes incomplet")
if not candidates_path.exists():
 print("Pas encore de fichier de recherche : liens existants conservés.")
 raise SystemExit(0)
report=json.loads(candidates_path.read_text(encoding="utf-8"))
rows={x["folder"]:x for x in report.get("airports",[])}
added=0
verified=0
stale=0
# Une ancienne correspondance simMarket incorrecte ne doit pas survivre
# après un nouveau contrôle complet du catalogue (notamment FSX/P3D).
fresh_report=(report.get("generated_at","")[:10]==today and
              report.get("simmarket_checked_at","")[:10]==today and
              not report.get("catalog_errors"))
if fresh_report:
 for a in airports:
  if a.get("source_store")!="simMarket":continue
  if rows.get(a["folder"],{}).get("selected"):continue
  for key in ("source_url","source_store","source_title","source_edition","source_vendor",
              "source_confidence","server_version","version_checked_at"):
   a.pop(key,None)
  a["version_check_state"]="no_source"
  a["version_check_reason"]="Ancienne correspondance rejetée : produit ou simulateur différent"
  a["status"]="UNK-P"
for a in airports:
 row=rows.get(a["folder"],{})
 selected=row.get("selected")
 if not selected or not selected.get("url") or not selected.get("version"):continue
 if selected.get("score",0)<20:continue
 url=selected["url"]
 parsed=urlparse(url)
 if parsed.scheme!="https":
  continue
 if parsed.netloc in ("contrail.shop","inibuilds.com"):
  if not parsed.path.startswith("/products/"):continue
 elif parsed.netloc=="secure.simmarket.com":
  if not parsed.path.endswith(".phtml"):continue
 else:
  continue
 # Les 8 sources Aerosoft ont un extracteur officiel distinct : conserver la référence.
 if str(a.get("source_url") or "").startswith("https://www.aerosoft.com/"):
  continue
 if a.get("source_url")!=url:added+=1
 a["source_url"]=url
 a["source_store"]=selected.get("store")
 a["source_title"]=selected.get("title")
 a["source_edition"]=selected.get("edition")
 a["source_vendor"]=selected.get("vendor")
 a["source_confidence"]="éditeur et code aéroport concordants"
 checked=selected.get("checked_at","")[:10]
 if checked==today and selected.get("state")=="verified":
  a["server_version"]=selected["version"]
  a["version_checked_at"]=today
  a["version_check_state"]="verified"
  a["status"]="verified"
  a.pop("version_check_reason",None)
  verified+=1
 else:
  stale+=1
  a["version_check_state"]="unavailable"
  a["version_check_reason"]="Source retrouvée mais version non revalidée aujourd'hui"
  a["status"]="UNK-V"
manual_path=PUBLIC/"airport_manual_sources.json"
manual=json.loads(manual_path.read_text(encoding="utf-8")) if manual_path.is_file() else {}
for a in airports:
 m=manual.get(a["folder"])
 if not m or a.get("source_url"):continue
 a["source_url"]=m["url"]
 a["source_store"]=m.get("store","Éditeur")
 a["source_edition"]=m.get("edition","")
 a["source_title"]=a.get("name")
 a["source_note"]=m.get("note","")
 if m.get("new_edition_version"):
  a["new_edition_version"]=m["new_edition_version"]
  try:
   from discover_simmarket import parse_page
   _,result=parse_page(m["url"])
   if result.get("state")=="verified":
    a["new_edition_version"]=result["version"]
    a["new_edition_checked_at"]=today
   else:
    a["new_edition_checked_at"]=None
  except Exception:
   a["new_edition_checked_at"]=None
 a["version_check_state"]="unavailable"
 a["version_check_reason"]=m.get("note","Version à vérifier dans le gestionnaire éditeur")
 a["status"]="UNK-V"
airports_path.write_text(json.dumps(airports,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"Fiches liées : {added} ; versions boutique contrôlées aujourd'hui : {verified} ; anciennes : {stale} ; inventaire : {len(airports)}")
