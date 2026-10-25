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
        m=re.search(r"([0-9,]+)\\s+"+label,text,re.I)
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
            "source":previous.get("source"),
            "verified_at":previous.get("verified_at"),"checked_at":dt.datetime.now(dt.timezone.utc).isoformat()}
    try:
        request=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 (compatible; JournalMSFS/1.0)","Accept":"text/html"})
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            page=browser.new_page()
            page.goto(URL,wait_until="domcontentloaded",timeout=30000)
            page.get_by_text("IFR HOURS",exact=False).first.wait_for(timeout=20000)
            html=page.locator("body").inner_text()
            browser.close()
        found=parse_public_profile(html)
        if all(found.get(k) is not None for k in ("rank","ifr_hours","vfr_hours","total_flights","airports_visited")):
            result.update({k:v for k,v in found.items() if v is not None})
            result["state"]="ok"
            result["source"]="profil public Gate 404 (navigateur Chromium)"
            result["verified_at"]=result["checked_at"]
        else:
            result["state"]="stale" if previous.get("rank") else "unparsed"
            print("Gate 404: page reçue, données probablement chargées en JavaScript")
    except Exception as exc:
        print("Gate 404: profil inaccessible",type(exc).__name__,str(exc)[:120])
    DEST.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Gate 404:",result["state"],"rank=",result["rank"],"hours=",result["flight_hours"])
if __name__=="__main__":run()
