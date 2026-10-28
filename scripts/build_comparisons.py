"""Rebuild the scenery comparator from the current Excel-imported airport inventory.
Preserve editorial analyses separately; never invent ratings or winners.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
airports=json.loads((ROOT/'public/airports.json').read_text(encoding='utf-8'))
reviews_path=ROOT/'data/airport_comparisons.json'
reviews=json.loads(reviews_path.read_text(encoding='utf-8')) if reviews_path.exists() else {}
# Conserver les images officielles déjà trouvées pour éviter de rescanner les boutiques quotidiennement.
cache_path=ROOT/'public/comparison_images.json'
try:
 cache=json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
except (ValueError, OSError):
 cache={}
# Réutiliser les images déjà publiées : comparaisons.json est versionné.
previous_path=ROOT/'public/comparisons.json'
if previous_path.exists():
 try:
  for record in json.loads(previous_path.read_text(encoding='utf-8')):
   for scene in record.get('scenes',[]):
    if scene.get('url') and scene.get('image'):
     cache.setdefault(scene['url'],scene['image'])
 except (ValueError, OSError, TypeError):
  pass
class PhotoParser(HTMLParser):
 def __init__(self):
  super().__init__()
  self.image=''
 def handle_starttag(self,tag,attrs):
  if tag!='meta' or self.image:return
  data=dict(attrs)
  if data.get('property','').lower()=='og:image' or data.get('name','').lower()=='twitter:image':
   self.image=data.get('content','')
def official_photo(url):
 if not url or not url.startswith('https://'):return ''
 try:
  request=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; JournalMSFS/1.0)'})
  with urlopen(request,timeout=6) as response:
   page=response.read(450000).decode('utf-8','replace')
  parser=PhotoParser()
  parser.feed(page)
  image=urljoin(url,parser.image) if parser.image else ''
  return image if image.startswith('https://') and urlparse(image).hostname else ''
 except Exception as error:
  print(f'Photo indisponible {url}: {type(error).__name__}')
  return ''
counts={}
for a in airports:
 code=str(a.get('icao') or '').upper()
 counts[code]=counts.get(code,0)+1
urls={a.get('source_url') for a in airports if counts.get(str(a.get('icao') or '').upper(),0)>1 and (a.get('source_url') or '').startswith('https://')}
missing=sorted(u for u in urls if not cache.get(u))
if missing:
 with ThreadPoolExecutor(max_workers=6) as pool:
  for url,photo in zip(missing,pool.map(official_photo,missing)): cache[url]=photo
 cache_path.write_text(json.dumps(cache,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
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
