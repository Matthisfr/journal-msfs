#!/usr/bin/env python3
"""Surveillance prudente des fiches Airbus du fabricant Santiluib3 (S3)."""
from __future__ import annotations
import datetime as dt
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from html import unescape
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"public"/"s3_airbus.json"
SITE="https://www.santiluib3.com/"
AIRBUS=re.compile(r"airbus|a320|a319|a321|a32x|a330|a350|fenix|ecam|overhead|m(c|f)du|rmp|fcu|efis|pedestal|sidestick|autobrake",re.I)
EXCLUDE=re.compile(r"boeing|737|747|777|787|cessna|airliner 737",re.I)

class MetaImage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image=""
    def handle_starttag(self,tag,attrs):
        if tag!="meta":return
        a=dict(attrs)
        if a.get("property") in ("og:image","og:image:secure_url") or a.get("name")=="twitter:image":
            self.image=self.image or a.get("content","")

def product_details(url):
    """Fiche Shopify officielle : image, prix et stock; repli sur og:image."""
    req=Request(url+".js",headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    try:
        with urlopen(req,timeout=15) as response:
            data=json.load(response)
        variants=data.get("variants") or []
        prices=[v.get("price") for v in variants if isinstance(v.get("price"),(int,float))]
        raw_image=data.get("featured_image") or (data.get("images") or [""])[0]
        if isinstance(raw_image,dict):raw_image=raw_image.get("src","")
        return {"image_url":urljoin(SITE,str(raw_image).replace("//","https://",1) if str(raw_image).startswith("//") else str(raw_image)),
                "price":round(min(prices)/100,2) if prices else None,
                "currency":"", "availability":"Disponible" if any(v.get("available") for v in variants) else "Indisponible",
                "published_at":data.get("published_at")}
    except Exception:
        try:
            with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=15) as response:
                html=response.read(1_000_000).decode("utf-8","replace")
            parser=MetaImage()
            parser.feed(html)
            return {"image_url":urljoin(SITE,unescape(parser.image)) if parser.image else ""}
        except Exception:return {}

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

def fetch_catalog():
    """Catalogue Shopify paginé, sans se limiter aux liens de l'accueil."""
    found={}
    for page in range(1,31):
        endpoint=urljoin(SITE,f"products.json?limit=250&page={page}")
        request=Request(endpoint,headers={"User-Agent":"Mozilla/5.0 (compatible; JournalMSFS/1.0)","Accept":"application/json"})
        with urlopen(request,timeout=35) as response:
            batch=json.load(response).get("products",[])
        if not batch:break
        for item in batch:
            title=str(item.get("title") or "").strip()
            handle=str(item.get("handle") or "").strip()
            desc=re.sub(r"<[^>]+>"," ",str(item.get("body_html") or ""))
            tags=item.get("tags") or []
            if isinstance(tags,list):tags=" ".join(map(str,tags))
            corpus=" ".join([title,handle,str(item.get("product_type") or ""),str(tags),desc[:300]])
            if EXCLUDE.search(title+" "+handle):continue
            # S3 est un fabricant Airbus : conserver les composants même sans A320 dans le titre.
            if not AIRBUS.search(corpus) and not re.search(r"panel|switch|button|knob|rotary|encoder|light|dimmer|mount|board|kit|gauge|module|cockpit|display|screen|throttle|quadrant|lever|handle|printable|download",corpus,re.I):continue
            if not handle:continue
            url=urljoin(SITE,"products/"+handle)
            images=item.get("images") or []
            featured=item.get("image") or (images[0] if images else {})
            raw_image=featured.get("src","") if isinstance(featured,dict) else str(featured)
            variants=item.get("variants") or []
            prices=[]
            for v in variants:
                try:prices.append(float(v["price"]))
                except (KeyError,TypeError,ValueError):pass
            found[url]={
                "id":url,"title":title,"url":url,
                "image_url":urljoin(SITE,raw_image) if raw_image else "",
                "price":min(prices) if prices else None,
                "currency":"",
                "availability":"Disponible" if any(v.get("available") for v in variants) else "Indisponible",
                "published_at":item.get("published_at"),
                "updated_at":item.get("updated_at"),
            }
        if len(batch)<250:break
    return list(found.values())

def main():
    previous={}
    if OUT.exists():
        try:previous=json.loads(OUT.read_text(encoding="utf-8"))
        except (ValueError,OSError):pass
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        products=fetch_catalog()
        if not products:raise ValueError("Catalogue Shopify vide ou inaccessible")
        before={x["id"]:x for x in previous.get("products",[])}
        changes=[x for x in products if x["id"] not in before]
        data={"checked_at":now,"source_url":SITE,"source_state":"ok","products":products,"changes":changes,"total":len(products)}
        print(f"S3 Airbus: {len(products)} produits, {len(changes)} nouvelles fiches")
    except Exception as exc:
        data={**previous,"checked_at":now,"source_url":SITE,"source_state":"unavailable","error":str(exc)[:200]}
        data.setdefault("products",[])
        data.setdefault("changes",[])
        print("S3 Airbus: catalogue non confirmé, anciennes données conservées:",exc)
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
