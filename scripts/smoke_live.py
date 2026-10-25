#!/usr/bin/env python3
"""Smoke test après déploiement GitHub Pages : contrôle du vrai site public."""
from __future__ import annotations
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://matthisfr.github.io/journal-msfs/").rstrip("/") + "/"

def get(path):
    url = urllib.parse.urljoin(BASE, path)
    url += ("&" if "?" in url else "?") + "smoke=" + str(int(time.time()))
    req = urllib.request.Request(url, headers={"User-Agent": "JournalMSFS-Smoke/1.0", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=18) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}: {path}")
        return r.read(1_500_000).decode("utf-8", errors="replace")

def verify():
    index = get("index.html")
    if index.count("<tr>") < 171: raise AssertionError("171 scènes absentes du HTML publié")
    for marker in ('id="watch-container"', 'id="home-updated"', 'id="news-container"',
                   'google.com/maps/d/embed', 'id="airport-body"'):
        if marker not in index: raise AssertionError(f"Élément manquant: {marker}")
    if index.count('class="watch-source"') < 30: raise AssertionError("Veille des sites absente")
    airports = json.loads(get("airports.json"))
    if len(airports) != 171: raise AssertionError("Inventaire incomplet")
    status = json.loads(get("status.json"))
    checked = dt.datetime.fromisoformat(status["last_run"].replace("Z", "+00:00"))
    if dt.datetime.now(dt.timezone.utc) - checked > dt.timedelta(hours=3):
        raise AssertionError("Collecte trop ancienne")
    coverage = status.get("version_coverage", {})
    if coverage.get("inventory_total") != 171:
        raise AssertionError("Audit des 171 scènes manquant")
    watch = json.loads(get("watch.json"))
    if watch.get("total", 0) < 30: raise AssertionError("Liste de veille incomplète")
    print(f"Site en ligne OK : 171 scènes ; {watch['total']} sources ; "
          f"{coverage.get('verified_today',0)} versions vérifiées ; "
          f"{len(status.get('weather',[]))} METAR classés ; "
          f"{len(status.get('news',[]))} actualités automatiques.")
    return True

if __name__ == "__main__":
    for attempt in range(1, 6):
        try:
            verify()
            sys.exit(0)
        except Exception as exc:
            print(f"Tentative {attempt}/5 : {type(exc).__name__}: {exc}", flush=True)
            if attempt < 5: time.sleep(12)
    sys.exit("ERREUR : site public non conforme après publication")
