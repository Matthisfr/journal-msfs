#!/usr/bin/env python3
"""Compléter les fiches non trouvées chez Contrail/iniBuilds par simMarket.
Recherche par ICAO, recoupement du vendeur, de la scène et du simulateur.
Aucun résultat ambigu n'est promu au rang de version vérifiée.
"""
from __future__ import annotations
import concurrent.futures as cf
import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
from discover_airports import AIRPORTS, PUBLIC, ALIASES, airport_code, edition, norm

BASE="https://secure.simmarket.com"
UA="Mozilla/5.0 (compatible; MSFSJournalSourceResearch/1.0)"
REPORT=PUBLIC/"airport_source_candidates.json"

class Links(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True)
  self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag!="a":return
  href=dict(attrs).get("href") or ""
  if href.startswith(BASE+"/") and ".phtml" in href:
   self.links.append(href.split("?")[0].split("#")[0])
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html"})
 with urllib.request.urlopen(req,timeout=20) as resp:
  if resp.status!=200:raise ValueError(f"HTTP {resp.status}")
  return resp.read(800_000).decode("utf-8",errors="replace")
def links_for(code):
 try:
  raw=get(BASE+"/advanced_search_result.php?keywords="+urllib.parse.quote(code))
  parser=Links()
  parser.feed(raw)
  return code,list(dict.fromkeys(parser.links)),None
 except Exception as e:
  return code,[],f"{type(e).__name__}: {str(e)[:90]}"
def vendor_match(a,slug):
 prefix=a["folder"].split("-")[0].lower()
 allowed=set(ALIASES.get(prefix,(prefix,)))
 if prefix=="flightbeam" and airport_code(a)=="KPDX":allowed.add("iblueyonder")
 slug_norm=norm(slug)
 publisher=norm(a.get("publisher"))
 return any(len(x)>3 and x in slug_norm for x in allowed) or (len(publisher)>4 and publisher in slug_norm)
def candidate(a,url):
 if "(SUB" in str(a.get("icao","")):return False
 slug=urllib.parse.urlparse(url).path.rsplit("/",1)[-1].replace(".phtml","")
 code=airport_code(a)
 if not vendor_match(a,slug):return False
 if re.search(r"(?<![A-Z0-9])"+re.escape(code)+r"(?![A-Z0-9])",slug.upper().replace("-"," ")):
  return True
 # Certaines fiches utilisent la ville plutôt que le code ICAO.
 tokens=[x for x in a["folder"].split("-")[3:] if len(x)>4 and x not in ("airport","international","regional","scenery")]
 return any(norm(x) in norm(slug) for x in tokens)
def parse_page(url):
 try:
  raw=get(url)
  title_match=re.search(r"<title[^>]*>(.*?)</title>",raw,re.I|re.S)
  title=re.sub(r"<[^>]+>"," ",title_match.group(1)).strip() if title_match else ""
  # Version est une donnée explicite dans la fiche détaillée simMarket.
  m=re.search(r'>\s*Version\s*</div>\s*<span[^>]*>\s*[vV]?\s*(\d+(?:\.\d+){1,4})\s*</span>',raw,re.I|re.S)
  if not m:raise ValueError("Numéro de version non publié dans la fiche")
  # Vérifier que le produit est bien une scène MSFS, et non FSX/P3D/X-Plane.
  ed=edition(title)
  if ed=="other":raise ValueError("Produit pour un autre simulateur")
  return url,{"version":m.group(1),"title":title,"edition":ed,"store":"simMarket",
              "state":"verified","checked_at":dt.datetime.now(dt.timezone.utc).isoformat()}
 except Exception as e:
  return url,{"state":"unavailable","reason":f"{type(e).__name__}: {str(e)[:110]}"}
def run():
 data=json.loads(REPORT.read_text(encoding="utf-8"))
 byfolder={a["folder"]:a for a in AIRPORTS}
 rows=data["airports"]
 missing=[x for x in rows if not x.get("selected")]
 codes=sorted({airport_code(byfolder[x["folder"]]) for x in missing if airport_code(byfolder[x["folder"]])})
 search={}
 with cf.ThreadPoolExecutor(max_workers=8) as pool:
  for code,links,error in pool.map(links_for,codes):
   search[code]=(links,error)
 product_to_check={}
 for row in missing:
  a=byfolder[row["folder"]]
  code=airport_code(a)
  links,error=search.get(code,([],None))
  matches=[u for u in links if candidate(a,u)]
  row["simmarket_search_count"]=len(matches)
  if error:row["simmarket_error"]=error
  for url in matches[:4]:
   product_to_check[url]=True
 print("SIMMARKET",len(codes),"recherches",len(product_to_check),"fiches candidates",flush=True)
 products={}
 with cf.ThreadPoolExecutor(max_workers=8) as pool:
  for url,record in pool.map(parse_page,product_to_check):
   products[url]=record
 found=0
 for row in missing:
  a=byfolder[row["folder"]]
  links,_=search.get(airport_code(a),([],None))
  choices=[]
  for url in [u for u in links if candidate(a,u)][:4]:
   p=products.get(url,{})
   if p.get("state")!="verified":continue
   code=airport_code(a)
   if not re.search(r"(?<![A-Z0-9])"+re.escape(code)+r"(?![A-Z0-9])",
                    (p.get("title","")+" "+url.rsplit("/",1)[-1]).upper().replace("-"," ")):
    continue
   ed=p.get("edition")
   score={"2024":12,"2020+2024":10,"MSFS (édition non précisée)":5,"2020":0}.get(ed,1)
   if p.get("version")==a.get("installed"):score+=20
   v1=re.findall(r"\d+",str(a.get("installed","")))
   v2=re.findall(r"\d+",str(p.get("version","")))
   if v1 and v2 and v1[0]==v2[0]:score+=4
   if v1 and v2 and len(v1)==len(v2) and tuple(map(int,v2))<tuple(map(int,v1)):score-=6
   choices.append((score,url,p))
  choices.sort(key=lambda x:x[0],reverse=True)
  if not choices:continue
  _,url,p=choices[0]
  row["selected"]={"score":25,"store":"simMarket","title":p["title"],
                   "vendor":a.get("publisher"),"url":url,"edition":p["edition"],
                   "version":p["version"],"checked_at":p["checked_at"],"state":"verified"}
  row["state"]="source_found"
  row["matches"].append(row["selected"])
  found+=1
  print("SIMMARKET_TROUVÉ",row["icao"],row["folder"],a.get("installed"),"→",p["version"],p["edition"],url,flush=True)
 data["stores"]["simMarket"]=len(product_to_check)
 data["counts"]["source_found"]=sum(bool(x.get("selected")) for x in rows)
 data["counts"]["needs_research"]=sum(not x.get("selected") for x in rows)
 data["counts"]["pages_verified"]+=sum(x.get("state")=="verified" for x in products.values())
 data["simmarket_checked_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
 REPORT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("SIMMARKET_RÉSULTAT",found,"nouveaux liens, couverture",data["counts"],flush=True)
if __name__=="__main__":run()
