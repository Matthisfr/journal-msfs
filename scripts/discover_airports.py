#!/usr/bin/env python3
"""Recherche des fiches *exactes* de scènes MSFS dans les catalogues publics.
Phase d'inventaire : aucune version n'est modifiée ici. Le résultat doit être
contrôlé avant d'être activé pour la veille quotidienne.
"""
from __future__ import annotations
import concurrent.futures as cf
import datetime as dt
import html
import json
from pathlib import Path
import re
import time
import unicodedata
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/"public"
AIRPORTS=json.loads((PUBLIC/"airports.json").read_text(encoding="utf-8"))
UA="Mozilla/5.0 (compatible; MSFSJournalAirportSource/1.0)"
SHOPS={"Contrail":"https://contrail.shop","iniBuilds":"https://inibuilds.com"}
ALIASES={
 "inibuilds":("inibuilds",),"mkstudios":("mkstudios",),"flytampa":("flytampa",),
 "tms":("taimodels",),"lvfr":("lvfr","latinvfr"),"fsxcenery":("msfscenerybuilders","fsxcenery"),
 "pacsim":("pacsim",),"glideslope":("glideslopepro","glideslope"),
 "finalapproach":("finalapproach",),"flyhigh":("fly2high","flyhigh","fl2"),
 "fsdreamteam":("fsdreamteam",),"rdpresets":("rdpresets",),
 "flightbeam":("flightbeam","iblueyonder"),"jetstream":("jetstreamdesigns","jetstream"),
 "orbx":("orbx",),"29palms":("29palms",),"simwings":("simwings",),
 "aerosoft":("aerosoft",),"francevfr":("francevfr",),"pilotexperiencesim":("pilotexperiencesim",),
 "fsx3d":("fsx3d",),"dominicdesignteam":("dominicdesignteam",),
 "drzewieckidesign":("drzewieckidesign",),"fsdg":("fsdg",),"prealsoft":("prealsoft",),
 "uk2000scenery":("uk2000scenery",),"sofly":("sofly",),"tropicalsim":("tropicalsim",),
 "simnord":("simnord",),"verticalsim":("verticalsim",),"digitaldesign":("digitaldesign",),
 "dreamflight":("dreamflight",),"ad":("aerodesigns",),"feelthere":("feelthere",),
 "perfectsoft":("perfectsoft",),"net":("netdesign",),"xcodr":("xcodr",),
 "mmsimulations":("mmsimulations","mmsimulations"),
 "fsxcenery":("msfscenerybuilders","fsxcenery"),
 "bravoairspace":("bravoairspace",),"dfflyerdirect":("dfflyerdirect",),
 "slhsimdesigns":("slhsimdesigns",),"azrsim":("azrsim",),
 "justsim":("justsim",),"bmw":("beautifulmodeloftheworld","bmw"),
 "euroscene":("euroscene",),"flydesign":("flydesign",),
 "scenerytr":("scenerytr",),"doublet":("doublet",),
 "mexhighflight":("mexhighflight",),"photorico":("photorico",),
 "propairflight":("propairflight",),"vref":("vrefsimulations",),
 "rdpresets":("rdpresets",),"tropicalsim":("tropicalsim",),
}
def norm(s):
 s=unicodedata.normalize("NFKD",str(s or ""))
 return re.sub(r"[^a-z0-9]+","",s.lower())
def request_json(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=30) as response:
  return json.load(response)
def request_html(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html"})
 with urllib.request.urlopen(req,timeout=25) as response:
  if response.status!=200: raise ValueError(f"HTTP {response.status}")
  return response.read(1_600_000).decode("utf-8",errors="replace")
def catalog(shop,base):
 all_products=[]
 errors=[]
 for page in range(1,35):
  url=f"{base}/products.json?limit=250&page={page}"
  try:
   obj=request_json(url)
   products=obj.get("products",[])
   if not isinstance(products,list): raise ValueError("Format inattendu")
   if not products: break
   all_products.extend(products)
   if len(products)<250: break
  except Exception as exc:
   errors.append(f"{shop} page {page}: {type(exc).__name__}: {str(exc)[:100]}")
   break
 print(f"CATALOGUE {shop}: {len(all_products)} produits, {len(errors)} erreurs",flush=True)
 return shop,all_products,errors
def airport_code(a):
 icao=str(a.get("icao",""))
 m=re.search(r"[A-Z0-9]{4}",icao)
 return m.group(0) if m else ""
def edition(title):
 s=norm(title)
 if any(t in s for t in ("xplane","xpl","xp12","xp11","prepar3d","p3dv","fsxonly")):
  return "other"
 has24=any(t in s for t in ("2024","msfs24","fs24"))
 has20=any(t in s for t in ("2020","msfs20","fs20"))
 if has24 and has20:return "2020+2024"
 if has24:return "2024"
 if has20:return "2020"
 if "msfs" in s or "flightsimulator" in s:return "MSFS (édition non précisée)"
 return "unknown"
def vendor_matches(a,p):
 prefix=a["folder"].split("-")[0].lower().strip()
 publisher=norm(a.get("publisher"))
 vendor=norm(p.get("vendor"))
 allowed=set(ALIASES.get(prefix,(prefix,)))
 if prefix=="flightbeam" and airport_code(a)=="KPDX": allowed.add("iblueyonder")
 if vendor in allowed:return True
 if vendor==publisher and vendor:return True
 # Ne jamais accepter une autre marque au seul motif qu'elle figure dans son URL.
 return False
def score(a,p,shop):
 title=str(p.get("title") or "")
 handle=str(p.get("handle") or "")
 code=airport_code(a)
 if not code:return -999
 if not re.search(r"(?<![A-Z0-9])"+re.escape(code)+r"(?![A-Z0-9])",title.upper()+" "+handle.upper().replace("-"," ")):
  return -999
 ed=edition(title+" "+handle)
 if ed=="other":return -999
 if norm(p.get("product_type")) not in ("scenery","airport","airports",""):
  return -999
 if not vendor_matches(a,p):return -999
 prefix=a["folder"].split("-")[0]
 if "(SUB" in a["icao"]:
  suffix=a["folder"].split(code.lower(),1)[-1]
  qualifier="city" if "city" in a["folder"] else "jetway" if "jetway" in a["folder"] else "tree"
  if qualifier not in norm(title+" "+handle):return -999
 base=20
 if ed=="2024":base+=7
 elif ed=="2020+2024":base+=6
 elif ed=="MSFS (édition non précisée)":base+=3
 elif ed=="2020":base+=1
 else:base-=2
 if shop=="iniBuilds" and prefix=="inibuilds":base+=3
 if shop=="Contrail" and prefix!="inibuilds":base+=2
 major_match=re.search(r"(?<![A-Za-z0-9])v([1-9])(?:\b|[ .-])",title,re.I)
 if major_match:
  installed_major=str(a.get("installed","")).split(".")[0]
  base += 5 if major_match.group(1)==installed_major else -9
 if "premium" in norm(title) and "premium" not in norm(a.get("name")):base-=1
 return base
def parse_product_version(raw,shop):
 if shop=="Contrail":
  m=re.search(r"<dt>\s*Version\s*</dt>\s*<dd>\s*v?\s*(\d+(?:\.\d+){1,4})\s*</dd>",raw,re.I)
 else:
  m=re.search(r"Product\s+Version\s*</h3>\s*<div[^>]*>\s*<p>\s*v?\s*(\d+(?:\.\d+){1,4})\s*</p>",raw,re.I|re.S)
 return m.group(1) if m else None
def analyze_product(item):
 shop,p=item
 url=SHOPS[shop]+"/products/"+p["handle"]
 try:
  raw=request_html(url)
  version=parse_product_version(raw,shop)
  if not version:raise ValueError("Version non publiée ou format non reconnu")
  return url,{"version":version,"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),"state":"verified"}
 except Exception as e:
  return url,{"version":None,"state":"unavailable","reason":(type(e).__name__+": "+str(e))[:140]}
def run():
 with cf.ThreadPoolExecutor(max_workers=2) as pool:
  results=list(pool.map(lambda kv:catalog(*kv),SHOPS.items()))
 products=[]
 for shop,items,errors in results:
  for p in items:
   if p.get("handle") and p.get("title"):products.append((shop,p))
 all_rows=[]
 selected={}
 for a in AIRPORTS:
  matches=[]
  for shop,p in products:
   value=score(a,p,shop)
   if value>=20:
    matches.append((value,shop,p))
  matches.sort(key=lambda x:x[0],reverse=True)
  chosen=matches[:3]
  row={"folder":a["folder"],"icao":a["icao"],"name":a.get("name"),
       "publisher":a.get("publisher"),"installed":a.get("installed"),
       "matches":[{"score":sc,"store":shop,"title":p["title"],"vendor":p.get("vendor"),
                   "url":SHOPS[shop]+"/products/"+p["handle"],"edition":edition(p["title"]+" "+p["handle"])}
                  for sc,shop,p in chosen]}
  all_rows.append(row)
  for sc,shop,p in chosen[:2]:
   selected[(shop,p["handle"])]=(shop,p)
 print(f"CANDIDATES: {sum(bool(x['matches']) for x in all_rows)} / {len(all_rows)} scènes ; pages à vérifier: {len(selected)}",flush=True)
 versions={}
 with cf.ThreadPoolExecutor(max_workers=8) as pool:
  for url,record in pool.map(analyze_product,selected.values()):
   versions[url]=record
 for row in all_rows:
  for match in row["matches"]:
   match.update(versions.get(match["url"],{}))
  row["selected"]=next((x for x in row["matches"] if x.get("version") and x["edition"] not in ("other","unknown")),None)
  if row["selected"]:
   row["state"]="source_found"
  else:row["state"]="needs_research"
 counts={"source_found":sum(x["state"]=="source_found" for x in all_rows),
         "needs_research":sum(x["state"]=="needs_research" for x in all_rows),
         "pages_verified":sum(x.get("version") is not None for x in versions.values())}
 output={"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
         "stores":{shop:len(items) for shop,items,err in results},
         "catalog_errors":{shop:err for shop,items,err in results if err},
         "counts":counts,"airports":all_rows}
 out=PUBLIC/"airport_source_candidates.json"
 out.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("RÉSULTAT",json.dumps(counts,ensure_ascii=False),flush=True)
 for row in all_rows:
  x=row.get("selected")
  if x:
   print("TROUVÉ",row["icao"],row["folder"],row["installed"],"→",x["version"],x["store"],x["edition"],x["url"],flush=True)
  else:
   print("MANQUANT",row["icao"],row["folder"],row["publisher"],flush=True)
if __name__=="__main__":run()
