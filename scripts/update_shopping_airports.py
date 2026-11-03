"""Recalcul manuel de la liste de courses à partir du catalogue validé.
Aucune découverte implicite ni URL de boutique fabriquée : liens exacts seulement.
Les scènes figurant dans l'inventaire sont toujours exclues.
"""
import json
import pathlib
import re
from urllib.parse import urlparse

ROOT=pathlib.Path(__file__).resolve().parents[1]
CATALOG=ROOT/"data"/"shopping_airports_catalog.json"
OWNED=ROOT/"public"/"airports.json"
WORLD=ROOT/"public"/"world_airports.json"
OUTPUT=ROOT/"public"/"shopping_airports.json"

def main():
    catalog=json.loads(CATALOG.read_text(encoding="utf-8"))
    owned=json.loads(OWNED.read_text(encoding="utf-8"))
    index=json.loads(WORLD.read_text(encoding="utf-8"))
    owned_codes={str(a.get("icao") or "").strip().upper() for a in owned}
    result=[]
    encountered=set()
    skipped=[]
    for item in catalog:
        code=str(item.get("icao") or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{4}",code):
            raise ValueError(f"Code ICAO invalide : {code!r}")
        if code in encountered:
            raise ValueError(f"ICAO dupliqué dans le catalogue : {code}")
        encountered.add(code)
        if code in owned_codes:
            skipped.append(code)
            continue
        position=index.get(code)
        if not isinstance(position,list) or len(position)<2:
            skipped.append(code+" (coordonnées absentes)")
            continue
        lat,lon=position[:2]
        if not (-90<=float(lat)<=90 and -180<=float(lon)<=180):
            raise ValueError(f"Coordonnées incorrectes : {code}")
        shops=[]
        for entry in item.get("shops",[])[:2]:
            url=str(entry.get("url") or "").strip()
            parsed=urlparse(url)
            if parsed.scheme!="https" or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError(f"URL boutique non conforme pour {code}: {url}")
            if not re.fullmatch(r"[A-Za-z0-9.-]+",parsed.hostname or ""):
                raise ValueError(f"Hôte boutique non conforme : {code}")
            shops.append({"store":str(entry.get("store") or "Boutique")[:65],"url":url,"price_type":str(entry.get("price_type") or "Prix à vérifier")[:32],"product_title":str(entry.get("product_title") or "")[:140]})
        if not shops:
            skipped.append(code+" (aucun lien produit)")
            continue
        result.append({"icao":code,"name":str(item.get("name") or (position[2] if len(position)>2 else code))[:100],"lat":float(lat),"lon":float(lon),"type":str(item.get("type") or "airport"),"shops":shops})
    result.sort(key=lambda x:x["icao"])
    # Une liste vide est légitime lorsque tous les aéroports du catalogue sont achetés.
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Liste de courses : {len(result)} aéroports retenus ; {len(skipped)} ignorés.")
    for code in skipped:
        print("Exclu :",code)

if __name__=="__main__":
    main()
