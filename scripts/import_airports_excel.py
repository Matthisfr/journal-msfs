"""Import an airport inventory Excel safely, preserving publisher audits and scene duplicates.

Put the newest .xlsx in data/airports/. The workbook must contain columns for
airport code, scene name or package folder, and installed version.
"""
from __future__ import annotations
import json, pathlib, re, sys, unicodedata
ROOT=pathlib.Path(__file__).resolve().parents[1]
DIR=ROOT/"data"/"airports"
OUT=ROOT/"public"/"airports.json"
ALIASES={
 "icao":{"icao","code","code icao","airport code","airport","code aeroport","aeroport"},
 "name":{"name","nom","scene","scene name","nom scene","airport name","nom aeroport"},
 "folder":{"folder","dossier","package","package name","nom dossier","community folder","repertoire"},
 "installed":{"installed","version","version installee","installed version","version locale","local version"},
 "publisher":{"publisher","editeur","developer","developpeur","auteur"},
 "region":{"region","continent","zone","category","categorie"},
 "description":{"description","desceitption","desc","commentaire","commentaires","details","detail"},
}
CORRECTIONS={"BCGB":"LXGB","KABK":"KABQ"}
def norm(value):
 s=unicodedata.normalize("NFKD",str(value or "")).encode("ascii","ignore").decode().lower()
 return re.sub(r"[^a-z0-9]+"," ",s).strip()
def colmap(row):
 labels=[norm(x) for x in row]
 return {key:next((i for i,label in enumerate(labels) if label in names),None) for key,names in ALIASES.items()}
def is_sub_scene(*values):
 return any(re.search(r"\(\s*sub\b",str(value or ""),re.I) for value in values)

def scene_type(code,name,folder):
 value=norm(" ".join(str(x or "") for x in (name,folder)))
 return "heliport" if re.search(r"\b(heliport|heliports|helipad|helipads|helistop|helisurface|helisurfaces)\b",value) else "airport"

def section_kind(value):
 # Les titres Addons Linker peuvent porter des compteurs : (4 / 4), (0/62).
 raw=str(value or "").strip()
 raw=re.sub(r"\s*\(\s*\d+\s*(?:/\s*\d+)?\s*\)\s*$","",raw)
 label=norm(raw)
 if label in {"aeroport","aeroports","airport","airports","airfield","airfields","aerodrome","aerodromes","heliport","heliports"}:
  return "airports"
 if label in {"decor","decors","scenery","sceneries","city","cities","ville","villes","landmark","landmarks","divers","other","autres"}:
  return "other"
 return None

def extract_icao_codes(value):
 # Accept explicit ICAO lists in the export, including custom simulator IDs AQ80/AQ85.
 raw=str(value or "").upper().strip()
 if re.fullmatch(r"[A-Z0-9]{4}",raw):
  return [CORRECTIONS.get(raw,raw)]
 # Only a clearly delimited list; never harvest four-letter words from names.
 if not re.fullmatch(r"[A-Z0-9]{4}(?:\s*(?:[,;/+&]|\bAND\b|\bET\b)\s*[A-Z0-9]{4})+",raw):
  return []
 return list(dict.fromkeys(CORRECTIONS.get(c,c) for c in re.findall(r"[A-Z0-9]{4}",raw) if c not in ("2020","2024")))

def associated_airport_codes(code,name,folder,description=""):
 # Only airport codes explicitly grouped in a scene title, folder or description.
 # Do not invent secondary airports based on geographical proximity.
 text=" ".join(str(v or "") for v in (name,folder,description)).upper()
 groups=re.findall(r"(?<![A-Z0-9])(?:[A-Z0-9]{4}\s*(?:[,;/+&]|\bAND\b|\bET\b)\s*)+[A-Z0-9]{4}(?![A-Z0-9])",text)
 found=[]
 for group in groups:
  for secondary in extract_icao_codes(group):
   if secondary!=code and secondary not in found:
    found.append(secondary)
 return found

def parse_addons_linker(sheet):
 records=[]
 region=""
 country=""
 section=None
 rows=sheet.iter_rows(values_only=True)
 for row in rows:
  if len(row)<13: continue
  raw_code=str(row[6] or "").strip().upper()
  codes=extract_icao_codes(raw_code)
  code=codes[0] if codes else raw_code
  # Only heading rows (no ICAO) can change the active category.
  if not code:
   for cell in row[:6]:
    kind=section_kind(cell)
    if kind:
     section=kind
     break
  if row[3] and not row[4] and not row[5]:
   region=str(row[3]).split(" (")[0].strip()
  if row[4] and not row[5]:
   country=str(row[4]).split(" (")[0].strip()
  folder=str(row[5] or row[4] or "").strip()
  version=str(row[9] or "").strip()
  name=str(row[11] or folder).strip()
  if is_sub_scene(code,name,folder): continue
  # Un code ICAO présent explicitement dans le nom ou dossier indique une scène
  # aéroport, même si Addons Linker la range dans une section non standard.
  # Ne jamais importer les simples décors de villes sans code dans leur nom.
  explicit_code=bool(code and re.search(r"(?<![A-Z0-9])"+re.escape(code)+r"(?![A-Z0-9])", (name+" "+folder).upper()))
  airport_folder=bool(re.search(r"(?:^|[-_])(airport|airports|heliport|helipad)(?:[-_]|$)",folder,re.I))
  if section=="other" and not (explicit_code and airport_folder): continue
  if section is None and not (airport_folder or explicit_code): continue
  if not re.fullmatch(r"[A-Z0-9]{4}",code) or not version or not folder or not name: continue
  original=code
  code=CORRECTIONS.get(code,code)
  base={"icao":code,"original":original,"name":name,"folder":folder,
                  "installed":version,"publisher":str(row[12] or "").strip(),
                  "region":region or country,"description":str(row[10] or "").strip(),
                  "scene_type":scene_type(code,name,folder)}
  records.append(base)
  for secondary in dict.fromkeys(codes[1:]+associated_airport_codes(code,name,folder,base["description"])):
   records.append(dict(base,icao=secondary,original=secondary,
                       name=secondary+" — "+name,pack_primary_icao=code,
                       pack_secondary=True))
 if not records:
  raise ValueError("Aucune scène aéroport/héliport valide dans l'export Addons Linker : import annulé")
 return records

def parse(book):
 from openpyxl import load_workbook
 wb=load_workbook(book,read_only=True,data_only=True)
 if any(str(cell.value or "").strip()=="ICAO Duplicate" for cell in wb.active[1]):
  return parse_addons_linker(wb.active)
 records=[]
 for sheet in wb:
  rows=sheet.iter_rows(values_only=True)
  for header in rows:
   if not any(v is not None for v in header): continue
   cols=colmap(header)
   if cols["installed"] is not None and (cols["folder"] is not None or cols["name"] is not None) and cols["icao"] is not None:
    break
  else: continue
  for row in rows:
   def get(key):
    idx=cols[key]
    return str(row[idx]).strip() if idx is not None and idx<len(row) and row[idx] is not None else ""
   raw_code=get("icao").upper()
   codes=extract_icao_codes(raw_code)
   code=codes[0] if codes else raw_code
   folder=get("folder")
   name=get("name")
   version=get("installed")
   if is_sub_scene(code,name,folder): continue
   if not code and not folder and not name: continue
   if not code or not version or not (folder or name):
    raise ValueError(f"{sheet.title}: ligne incomplète : ICAO, scène/dossier et version requis")
   if not re.fullmatch(r"[A-Z0-9]{4}",code): continue
   original=code
   code=CORRECTIONS.get(code,code)
   base={"icao":code,"original":original,"name":name or folder,"folder":folder,"installed":version,"publisher":get("publisher"),"region":get("region"),"description":get("description"),"scene_type":scene_type(code,name,folder)}
   records.append(base)
   for secondary in dict.fromkeys(codes[1:]+associated_airport_codes(code,name,folder,base["description"])):
    records.append(dict(base,icao=secondary,original=secondary,name=secondary+" — "+base["name"],pack_primary_icao=code,pack_secondary=True))
 return records
def merge(records,old):
 by_folder={(norm(a.get("folder")),a.get("icao")):a for a in old if a.get("folder")}
 by_identity={(a.get("icao"),norm(a.get("name")),norm(a.get("publisher"))):a for a in old}
 output=[]
 seen={}
 duplicates=0
 for rec in records:
  key=("folder",norm(rec["folder"]),rec["icao"]) if rec["folder"] else ("identity",rec["icao"],norm(rec["name"]),norm(rec.get("publisher")))
  if key in seen:
   prior=seen[key]
   comparable=("icao","installed","name","publisher","folder","scene_type")
   if any(norm(prior.get(field))!=norm(rec.get(field)) for field in comparable):
    raise ValueError(f"Scène répétée avec données contradictoires : {rec['name']}")
   duplicates+=1
   continue
  seen[key]=rec
  previous=by_folder.get((norm(rec["folder"]),rec["icao"])) if rec["folder"] else None
  if previous is None: previous=by_identity.get((rec["icao"],norm(rec["name"]),norm(rec.get("publisher"))))
  entry=dict(previous or {})
  entry.update({k:v for k,v in rec.items() if v or k in ("icao","original","installed","description")})
  if previous and previous.get("installed")!=entry["installed"]:
   for field in ("version_checked_at","version_comparison","version_check_state","server_version"):
    entry.pop(field,None)
   entry["status"]="UNK-V"
  entry["scene_type"]=rec.get("scene_type","airport")
  entry.setdefault("status","UNK-V")
  entry.setdefault("country",entry.get("region",""))
  output.append(entry)
 if duplicates: print(f"Doublons identiques ignorés : {duplicates}")
 return output
def main():
 files=sorted(DIR.glob("*.xlsx"),key=lambda p:(p.stat().st_mtime,p.name),reverse=True) if DIR.exists() else []
 if not files:
  print("Aucun fichier Excel : inventaire actuel conservé.")
  return
 if len(files)>1: raise ValueError("Plusieurs fichiers Excel présents : conserver un seul fichier dans data/airports/")
 records=parse(files[0])
 if len(records)<10: raise ValueError(f"Import annulé : seulement {len(records)} scènes (minimum 10)")
 old=json.loads(OUT.read_text(encoding="utf-8"))
 result=merge(records,old)
 OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(f"Excel importé : {files[0].name}, {len(result)} scènes, {len(set(a['icao'] for a in result))} codes")
if __name__=="__main__":
 try: main()
 except Exception as exc:
  print(f"ERREUR IMPORT EXCEL : {exc}",file=sys.stderr)
  raise
