"""Rebuild the scenery comparator from the current Excel-imported airport inventory.
Preserve editorial analyses separately; never invent ratings or winners.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
airports=json.loads((ROOT/'public/airports.json').read_text(encoding='utf-8'))
reviews_path=ROOT/'data/airport_comparisons.json'
reviews=json.loads(reviews_path.read_text(encoding='utf-8')) if reviews_path.exists() else {}
# Conserver les images officielles déjà trouvées pour éviter de rescanner les boutiques quotidiennement.
cache_path=ROOT/'public/comparison_images.json'
cache=json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
def official_photo(url):
 if not url or not url.startswith('https://'): return ''
 try:
  request=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; JournalMSFS/1.0)'})
  with urlopen(request,timeout=6) as response:
   page=response.read(450000).decode('utf-8','replace')
  for pattern in (r'<meta[^>]+property=["\\']og:image["\\'][^>]+content=["\\']([^"\\']+)',r'<meta[^>]+content=["\\']([^"\\']+)["\\'][^>]+property=["\\']og:image',r'<meta[^>]+name=["\\']twitter:image["\\'][^>]+content=["\\']([^"\\']+)'):
   match=re.search(pattern,page,re.I)
   if match:
    image=urljoin(url,unescape(match.group(1)))
    if image.startswith('https://') and urlparse(image).hostname: return image
 except Exception as error:
  print(f'Photo indisponible {url}: {type(error).__name__}')
 return ''
urls={a.get('source_url') for a in airports if a.get('source_url','').startswith('https://')}
missing=sorted(u for u in urls if u not in cache)
if missing:
 with ThreadPoolExecutor(max_workers=6) as pool:
  for url,photo in zip(missing,pool.map(official_photo,missing)): cache[url]=photo
 cache_path.write_text(json.dumps(cache,ensure_ascii=False,indent=2)+'\\n',encoding='utf-8')
groups={}
for a in airports:
 code=str(a.get('icao') or '').strip().upper()
 if code: groups.setdefault(code,[]).append(a)
records=[]
for code,scenes in groups.items():
 if len(scenes)<2: continue
 review=reviews.get(code,{})
 records.append({'code':code,'name':scenes[0].get('name') or code,
  'scenes':[{'publisher':a.get('publisher') or 'Éditeur inconnu','installed':a.get('installed') or '',
             'url':a.get('source_url') or '', 'image':cache.get(a.get('source_url') or '', ''), 'comparison':a.get('version_comparison') or '',
             'server_version':a.get('server_version') or '',
             'version_state':({'equal':'À jour','update':'Mise à jour disponible','source_older':'Version installée plus récente'}.get(a.get('version_comparison'),'À vérifier'))} for a in scenes],
  'winner':review.get('winner','Non déterminé'),'confidence':review.get('confidence','Avis insuffisants'),
  'summary':review.get('summary','Aucune comparaison indépendante suffisamment fiable. Consultez les fiches officielles pour les images et avis disponibles.'),
  'criteria':review.get('criteria',[])})
(ROOT/'public/comparisons.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Comparateur : {len(records)} aéroports doublons, {sum(len(x["scenes"]) for x in records)} scènes.')
