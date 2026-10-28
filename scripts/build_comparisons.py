"""Rebuild the scenery comparator from the current Excel-imported airport inventory.
Preserve editorial analyses separately; never invent ratings or winners.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
airports=json.loads((ROOT/'public/airports.json').read_text(encoding='utf-8'))
reviews_path=ROOT/'data/airport_comparisons.json'
reviews=json.loads(reviews_path.read_text(encoding='utf-8')) if reviews_path.exists() else {}
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
             'url':a.get('source_url') or '', 'comparison':a.get('version_comparison') or ''} for a in scenes],
  'winner':review.get('winner','Non déterminé'),'confidence':review.get('confidence','Avis insuffisants'),
  'summary':review.get('summary','Aucune comparaison indépendante suffisamment fiable. Consultez les fiches officielles pour les images et avis disponibles.')})
(ROOT/'public/comparisons.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Comparateur : {len(records)} aéroports doublons, {sum(len(x["scenes"]) for x in records)} scènes.')
