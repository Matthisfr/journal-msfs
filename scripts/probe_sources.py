"""Diagnostic ponctuel des moteurs de recherche publics des boutiques MSFS."""
import concurrent.futures
import urllib.request, urllib.parse, json, re
URLS = [
 "https://contrail.shop/search/suggest.json?q=BIKF&resources%5Btype%5D=product",
 "https://contrail.shop/search?q=BIKF&type=product",
 "https://contrail.shop/products.json?limit=1",
 "https://inibuilds.com/search/suggest.json?q=EGLL&resources%5Btype%5D=product",
 "https://inibuilds.com/search?q=EGLL&type=product",
 "https://inibuilds.com/products.json?limit=1",
 "https://contrail.shop/products/mk-studios-keflavik-reykjavik-airports-v2-msfs",
 "https://inibuilds.com/products/inibuilds-london-heathrow-egll-msfs-2024",
]
def probe(url):
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"text/html,application/json,*/*"})
  with urllib.request.urlopen(req,timeout=15) as resp:
   blob=resp.read(350000).decode("utf-8",errors="replace")
   title=re.search(r"<title[^>]*>(.*?)</title>",blob,re.I|re.S)
   products=re.findall(r'href="([^"]*/products/[^"]+)"',blob)[:6]
   result={"url":url,"status":resp.status,"length":len(blob),"type":resp.headers.get("Content-Type"),
           "title":title.group(1).strip() if title else "","products":products,
           "sample":re.sub(r"\s+"," ",blob[:200])}
   if "json" in (resp.headers.get("Content-Type") or ""):
    try:
     obj=json.loads(blob)
     result["json_keys"]=list(obj)[:8]
     result["json_sample"]=str(obj.get("resources",obj.get("products",{})))[:800]
    except Exception as exc: result["json_error"]=str(exc)
   return result
 except Exception as e: return {"url":url,"error":f"{type(e).__name__}: {e}"}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 for x in pool.map(probe,URLS):
  print(json.dumps(x,ensure_ascii=False))

for shop,q in [("contrail.shop","BIKF"),("inibuilds.com","EGLL"),("contrail.shop","LIRF"),("inibuilds.com","KJFK")]:
 u=f"https://{shop}/search/suggest.json?q={q}&resources%5Btype%5D=product&resources%5Blimit%5D=10"
 try:
  req=urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"})
  with urllib.request.urlopen(req,timeout=15) as resp: data=json.load(resp)
  items=data.get("resources",{}).get("results",{}).get("products",[])
  print("PRODUCTS",shop,q,len(items),json.dumps([{k:p.get(k) for k in ("title","vendor","type","url","handle","id")} for p in items],ensure_ascii=False))
 except Exception as e: print("ERROR",u,str(e))

for url in ("https://contrail.shop/products/mk-studios-keflavik-reykjavik-airports-v2-msfs",
            "https://contrail.shop/products/mk-studios-lirf-rome-fiumicino-v2-msfs-2020-2024",
            "https://inibuilds.com/products/inibuilds-london-heathrow-egll-msfs-2024"):
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
  with urllib.request.urlopen(req,timeout=15) as resp: html=resp.read(1500000).decode("utf-8",errors="replace")
  samples=[]
  for needle in ("Product Version","Version","v2.0.5","v2.0.2","1.1.0","application/ld+json","data-product"):
   matches=list(re.finditer(re.escape(needle),html,re.I))
   if matches:
    x=matches[-1] if needle=="Version" else matches[0]
    samples.append({"needle":needle,"count":len(matches),"sample":re.sub(r"\\s+"," ",html[max(0,x.start()-130):x.start()+200])})
  print("VERSION_PROBE",url,"len",len(html),json.dumps(samples,ensure_ascii=False))
 except Exception as e:print("VERSION_PROBE_ERROR",url,str(e))

for shop in ("contrail.shop","inibuilds.com"):
 for page in (1,2,3):
  url=f"https://{shop}/products.json?limit=250&page={page}"
  try:
   req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
   with urllib.request.urlopen(req,timeout=25) as resp:
    data=json.load(resp)
   ps=data.get("products",[])
   print("CATALOG",shop,page,len(ps),[(x.get("title"),x.get("vendor"),x.get("handle")) for x in ps[:2]])
  except Exception as e:print("CATALOG_ERROR",shop,page,type(e).__name__,str(e)[:160])

for url in ("https://secure.simmarket.com/search.php?keywords=LFST",
            "https://secure.simmarket.com/search.php?keywords=CYVR",
            "https://secure.simmarket.com/france-vfr-lfst-strasbourg-entzheim-msfs.phtml",
            "https://orbxdirect.com/product/essa-msfs2024",
            "https://orbxdirect.com/product/esgg-msfs"):
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
  with urllib.request.urlopen(req,timeout=18) as resp: raw=resp.read(800000).decode("utf-8",errors="replace")
  titles=re.findall(r"<title[^>]*>(.*?)</title>",raw,re.I|re.S)
  links=list(dict.fromkeys(re.findall(r'href="([^"]+\.phtml[^"]*)"',raw,re.I)))[:8]
  samples=[]
  for needle in ("Version","Published by","Product Version","1.3.3"):
   m=re.search(re.escape(needle),raw,re.I)
   if m:samples.append((needle,re.sub(r"\\s+"," ",raw[max(0,m.start()-110):m.start()+150])))
  print("OTHER_PROBE",url,"size",len(raw),"title",titles[:1],"links",links,"samples",samples)
 except Exception as e:print("OTHER_PROBE_ERROR",url,type(e).__name__,str(e)[:160])
