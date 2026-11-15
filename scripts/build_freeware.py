"""Page indépendante GRATUIT : aéroports et avions, hors Flightsim.to."""
from __future__ import annotations
import datetime as dt
import html
import json
import pathlib
import re
from urllib.request import Request, urlopen
from urllib.parse import urljoin

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"

def esc(v):
    return html.escape(str(v or ""), quote=True)

def image_for(url):
    try:
        with urlopen(Request(url, headers={"User-Agent":"Mozilla/5.0"}), timeout=7) as res:
            data = res.read(180000).decode("utf-8", "ignore")
        m = re.search(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)', data, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)', data, re.I)
        return urljoin(url, html.unescape(m.group(1))) if m else ""
    except Exception:
        return ""

def latest_freeware():
    """Actualités freeware récentes, excluant Flightsim.to et les utilitaires."""
    import xml.etree.ElementTree as ET
    try:
        with urlopen(Request("https://msfsaddons.com/category/freeware/feed/",headers={"User-Agent":"JournalMSFS/1.0"}),timeout=12) as res:
            xml=res.read(700000)
        root=ET.fromstring(xml)
        found=[]
        for item in root.findall("./channel/item")[:35]:
            title=(item.findtext("title") or "").strip()
            url=(item.findtext("link") or "").strip()
            cats=[(c.text or "").lower() for c in item.findall("category")]
            if "freeware" not in cats or not url or "flightsim.to" in url.lower(): continue
            kind="aeroport" if "airports" in cats else "avion" if "aircraft" in cats else None
            if not kind: continue
            # Ne pas confondre une annonce de développement avec un produit téléchargeable.
            if re.search(r"upcoming|preview|shows|progress|coming|teases|announces|returns|review|guide",title,re.I): continue
            if not re.search(r"free|giveaway|gives away|released|available|download|now out",title,re.I): continue
            found.append({"type":kind,"title":title,"publisher":"MSFS Addons — actualité freeware",
                          "description":"Annonce gratuite repérée automatiquement ; vérifier la disponibilité sur la fiche source.",
                          "url":url,"source":"MSFS Addons","compatibility":"MSFS 2024 à vérifier","image":""})
        return found[:12]
    except Exception as exc:
        print("Veille freeware indisponible :",exc)
        return []

def build():
    payload=json.loads((PUBLIC/"freeware.json").read_text(encoding="utf-8"))
    airports=json.loads((PUBLIC/"airports.json").read_text(encoding="utf-8"))
    owned={str(a.get("icao","")).upper() for a in airports}
    items=payload.get("items",[])
    known={x["url"] for x in items}
    items += [x for x in latest_freeware() if x["url"] not in known]
    blocks=[]
    image_cache={}
    for kind, heading in [("aeroport","Aéroports gratuits"),("avion","Avions gratuits")]:
        cards=[]
        for item in items:
            if item.get("type") != kind: continue
            img=item.get("image") or image_cache.setdefault(item["url"], image_for(item["url"]))
            image_html=('<img loading="lazy" alt="Illustration : '+esc(item["title"])+'" src="'+esc(img)+'">') if img else '<div class="noimage">✈</div>'
            code=str(item.get("icao") or "").upper()
            ownership='<span class="owned">Déjà dans ton inventaire</span>' if code and code in owned else ''
            cards.append('<article class="card">'+image_html+'<div class="cardbody"><small>'+esc(item.get("publisher"))+' · '+esc(item.get("compatibility"))+'</small><h3>'+esc(item["title"])+'</h3><p>'+esc(item.get("description"))+'</p>'+ownership+'<a target="_blank" rel="noopener noreferrer" href="'+esc(item["url"])+'">Consulter la fiche / télécharger ↗</a></div></article>')
        blocks.append('<section><h2>'+heading+' <span class="count">'+str(len(cards))+'</span></h2><div class="grid">'+''.join(cards)+'</div></section>')
    today=dt.datetime.now(dt.timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    page='''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GRATUIT — Le Journal MSFS</title><link rel="stylesheet" href="styles.css">
<style>
body{background:#edf2f5;color:#142d41}.wrap{max-width:1200px;margin:auto;padding:20px}
header{background:#081d30;color:#fff;padding:30px 0}header a{color:#f9d17d}
h1{font-size:clamp(32px,5vw,52px);margin:12px 0}h2{margin:32px 0 15px}.count{font-size:14px;color:#597187}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}
.card{background:white;border-radius:14px;overflow:hidden;box-shadow:0 4px 18px #102d4517}
.card img,.noimage{display:block;width:100%;height:185px;object-fit:cover;background:linear-gradient(135deg,#0b2943,#4384a6);color:#fff}
.noimage{display:grid;place-items:center;font-size:68px}.cardbody{padding:18px}.cardbody h3{margin:10px 0}
.cardbody small{color:#617588}.cardbody a{display:inline-block;margin-top:10px;font-weight:700;color:#0867a0}
.owned{display:block;font-weight:700;color:#31714a;margin:10px 0}
</style></head><body><header><div class="wrap"><a href="index.html">← Retour au Journal MSFS</a><h1>🎁 GRATUIT</h1>
<p>Scènes et avions gratuits hors Flightsim.to · sélection vérifiée et actualisée selon les sources disponibles</p>
<p>Catalogue actualisé : '''+esc(payload.get("updated_at"))+''' · Page générée : '''+esc(today)+'''</p></div></header>
<main class="wrap">'''+''.join(blocks)+'''<p>Les liens peuvent pointer vers une page éditeur ou une annonce lorsqu'un téléchargement direct n'est pas confirmé. Vérifier la compatibilité et les conditions avant installation.</p></main></body></html>'''
    (PUBLIC/"gratuits.html").write_text(page,encoding="utf-8")
    print("Page GRATUIT :",len(items),"fiches")

if __name__=="__main__":
    build()
