#!/usr/bin/env python3
"""Surveillance prudente des fiches Airbus du fabricant Santiluib3 (S3)."""
from __future__ import annotations
import datetime as dt
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"public"/"s3_airbus.json"
SITE="https://www.santiluib3.com/"
AIRBUS=re.compile(r"airbus|a320|a319|a321|a32x|a330|a350|fenix|ecam|overhead|m(c|f)du|rmp|fcu|efis|pedestal|sidestick|autobrake",re.I)
EXCLUDE=re.compile(r"boeing|737|747|777|787|cessna|airliner 737",re.I)

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href=None
        self.text=[]
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.href=dict(attrs).get("href","")
            self.text=[]
    def handle_data(self,data):
        if self.href is not None:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.href is not None:
            self.links.append((self.href," ".join(self.text).strip()))
            self.href=None

def main():
    previous={}
    if OUT.exists():
        try:previous=json.loads(OUT.read_text(encoding="utf-8"))
        except (ValueError,OSError):pass
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        request=Request(SITE,headers={"User-Agent":"Mozilla/5.0 (compatible; JournalMSFS/1.0)"})
        with urlopen(request,timeout=25) as response:
            html=response.read(2_000_000).decode("utf-8","replace")
        parser=Links()
        parser.feed(html)
        products=[]
        seen=set()
        for href,title in parser.links:
            url=urljoin(SITE,href)
            host=urlparse(url).hostname or ""
            if not (host=="santiluib3.com" or host.endswith(".santiluib3.com")):continue
            if not AIRBUS.search(title+" "+url) or EXCLUDE.search(title+" "+url):continue
            if url in seen or not title or len(title)>150:continue
            seen.add(url)
            products.append({"id":url,"title":title,"url":url,"image_url":"","price":None,"currency":"","availability":"À confirmer sur la fiche officielle","published_at":None})
        if not products:
            raise ValueError("Aucune fiche Airbus identifiable automatiquement sur la page officielle")
        before={x["id"]:x for x in previous.get("products",[])}
        changes=[x for x in products if x["id"] not in before]
        data={"checked_at":now,"source_url":SITE,"source_state":"ok","products":products,"changes":changes}
        print(f"S3 Airbus: {len(products)} liens Airbus, {len(changes)} nouveaux")
    except Exception as exc:
        data={**previous,"checked_at":now,"source_url":SITE,"source_state":"unavailable","error":str(exc)[:200]}
        data.setdefault("products",[])
        data.setdefault("changes",[])
        print("S3 Airbus: collecte non confirmée, anciennes données conservées:",exc)
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
