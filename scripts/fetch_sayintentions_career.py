"""Collecte prudente des statistiques publiques Gate 404, sans authentification."""
from __future__ import annotations
import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"public"/"sayintentions_career.json"
URL="https://pilots.sayintentions.ai/u/Mathis"
class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript"):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
def parse_public_profile(html):
    text=" ".join(html.split())
    # Only match a rank when it is actually present in the public page.
    rank=re.search(r"\b(Senior\s+(?:1st|First)\s+Officer|Senior\s+Copilot|Junior\s+Copilot|First\s+Officer|Senior\s+First\s+Officer|Captain|Senior\s+Captain)\b",text,re.I)
    # Label must be directly adjacent to its number. Never guess from unrelated page numbers.
    patterns=[
        r"\b(?:total\s+)?flight\s+hours\s*[:\-]?\s*([\d,.]+)",
        r"\b(?:total\s+)?hours\s+flown\s*[:\-]?\s*([\d,.]+)",
        r"\b([\d,.]+)\s*(?:flight\s+hours|hours\s+flown)\b",
    ]
    hours=None
    for pat in patterns:
        m=re.search(pat,text,re.I)
        if m:
            raw=m.group(1).replace(",","")
            try:
                v=float(raw)
                if 0<=v<=100000:hours=v;break
            except ValueError:pass
    values={}
    for key,label in (("ifr_hours","IFR HOURS"),("vfr_hours","VFR HOURS"),("total_flights","TOTAL FLIGHTS"),("airports_visited","AIRPORTS VISITED")):
        m=re.search(r"([0-9,]+)\s+"+label,text,re.I)
        values[key]=int(m.group(1).replace(",","")) if m else None
    if values["ifr_hours"] is not None and values["vfr_hours"] is not None:
        hours=values["ifr_hours"]+values["vfr_hours"]
    return {"rank":rank.group(1) if rank else None,"flight_hours":hours,**values}
def run():
    previous={}
    if DEST.exists():
        try:previous=json.loads(DEST.read_text(encoding="utf-8"))
        except (OSError,ValueError):pass
    result={"state":"unavailable","profile_url":URL,"username":"Mathis",
            "rank":previous.get("rank"),"flight_hours":previous.get("flight_hours"),
            "ifr_hours":previous.get("ifr_hours"),"vfr_hours":previous.get("vfr_hours"),
            "total_flights":previous.get("total_flights"),"airports_visited":previous.get("airports_visited"),
            "source":previous.get("source"),"rank_badge":previous.get("rank_badge"),
            "recent_flights":previous.get("recent_flights",[]),"flights_checked_at":previous.get("flights_checked_at"),
            "verified_at":previous.get("verified_at"),"checked_at":dt.datetime.now(dt.timezone.utc).isoformat()}
    try:
        request=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 (compatible; JournalMSFS/1.0)","Accept":"text/html"})
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            page=browser.new_page()
            page.goto(URL,wait_until="domcontentloaded",timeout=30000)
            page.get_by_text("IFR HOURS",exact=False).first.wait_for(timeout=20000)
            html=page.locator("body").inner_text()
            # Le badge doit être une image proche du nom/grade dans le profil.
            # Ne pas prendre la photo du pilote ni le badge d'identification.
            try:
                candidates=page.locator("img").evaluate_all("""imgs => imgs.map(i => ({
                  src:i.currentSrc||i.src, alt:i.alt||'', title:i.title||'',
                  x:i.getBoundingClientRect().x, y:i.getBoundingClientRect().y,
                  w:i.getBoundingClientRect().width, h:i.getBoundingClientRect().height
                }))""")
                profile=page.get_by_text("Mathis",exact=True).first.bounding_box()
                eligible=[(i,c) for i,c in enumerate(candidates) if c["w"]>=30 and c["w"]<=110 and c["h"]>=30 and c["h"]<=110 and profile and abs(c["y"]-profile["y"])<100 and c["x"]<profile["x"]]
                if not eligible:
                    print("Gate 404: images de la page:",[(c["alt"][:50],c["src"][:110],round(c["x"]),round(c["y"]),round(c["w"]),round(c["h"])) for c in candidates[:18]])
                if eligible:
                    idx,c=min(eligible,key=lambda item:abs(item[1]["x"]-profile["x"])+abs(item[1]["y"]-profile["y"]))
                    image=page.locator("img").nth(idx)
                    badge_path=ROOT/"public"/"sayintentions-rank.png"
                    image.screenshot(path=str(badge_path),timeout=5000)
                    result["rank_badge"]="sayintentions-rank.png"
                    print("Gate 404: insigne de grade récupéré près du profil")
                else:
                    print("Gate 404: insigne de grade non identifié, aucune image substituée")
            except Exception as badge_error:
                print("Gate 404: insigne indisponible:",type(badge_error).__name__)
            try:
                rows=page.locator("table tr").evaluate_all("""rows => rows.map(tr => ({
                  cells:[...tr.querySelectorAll('td')].map(td=>td.innerText.trim()),
                  href:tr.querySelector('a[href]')?.getAttribute('href')||''
                }))""")
                flights=[]
                for row in rows:
                    cells=row["cells"]
                    if len(cells)<7:continue
                    joined=" ".join(cells)
                    flight_id=re.search(r"\b(?:IFR|VFR)-\d{5,}\b",joined,re.I)
                    if not flight_id:continue
                    # Colonnes du tableau public: Actions, ID, Aircraft, When, Origin, Destination, Rules, Duration.
                    offset=0 if len(cells)>=8 else -1
                    if len(cells)<8+offset:continue
                    item={"id":flight_id.group(0),"aircraft":cells[2+offset],"when":cells[3+offset],
                          "origin":cells[4+offset],"destination":cells[5+offset],
                          "rules":cells[6+offset],"duration":cells[7+offset]}
                    if re.fullmatch(r"[A-Z0-9]{3,5}",item["origin"]) and re.fullmatch(r"[A-Z0-9]{3,5}",item["destination"]):
                        flights.append(item)
                if flights:
                    result["recent_flights"]=flights[:15]
                    result["flights_checked_at"]=result["checked_at"]
                    print("Gate 404: derniers vols récupérés:",len(flights))
                else:
                    print("Gate 404: tableau non reconnu; lignes:",len(rows),"exemples:",[row["cells"][:8] for row in rows[:3]])
            except Exception as flights_error:
                print("Gate 404: lecture des vols indisponible:",type(flights_error).__name__,str(flights_error)[:120])
            browser.close()
        found=parse_public_profile(html)
        if all(found.get(k) is not None for k in ("rank","ifr_hours","vfr_hours","total_flights","airports_visited")):
            result.update({k:v for k,v in found.items() if v is not None})
            result["state"]="ok"
            result["source"]="profil public Gate 404 (navigateur Chromium)"
            result["verified_at"]=result["checked_at"]
        else:
            result["state"]="stale" if previous.get("rank") else "unparsed"
            print("Gate 404: données visibles mais extraction incomplète:", {k:v for k,v in found.items() if v is None})
    except Exception as exc:
        print("Gate 404: profil inaccessible",type(exc).__name__,str(exc)[:120])
    DEST.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Gate 404:",result["state"],"rank=",result["rank"],"hours=",result["flight_hours"])
if __name__=="__main__":run()
