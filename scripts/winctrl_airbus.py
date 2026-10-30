#!/usr/bin/env python3
"""Veille éditoriale WINCTRL : uniquement les matériels Airbus.

MSFS Addons est une source d'annonces (pas un stock marchand).
Les prix ci-dessous sont ceux PUBLIÉS À LA DATE de l'article, jamais
présentés comme prix en vigueur. Une date ancienne ne devient pas NEWS
parce qu'elle est découverte aujourd'hui.
"""
from __future__ import annotations

import datetime as dt
from html.parser import HTMLParser
import html
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
OUTPUT = PUBLIC / "winctrl_airbus.json"
STATUS = PUBLIC / "status.json"
INDEX = "https://msfsaddons.com/developer/winctrl/"
HOST = "msfsaddons.com"
UTC = dt.timezone.utc

# Sources datées contrôlées individuellement. Les prix sont des instantanés
# de l'article, pas une vérification quotidienne du panier commercial.
SEEDS = [
    dict(date="2026-10-22", url="https://msfsaddons.com/2026/10/22/airbus-captain-sticks-are-like-buses-winctrls-full-metal-left-hand-grip-arrives-on-the-same-day-as-mozas/",
         title="WINCTRL : nouveau sidestick Airbus métal côté commandant",
         summary="32 Sidestick Controller Metal 2 : précommande annoncée à 55,53 $ ; vente annoncée à partir du 28 octobre. Nécessite une base Orion 2 ou Cyber Taurus.",
         products=["sidestick-metal"], price="$55.53"),
    dict(date="2026-07-02",url="https://msfsaddons.com/2026/07/02/winctrl-32-nws-the-tiller-finally-gets-its-affordable-moment-at-82-30/",
         title="WINCTRL 32 NWS : lancement du tiller Airbus gauche et droit",
         summary="Tiller Airbus disponible à l'annonce dès 82,30 $ (79,01 € en précommande européenne), avec profils Fenix et SimAppPro.",
         products=["nws"],price="$82.30"),
    dict(date="2026-04-15",url="https://msfsaddons.com/2026/04/15/winctrl-launches-the-32-tcas-panel-squawk-codes-and-tcas-control-in-physical-hardware-for-77-50/",
         title="WINCTRL 32 TCAS : lancement du panneau transpondeur Airbus",
         summary="TCAS commercialisé à l'annonce dès 77,50 $ (74,40 € en Europe). Compatibilité Fenix A319/A320/A321 via SimAppPro.",
         products=["tcas"],price="$77.50"),
    dict(date="2026-03-21",url="https://msfsaddons.com/2026/03/21/winctrls-ovhd32-sop-brings-a-full-airbus-overhead-panel-to-home-cockpits-for-349-95/",
         title="WINCTRL OVHD32 SOP : présentation du plafonnier Airbus",
         summary="Overhead A320 annoncé à 349,95 $. Date d'expédition non confirmée dans cet article.",
         products=["ovhd"],price="$349.95"),
    dict(date="2026-01-26",url="https://msfsaddons.com/2026/01/26/winctrl-targets-airliner-simmers-with-new-orion-32-rudder-pedals/",
         title="WINCTRL Orion 32 : palonniers métal pour avions de ligne",
         summary="Version avec amortisseur annoncée à 325,02 € en Europe ; commandes annoncées pour le 27 janvier 2026.",
         products=["pedals"],price="€325.02"),
    dict(date="2025-11-08",url="https://msfsaddons.com/2025/11/08/winwings-new-airbus-style-ecam-32-and-agp-32-metal-panels-are-now-listed-and-shipping-soon/",
         title="WINWING : ECAM 32 et AGP 32 Metal annoncés pour Airbus",
         summary="ECAM 32 à 57,63 $ et AGP 32 Metal à 116,34 $ (prix de lancement annoncés). Expéditions annoncées dès le 10 novembre 2025.",
         products=["ecam","agp"]),
    dict(date="2025-09-24",url="https://msfsaddons.com/2025/09/24/winwing-sets-september-26-launch-for-new-ursa-minor-airbus-style-throttles/",
         title="WINWING : manettes URSA MINOR 32 Airbus annoncées",
         summary="Annonce du lancement des manettes de poussée Airbus au 26 septembre 2025.",
         products=["throttle"]),
]
# Informations datées et vérifiées par produit. Ne sont jamais écrasées
# par un prix extrait du texte d'une annonce qui traiterait de plusieurs modèles.
PRODUCTS = {
    "brake-pressure-gauge":dict(price="$39.95",price_date="2026-08-24",
        availability="Annoncé ; date de commercialisation non confirmée",
        release_kind="sortie non confirmée",
        announcement_url="https://fsnews.eu/winctrl-unveils-newest-piece-of-hardware-for-home-airbus-cockpits/"),
    "sidestick-metal":dict(price="$55.53",price_eu="€53.31",price_date="2026-10-22",availability="Précommande annoncée le 22/10/2026 ; vente prévue le 28/10/2026",
        release_date="2026-10-28",release_kind="date de mise en vente annoncée",
        image_url="https://msfsaddons.com/wp-content/uploads/2026/10/WINCTRL-32-Sidestick-Controller-L-7.png.webp"),
    "nws":dict(price="$82.30",price_eu="€79.01",price_date="2026-07-02",availability="Lancement annoncé le 02/07/2026"),
    "tcas":dict(price="$77.50",price_eu="€74.40",price_date="2026-04-15",availability="Lancement annoncé le 15/04/2026"),
    "ovhd":dict(price="$349.95",price_date="2026-03-21",availability="Présenté à FSWeekend ; expédition non confirmée",
        image_url="https://msfsaddons.com/wp-content/uploads/2026/03/winctrl-airbus-overhead-panel-2.webp"),
    "pedals":dict(price="€325.02",price_date="2026-01-26",availability="Prix européen annoncé pour version avec amortisseur"),
    "ecam":dict(price="$57.63",price_date="2025-11-08",availability="Lancement annoncé le 10/11/2025",release_date="2025-11-10",
        release_kind="date de disponibilité annoncée",
        image_url="https://msfsaddons.com/wp-content/uploads/2025/11/winwing-ecam-6.webp"),
    "agp":dict(price="$116.34",price_date="2025-11-08",availability="Lancement annoncé le 10/11/2025",release_date="2025-11-10",
        release_kind="date de disponibilité annoncée",
        image_url="https://msfsaddons.com/wp-content/uploads/2025/11/winwing-agp-metal-1.webp"),
    "throttle":dict(availability="Lancement annoncé le 26/09/2025",release_date="2025-09-26",
        release_kind="date de lancement annoncée"),
}
LABELS = {"brake-pressure-gauge":"32 Brake Pressure Gauge Airbus", "sidestick-metal":"32 Sidestick Controller Metal 2", "nws":"32 NWS Airbus",
          "tcas":"32 TCAS Airbus", "ovhd":"OVHD32 SOP Airbus", "pedals":"Orion 32 Rudder Pedals",
          "ecam":"ECAM 32 Airbus", "agp":"AGP 32 Metal", "throttle":"URSA MINOR 32 Throttle",
          "acp":"ACP32 Airbus", "fcu":"FCU Airbus", "efis":"EFIS Airbus", "mcdu":"MCDU A320"}

class Tags(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[];self.meta={};self.times=[];self.title=[];self.h1=[]
        self.in_title=False;self.in_h1=False;self.ld=[];self.in_ld=False;self.buffer=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="a" and a.get("href"):self.links.append(a["href"])
        if tag=="meta":
            key=a.get("property") or a.get("name")
            if key and a.get("content"):self.meta[key.lower()]=a["content"]
        if tag=="time" and a.get("datetime"):self.times.append(a["datetime"])
        if tag=="title":self.in_title=True
        if tag=="h1":self.in_h1=True
        if tag=="script" and a.get("type","").lower()=="application/ld+json":
            self.in_ld=True;self.buffer=[]
    def handle_data(self,data):
        if self.in_title:self.title.append(data)
        if self.in_h1:self.h1.append(data)
        if self.in_ld:self.buffer.append(data)
    def handle_endtag(self,tag):
        if tag=="title":self.in_title=False
        if tag=="h1":self.in_h1=False
        if tag=="script" and self.in_ld:
            try:self.ld.append(json.loads("".join(self.buffer)))
            except (ValueError, TypeError):pass
            self.in_ld=False

def safe_url(url):
    p=urlparse(url)
    return p.scheme=="https" and p.hostname in (HOST,"www."+HOST)

def article_url(url):
    p=urlparse(url)
    return safe_url(url) and bool(re.match(r"^/20\d\d/\d{2}/\d{2}/[^/]+/?$",p.path))

def fetch(url):
    if not safe_url(url):raise ValueError("Source non autorisée")
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (Le Journal MSFS, veille Airbus)",
                            "Accept":"text/html"})
    with urlopen(req,timeout=14) as r:
        return r.read(1_800_000).decode("utf-8","replace")

def product_ids(title):
    t=title.lower()
    # Une actualité MOZA ou Boeing, même présente dans les liens associés,
    # ne devient jamais une actualité WINCTRL Airbus.
    if not re.search(r"\bwinctrl\b|\bwinwing\b",t):return []
    # Décision basée sur le TITRE et non les recommandations au bas de l'article.
    if "boeing" in t and "airbus" not in t:return []
    if "brake pressure" in t or "brake gauge" in t:return ["brake-pressure-gauge"]
    if "sidestick" in t or "captain sticks" in t:return ["sidestick-metal"] if ("airbus" in t or "winctrl" in t) else []
    if "ecam" in t and "agp" in t:return ["ecam","agp"]
    if "ovhd32" in t or "airbus overhead" in t:return ["ovhd"]
    if re.search(r"\b32\s*nws\b|\btiller\b",t):return ["nws"]
    if re.search(r"\b32\s*tcas\b",t):return ["tcas"]
    if "orion 32" in t and "rudder" in t:return ["pedals"]
    if ("ursa minor" in t or "ursa" in t) and ("throttle" in t or "manette" in t) and "airbus" in t:return ["throttle"]
    if "ecam" in t and "airbus" in t:return ["ecam"]
    if "agp" in t and "airbus" in t:return ["agp"]
    if "acp32" in t and "airbus" in t:return ["acp"]
    if "efis" in t and "airbus" in t:return ["efis"]
    if "fcu" in t and "airbus" in t:return ["fcu"]
    if "mcdu" in t and "airbus" in t:return ["mcdu"]
    return []

def article_date(parser,url):
    raw=(parser.meta.get("article:published_time") or parser.meta.get("datepublished")
         or (parser.times[0] if parser.times else ""))
    if raw:
        try:return dt.datetime.fromisoformat(raw.replace("Z","+00:00")).date().isoformat()
        except ValueError:pass
    # Une URL datée d'article est une date éditoriale explicite, pas la date du contrôle.
    m=re.match(r"^/(20\d\d)/(\d\d)/(\d\d)/",urlparse(url).path)
    if m:
        try:return dt.date(*map(int,m.groups())).isoformat()
        except ValueError:pass
    return ""

def from_article(url,raw):
    p=Tags();p.feed(raw)
    title=html.unescape(" ".join(p.h1).strip() or p.meta.get("og:title","").strip())
    ids=product_ids(title)
    date=article_date(p,url)
    if not ids or not date:return None
    if date>dt.datetime.now(UTC).date().isoformat():return None
    names=" et ".join(LABELS[x] for x in ids)
    image=p.meta.get("og:image","")
    image=image if safe_url(image) and "/wp-content/uploads/" in urlparse(image).path else ""
    if len(ids)!=1:image=""  # Ne jamais attribuer une photo de deux modèles à un seul.
    return {"url":url,"date":date,"title":"WINCTRL Airbus : annonce "+names,
            "summary":"MSFS Addons présente "+names+". Consulte l'article pour les caractéristiques et les conditions de vente.",
            "products":ids,"image_url":image,"source":"MSFS Addons — WINCTRL"}

def records(previous,fetcher=fetch):
    try:
        landing=fetcher(INDEX)
        page=Tags();page.feed(landing)
        urls=[]
        for href in page.links:
            u=urljoin(INDEX,href).split("?")[0].split("#")[0]
            if article_url(u) and u not in urls:urls.append(u)
        if not urls:raise ValueError("Aucun lien d'article daté trouvé sur la page WINCTRL")
        found=[]
        for u in urls[:25]:
            try:
                result=from_article(u,fetcher(u))
                if result:found.append(result)
            except Exception as exc:print("Article WINCTRL inaccessible",u,type(exc).__name__)
        if not found:raise ValueError("Aucun article Airbus daté vérifiable")
        state="ok"
    except Exception as exc:
        print("Source WINCTRL MSFS Addons indisponible:",type(exc).__name__,str(exc)[:160])
        found=[];state="unavailable"
    # Graines vérifiées : toujours disponibles même si le fournisseur bloque l'accès.
    all_records={x["url"]:dict(x) for x in SEEDS}
    for x in previous:
        if x.get("url") and article_url(x["url"]) and x.get("date") and x.get("products"):
            all_records.setdefault(x["url"],x)
    for x in found:
        # Préserver le titre et prix français d'une source déjà validée ; mettre à
        # jour seulement le visuel daté s'il est manquant.
        old=all_records.get(x["url"])
        if old:
            if x.get("image_url") and not old.get("image_url"):old["image_url"]=x["image_url"]
        else:all_records[x["url"]]=x
    return sorted(all_records.values(),key=lambda x:(x["date"],x["url"]),reverse=True)[:45],state

def run(fetcher=fetch,now=None):
    now=now or dt.datetime.now(UTC)
    try:old=json.loads(OUTPUT.read_text(encoding="utf-8"))
    except (FileNotFoundError,ValueError):old={}
    stories,state=records(old.get("articles",[]),fetcher)
    products={k:dict(v) for k,v in PRODUCTS.items()}
    for article in reversed(stories):
        for pid in article["products"]:
            x=products.setdefault(pid,{})
            if not x.get("article_date") or article["date"]>=x["article_date"]:
                x["article_date"]=article["date"]
                x["article_url"]=article["url"]
            if not x.get("image_url") and article.get("image_url") and len(article["products"])==1:
                x["image_url"]=article["image_url"]
    # Les anciens tarifs sont des instantanés, jamais des prix actuels.
    payload={"checked_at":now.isoformat(),"source_url":INDEX,
             "source_state":state,"scope":"Matériels Airbus uniquement ; annonces historiques et prix datés",
             "articles":stories,"products":products}
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if STATUS.is_file():
        status=json.loads(STATUS.read_text(encoding="utf-8"))
        status.setdefault("source_status",{})["winctrl_airbus_articles"]=state
        status["winctrl_airbus_checked_at"]=now.isoformat()
        old_news={x.get("url"):x for x in status.get("news",[]) if x.get("url")}
        # Conserver le tri 16 en interface ; injecter uniquement des annonces
        # réellement publiées depuis moins de 60 jours.
        for a in stories:
            age=(now.date()-dt.date.fromisoformat(a["date"])).days
            if age<0 or age>60:continue
            if a["url"] in old_news:continue
            old_news[a["url"]]={"id":"winctrl-airbus-"+re.sub("[^a-z0-9]+","-",a["url"].rsplit("/",2)[-2].lower()),
                "url":a["url"],"date":a["date"],"topic":"WINCTRL","category":"Matériel Airbus",
                "source":"MSFS Addons — WINCTRL", "title":a["title"],"summary":a["summary"],
                "impact":"Prix annoncés à la date de l'article ; vérifier la boutique WINCTRL pour disponibilité et tarif actuels.",
                "new":age==0}
        status["news"]=sorted(old_news.values(),key=lambda x:(x.get("date",""),x.get("url","")),reverse=True)[:35]
        STATUS.write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("WINCTRL Airbus : ",len(stories),"annonces datées ;",len(products),"modèles ; source",state)

if __name__=="__main__":run()
