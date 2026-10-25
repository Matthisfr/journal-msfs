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
