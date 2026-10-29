#!/usr/bin/env python3
"""Surveillance publique quotidienne du Journal MSFS.
Les changements de page sont des indices À VÉRIFIER, jamais des mises à jour
confirmées. Aucun contenu privé, aucune connexion à un compte.
"""
from __future__ import annotations
import concurrent.futures
import datetime as dt
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
WATCH_FILE = PUBLIC / "watch.json"
NOW = dt.datetime.now(dt.timezone.utc)
UA = "Mozilla/5.0 (compatible; JournalMSFS/1.1; +https://matthisfr.github.io/journal-msfs/)"

# Tous les thèmes demandés sont inscrits explicitement, même si un site bloque
# l'accès automatique. Ces entrées restent visibles avec leur statut d'échec.
SOURCES = [
    ("si", "SayIntentions — site", "SayIntentions", "https://sayintentions.ai/"),
    ("si-kb", "SayIntentions — documentation", "SayIntentions", "https://kb.sayintentions.ai/"),
    ("si-blog", "SayIntentions — annonces et nouveautés", "SayIntentions", "https://www.sayintentions.ai/blog"),
    ("si-portal-news", "SayIntentions — Pilot Portal / What\'s New", "SayIntentions", "https://p2.sayintentions.ai/p2/#news"),
    ("si-pocket", "SayIntentions — PocketSky / Windows App", "SayIntentions", "https://sayintentions.ai/"),
    ("fenix", "Fenix — annonces et V3 / CIDS / FAP", "Fenix", "https://fenixsim.com/blog/"),
    ("fenix-status", "Fenix — état des produits A320 / A319 / A321 / NEO", "Fenix", "https://fenixsim.com/status/"),
    ("fenix-help", "Fenix — documentation technique", "Fenix", "https://support.fenixsim.com/hc/en-us"),
    ("mf", "MobiFlight — site", "MobiFlight", "https://www.mobiflight.com/"),
    ("mf-download", "MobiFlight — téléchargements", "MobiFlight", "https://www.mobiflight.com/download/"),
    ("mf-releases", "MobiFlight — versions officielles GitHub", "MobiFlight", "https://github.com/MobiFlight/MobiFlight-Connector/releases"),
    ("msfs", "MSFS 2024 — site officiel", "MSFS 2024", "https://www.flightsimulator.com/"),
    ("msfs-forum", "MSFS — annonces officielles", "MSFS 2024", "https://forums.flightsimulator.com/c/official/news-and-announcements/141"),
    ("fshud", "FSHud — site officiel", "ATC / Trafic", "https://www.fshud.com/"),
    ("fshud-kb", "FSHud — documentation et mises à jour", "ATC / Trafic", "https://www.fshud.com/site/knowledge"),
    ("gsx", "GSX Pro — FSDreamTeam", "GSX Pro", "https://www.fsdreamteam.com/products_gsxpro.html"),
    ("gsx-changelog", "GSX / Couatl — notes officielles de mise à jour", "GSX Pro", "https://www.fsdreamteam.com/couatl_liveupdate_notes.html"),
    ("gsx-forum", "GSX — forum de l'éditeur", "GSX Pro", "https://www.fsdreamteam.com/forum/"),
    ("gsx-fselite", "GSX / FSDreamTeam — actualités FSElite", "GSX Pro", "https://fselite.net/developer/fsdreamteam/"),
    ("fsltl", "FSLTL — versions officielles modèles et livrées", "Trafic IA", "https://github.com/FSLiveTrafficLiveries/base/releases"),
    ("fsltl-models", "FSLTL — paquets officiels Base Models", "Trafic IA", "https://github.com/FSLiveTrafficLiveries/FSLTL_BaseModels_Releases/releases"),
    ("aig", "AIG — forum officiel modèles, livrées et OCI", "Trafic IA", "https://www.alpha-india.net/forums"),
    ("aig-msfs", "AIG — annonces développeurs sur le forum MSFS", "Trafic IA", "https://forums.flightsimulator.com/t/aig-ai-manager-and-traffic-controller-for-msfs/324219"),
    ("winctrl", "WINCTRL / WINWING — ACP32 / OVHD32 / AGP32 / SimAppPro", "WINCTRL", "https://winwingsim.com/"),
    ("winctrl-shop", "WINCTRL — catalogue nouveautés matériel", "Matériel cockpit Airbus A320", "https://winctrl.com/view/shopping.html"),
    ("navigraph", "Navigraph — site officiel", "Navigraph", "https://navigraph.com/"),
    ("simbrief-changelog", "SimBrief — changelog officiel", "Navigraph", "https://www.simbrief.com/home/?page=changelog"),
    ("navigraph-charts", "Navigraph Charts — actualités", "Navigraph", "https://navigraph.com/blog"),
    ("navigraph-blog", "Navigraph — blog", "Navigraph", "https://navigraph.com/blog"),
    ("fcr", "FlightControlReplay — FlightControlTools", "Utilitaires", "https://flightcontroltools.com/"),
    ("fsipanel", "FSIPanel — site officiel", "Utilitaires", "https://www.fsipanel.com/"),
    ("siminnov", "Sim Innovations — Air Manager / Air Player / Knobster", "Utilitaires", "https://www.siminnovations.com/"),
    ("p42", "Parallel 42 — site officiel", "Utilitaires", "https://parallel42.com/"),
    ("p42-news", "Parallel 42 — actualités / ChasePlane", "Utilitaires", "https://parallel42.com/blogs/news"),
    ("p42-releases", "Parallel 42 — tableau officiel des versions et changelogs (Flow Pro / ChasePlane)", "Utilitaires", "https://parallel42.com/pages/is-it-out"),
    ("s3", "S3 — santiluib3.com", "Matériel cockpit Airbus A320", "https://santiluib3.com/"),
    ("stratawx", "StrataWx — météo", "Météo", "https://stratawx.com/"),
    ("aerosoft", "Aerosoft — scènes et produits", "Éditeurs de scènes", "https://www.aerosoft.com/"),
    ("inibuilds", "iniBuilds — scènes et produits", "Éditeurs de scènes", "https://inibuilds.com/"),
    ("mkstudios", "MK-STUDIOS — scènes", "Éditeurs de scènes", "https://mkstudios.pl/"),
    ("flytampa", "FlyTampa — scènes", "Éditeurs de scènes", "https://www.flytampa.org/"),
    ("francevfr", "France VFR — scènes", "Éditeurs de scènes", "https://www.francevfr.com/"),
    ("flightbeam", "Flightbeam — scènes", "Éditeurs de scènes", "https://www.flightbeam.net/"),
    ("orbx", "Orbx — scènes", "Éditeurs de scènes", "https://orbxdirect.com/"),
    ("fsdg", "FSDG — scènes", "Éditeurs de scènes", "https://fsdg-online.com/"),
    ("rdpresets", "RDPresets — scènes", "Éditeurs de scènes", "https://www.rdpresets.com/"),
    ("fsdreamteam", "FSDreamTeam — scènes", "Éditeurs de scènes", "https://www.fsdreamteam.com/"),
    ("pacsim", "PacSim — Cleveland / Salt Lake City", "Éditeurs de scènes", "https://www.islandsim.com/index.html"),
    ("pacsim-kslc", "PacSim KSLC V2 — suivi des révisions publiques", "Éditeurs de scènes", "https://forums.flightsimulator.com/t/pacsim-kslc-salt-lake-city-international-airport/547684"),
    ("bmw-lipz", "Beautiful Model of the World — LIPZ", "Éditeurs de scènes", "https://beautifulmodelworld.com/"),
    ("orbx-central", "Orbx Central — annonces et versions privées", "Éditeurs de scènes", "https://orbxdirect.com/central"),
    ("simmarket", "simMarket — fiches et révisions de scènes", "Éditeurs de scènes", "https://secure.simmarket.com/"),
    ("flightsimto-lepa", "EuroScene LEPA — version publiée", "Éditeurs de scènes", "https://fr.flightsim.to/addon/84186/lepa-palma-de-mallorca-airport"),
    ("fsdt-updater", "FSDreamTeam — GSX et Live Update", "Éditeurs de scènes", "https://www.fsdreamteam.com/forum/"),

]
assert len({x[0] for x in SOURCES}) == len(SOURCES), "Identifiants de veille dupliqués"

class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.depth = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg", "noscript", "footer", "nav"):
            self.skip += 1
        elif tag in ("h1", "h2", "h3", "h4", "p", "article", "main", "title"):
            self.depth += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg", "noscript", "footer", "nav"):
            self.skip = max(0, self.skip - 1)
        elif tag in ("h1", "h2", "h3", "h4", "p", "article", "main", "title"):
            self.depth = max(0, self.depth - 1)
    def handle_data(self, data):
        if not self.skip and (self.depth or len(self.parts) < 20):
            s = re.sub(r"\s+", " ", data).strip()
            if s and len(s) > 2:
                self.parts.append(s)

def signature(html_bytes):
    parser = PageText()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    body = " ".join(parser.parts)
    body = re.sub(r"\s+", " ", body).strip()[:50000]
    if len(body) < 30:
        raise ValueError("Page sans contenu textuel exploitable")
    return hashlib.sha256(body.encode("utf-8")).hexdigest(), body[:140]

def fetch_one(source):
    key, name, group, url = source
    row = {"id": key, "name": name, "group": group, "url": url,
           "checked_at": NOW.isoformat(), "state": "unavailable"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"})
        with urllib.request.urlopen(req, timeout=12) as response:
            ctype = response.headers.get("Content-Type", "")
            if "text/html" not in ctype and "application/xhtml" not in ctype:
                raise ValueError("Type de contenu non HTML")
            blob = response.read(700_000)
            row["http_status"] = response.status
        digest, excerpt = signature(blob)
        row.update({"state": "ok", "hash": digest, "excerpt": excerpt})
    except urllib.error.HTTPError as e:
        row["http_status"] = e.code
        row["state"] = "restricted" if e.code in (401, 403, 429) else "unavailable"
        row["reason"] = f"HTTP {e.code}"
    except Exception as e:
        row["reason"] = (type(e).__name__ + ": " + str(e))[:150]
    return row

def collect(previous=None):
    previous = previous or {}
    before = {x["id"]: x for x in previous.get("sources", [])}
    rows, changes = [], list(previous.get("changes", []))[-50:]
    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as pool:
        for row in pool.map(fetch_one, SOURCES):
            old = before.get(row["id"], {})
            row["last_changed_at"] = old.get("last_changed_at")
            if row["state"] == "ok":
                if old.get("hash") and old["hash"] != row["hash"]:
                    row["state"] = "changed"
                    row["last_changed_at"] = NOW.isoformat()
                    changes.append({"id": row["id"], "name": row["name"],
                                    "group": row["group"], "url": row["url"],
                                    "detected_at": NOW.isoformat(),
                                    "note": "Contenu public modifié — version / annonce à confirmer"})
            else:
                if old.get("hash"):
                    row["hash"] = old["hash"]  # conserver la référence, jamais le statut OK
            rows.append(row)
    totals = {s: sum(x["state"] == s for x in rows) for s in ("ok", "changed", "restricted", "unavailable")}
    return {"checked_at": NOW.isoformat(), "total": len(SOURCES), "totals": totals,
            "sources": rows, "changes": changes[-50:],
            "note": "Changement de page ≠ nouvelle version. Les sources privées, inaccessibles ou sans changelog restent UNKNOWN."}

def main():
    try:
        previous = json.loads(WATCH_FILE.read_text(encoding="utf-8")) if WATCH_FILE.is_file() else {}
    except (ValueError, OSError):
        previous = {}
    data = collect(previous)
    WATCH_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Veille éditeurs :", data["total"], "sites ;", data["totals"])

if __name__ == "__main__":
    main()
