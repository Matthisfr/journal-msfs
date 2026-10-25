"""Télécharger de vraies photos produit (jamais des illustrations inventées).
Recherche sur les fiches publiques du revendeur WINCTRL et conserve une photo
uniquement lorsque le nom de produit correspond ; sinon 'photo non publiée'.
Les fichiers locaux évitent le suivi tiers et les images cassées.
"""
from __future__ import annotations
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/"public"
DEST=PUBLIC/"hardware"
DEST.mkdir(exist_ok=True)
SOURCE="https://winwingturkiye.com/"
ALIASES={
 "fcu":["fcu"],"efis":["efis"],"mcdu":["mcdu"],"nws":["tiller","nws"],
 "rmp":["rmp"],"tcas":["tcas"],"throttle":["throttle"],"pac":["pac"],
 "pedals":["rudder","pedals"],"acp":["acp32"],"ovhd":["overhead","ovhd"],
 "agp":["agp","landing gear"]
}
class ImgParser(HTMLParser):
    def __init__(self):
        super().__init__();self.images=[];self.meta=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="img":
            self.images.append({"alt":a.get("alt",""),"src":a.get("data-src") or a.get("src",""),
                "srcset":a.get("data-srcset") or a.get("srcset","")})
        if tag=="meta" and a.get("property")=="og:image":
            self.meta.append(a.get("content",""))
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; JournalMSFS/1.0)","Accept":"text/html,image/*"})
    with urllib.request.urlopen(req,timeout=14) as resp:
        return resp.read(2_500_000),resp.headers.get("Content-Type","")
def image_url(record):
    src=record["src"]
    if ("data:image" in src or "placeholder" in src.lower()) and record["srcset"]:
        src=record["srcset"].split(",")[-1].strip().split(" ")[0]
    return urllib.parse.urljoin(SOURCE,src)
def match_image(page,keywords):
    parser=ImgParser();parser.feed(page)
    # Prefer alt tags that actually name the physical device, never a logo.
    candidates=[]
    for img in parser.images:
        alt=img["alt"].lower()
        url=image_url(img)
        if not url.startswith("https://") or "winwingturkiye.com" not in urllib.parse.urlparse(url).netloc:continue
        if any(x in alt for x in keywords) and not any(x in alt for x in ("logo","banner","icon")):
            candidates.append((len(alt),url,alt))
    candidates.sort(reverse=True)
    return candidates[0][1] if candidates else None
def run():
    items=json.loads((PUBLIC/"hardware_catalog.json").read_text())
    manifest={}
    for x in items:
        key=x["id"];existing=next((DEST/(key+"."+ext) for ext in ("jpg","png","webp") if (DEST/(key+"."+ext)).is_file()),None)
        if existing:
            manifest[key]={"path":"hardware/"+existing.name,"state":"photo","source":"Photographie de produit — winwingturkiye.com"}
            continue
        queries=[x["image_query"],x["name"]]
        try:
            for query in queries:
                url=SOURCE+"?"+urllib.parse.urlencode({"s":query,"post_type":"product"})
                page,typ=fetch(url)
                src=match_image(page.decode("utf-8","replace"),ALIASES[key])
                if not src:continue
                data,typ=fetch(src)
                if not 2000<len(data)<2_500_000:continue
                ext=("jpg" if data[:3]==b"\xff\xd8\xff" else "png" if data.startswith(b"\x89PNG\r\n\x1a\n") else "webp" if data[:4]==b"RIFF" and data[8:12]==b"WEBP" else "")
                if not ext:continue
                path=DEST/(key+"."+ext);path.write_bytes(data)
                manifest[key]={"path":"hardware/"+path.name,"state":"photo",
                               "source":"Photographie de produit — winwingturkiye.com","origin":src}
                break
            else:
                manifest[key]={"state":"unpublished","reason":"Photographie produit exacte non trouvée sur les pages publiques du revendeur"}
        except Exception as exc:
            manifest[key]={"state":"unavailable","reason":type(exc).__name__+" : "+str(exc)[:90]}
    (PUBLIC/"hardware-images.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print("Photos matérielles réelles:",sum(x["state"]=="photo" for x in manifest.values()),"/",len(items))
if __name__=="__main__":run()
