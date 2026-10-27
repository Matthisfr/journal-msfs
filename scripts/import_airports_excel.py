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

def parse_addons_linker(sheet):
 records=[]
 region=""
 country=""
 section=None
 rows=sheet.iter_rows(values_only=True)
 for row in rows:
  if len(row)<13: continue
  code=str(row[6] or "").strip().upper()
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
  if section=="other": continue
  if section is None and not re.search(r"(?:^|[-_])(airport|airports|heliport|helipad)(?:[-_]|$)",folder,re.I): continue
  if not re.fullmatch(r"[A-Z0-9]{4}",code) or not version or not folder or not name: continue
  original=code
  code=CORRECTIONS.get(code,code)
  records.append({"icao":code,"original":original,"name":name,"folder":folder,
                  "installed":version,"publisher":str(row[12] or "").strip(),
                  "region":region or country,"scene_type":scene_type(code,name,folder)})
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
   code=get("icao").upper()
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
   records.append({"icao":code,"original":original,"name":name or folder,"folder":folder,"installed":version,"publisher":get("publisher"),"region":get("region"),"scene_type":scene_type(code,name,folder)})
 return records
def merge(records,old):
 by_folder={norm(a.get("folder")):a for a in old if a.get("folder")}
 by_identity={(a.get("icao"),norm(a.get("name")),norm(a.get("publisher"))):a for a in old}
 output=[]
 seen=set()
 for rec in records:
  key=norm(rec["folder"]) if rec["folder"] else (rec["icao"],norm(rec["name"]),norm(rec["publisher"]))
  if key in seen: raise ValueError(f"Doublon exact de scène dans Excel : {rec['name']}")
  seen.add(key)
  previous=by_folder.get(norm(rec["folder"])) if rec["folder"] else None
  if previous is None: previous=by_identity.get((rec["icao"],norm(rec["name"]),norm(rec["publisher"])))
  entry=dict(previous or {})
  entry.update({k:v for k,v in rec.items() if v or k in ("icao","original","installed")})
  if previous and previous.get("installed")!=entry["installed"]:
   for field in ("version_checked_at","version_comparison","version_check_state","server_version"):
    entry.pop(field,None)
   entry["status"]="UNK-V"
  entry["scene_type"]=rec.get("scene_type","airport")
  entry.setdefault("status","UNK-V")
  entry.setdefault("country",entry.get("region",""))
  output.append(entry)
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
