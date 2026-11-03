#!/usr/bin/env python3
"""Recherche à la demande de scènes MSFS non possédées : >=50 aéroports et >=50 aérodromes.
Sources : catalogues Shopify publics iniBuilds/Contrail et coordonnées/type OurAirports.
Le résultat n'est jamais inventé : il contient uniquement des pages produit exactes publiées.
"""
import csv
import io
import json
import pathlib
import re
import urllib.request
import urllib.parse
from collections import defaultdict

ROOT=pathlib.Path(__file__).resolve().parents[1]
PUBLIC=ROOT/"public"
CATALOG=ROOT/"data"/"shopping_airports_catalog.json"
OUT=PUBLIC/"shopping_airports.json"
AIRPORT_URL="https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv"
STORES={"iniBuilds":"https://inibuilds.com","Contrail":"https://contrail.shop"}
MIN_COUNT=50
UA="Mozilla/5.0 (compatible; MSFS-Journal-Shopping-Airports/1.0)"
CODE_RE=re.compile(r"(?<![A-Z0-9])([A-Z]{4})(?![A-Z0-9])")
NOT_AIRPORT=re.compile(r"\b(city|cities|landmark|bridge|vessel|ship|aircraft|livery|airport enhancement pack|terrain mesh|global)\b",re.I)

def request(url,timeout=50):
    headers={"User-Agent":UA,"Accept":"application/json,text/csv;q=0.9,*/*;q=0.5"}
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=timeout) as response:
        return response.read()

def airports():
    airport_index={}
    for row in csv.DictReader(io.StringIO(request(AIRPORT_URL,75).decode("utf-8-sig"))):
        typ=str(row.get("type") or "")
        if typ not in ("large_airport","medium_airport","small_airport"):
            continue
        codes={str(row.get(key) or "").upper().strip() for key in ("icao_code","gps_code","ident")}
        try:
            lat=float(row.get("latitude_deg") or "")
            lon=float(row.get("longitude_deg") or "")
        except ValueError:
            continue
        if not (-90<=lat<=90 and -180<=lon<=180):continue
        if str(row.get("scheduled_service") or "")=="yes": scheduled=True
        else:scheduled=False
        for code in codes:
            if re.fullmatch(r"[A-Z]{4}",code):
                value={"icao":code,"name":row.get("name") or code,"type":typ,"lat":lat,"lon":lon,"scheduled":scheduled,
                       "country":str(row.get("iso_country") or "")}
                if code not in airport_index or typ=="large_airport":airport_index[code]=value
    return airport_index

def shop_catalog(store,base):
    products=[]
    for page in range(1,45):
        url=base+"/products.json?limit=250&page="+str(page)
        try:
            data=json.loads(request(url).decode("utf-8"))
            batch=data.get("products",[])
            if not isinstance(batch,list):raise ValueError("Format Shopify non reconnu")
        except Exception as exc:
            if not products:raise RuntimeError(store+" : catalogue inaccessible : "+str(exc)) from exc
            print(store,"fin de pagination",page,type(exc).__name__)
            break
        products+=batch
        if len(batch)<250:break
    print(store,len(products),"fiches produits")
    return products

def candidate_codes(product,index):
    title=str(product.get("title") or "")
    handle=str(product.get("handle") or "")
    normalized=(title+" "+handle.replace("-"," ")).upper()
    return [code for code in set(CODE_RE.findall(normalized)) if code in index]

def msfs_product(product):
    title=str(product.get("title") or "")
    full=(" ".join([title,str(product.get("tags") or ""),str(product.get("product_type") or ""),str(product.get("body_html") or "")[:500]])).lower()
    if re.search(r"\b(x.plane|xplane|prepar3d|p3d|fsx)\b",title,re.I) and not re.search(r"msfs|microsoft flight simulator",title,re.I):return False
    if NOT_AIRPORT.search(title):return False
    # Les produits doivent être des scènes MSFS ; exclure les accessoires et les avions.
    return bool(re.search(r"\bmsfs\b|microsoft flight simulator|flightsim 2024|fs2024|fs2020",full,re.I))

def product_score(product,airport):
    title=str(product.get("title") or "")
    score=0
    if re.search(r"\b(?:airport|airfield|aerodrome|airstrip|regional|municipal|intl|international)\b",title,re.I):score+=15
    if re.search(r"\b2024\b|msfs.?24|fs24",title,re.I):score+=10
    if airport["scheduled"]:score+=7
    if airport["type"]=="large_airport":score+=7
    return score

def main():
    index=airports()
    owned={str(x.get("icao") or "").strip().upper() for x in json.loads((PUBLIC/"airports.json").read_text(encoding="utf-8"))}
    matches=defaultdict(list)
    errors=[]
    successful=0
    for store,base in STORES.items():
        try: products=shop_catalog(store,base)
        except Exception as exc:
            errors.append(str(exc))
            continue
        successful+=1
        for p in products:
            if not p.get("handle") or not msfs_product(p):continue
            for code in candidate_codes(p,index):
                if code in owned:continue
                apt=index[code]
                # Extra confirmation: product code is written explicitly in title or slug.
                url=base+"/products/"+urllib.parse.quote(str(p["handle"]),safe="-")
                if not url.startswith("https://"):continue
                price=None
                try:price=float(p["variants"][0].get("price",0))
                except (ValueError,TypeError,KeyError,IndexError):pass
                matches[code].append({"store":store,"url":url,"score":product_score(p,apt),
                                      "product_title":str(p.get("title") or "")[:140],
                                      "price_type":"Gratuit" if price==0 else "Payant" if price is not None else "Prix à vérifier"})
    if not successful:raise RuntimeError("Aucune boutique joignable : ancien fichier conservé. "+"; ".join(errors))
    groups={"airport":[],"aerodrome":[]}
    for code,products in matches.items():
        a=index[code]
        products.sort(key=lambda p:(-p["score"],p["store"]))
        # Seules les fiches présentant clairement un aéroport/terrain MSFS sont acceptées.
        products=[p for p in products if p["score"]>=15]
        if not products:continue
        kind="aerodrome" if a["type"]=="small_airport" else "airport"
        item={"icao":code,"name":a["name"],"type":kind,"lat":a["lat"],"lon":a["lon"],"country":a["country"],
              "shops":[{k:p[k] for k in ("store","url","price_type","product_title")} for p in products[:2]]}
        item["_rank"]=max(p["score"] for p in products)+(10 if a["scheduled"] else 0)
        groups[kind].append(item)
    for kind in groups:
        groups[kind].sort(key=lambda a:(-a["_rank"],a["icao"]))
    print("CANDIDATS", {k:len(v) for k,v in groups.items()},"déjà possédés",len(owned))
    if len(groups["airport"])<MIN_COUNT or len(groups["aerodrome"])<MIN_COUNT:
        raise RuntimeError("Moins de 50 propositions fiables par catégorie : conserver le catalogue précédent. "+
                           str({k:len(v) for k,v in groups.items()}))
    # Diversité régionale : les boutiques sont internationales ; garder 75 de chaque catégorie,
    # sans aucun code déjà possédé, et une sélection stable par tri.
    chosen=groups["airport"][:75]+groups["aerodrome"][:75]
    chosen.sort(key=lambda x:x["icao"])
    for item in chosen:item.pop("_rank",None)
    catalog=[{"icao":x["icao"],"name":x["name"],"type":x["type"],"shops":x["shops"]} for x in chosen]
    CATALOG.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    OUT.write_text(json.dumps(chosen,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PUBLIÉ",len(chosen),"dont",sum(x["type"]=="airport" for x in chosen),"aéroports et",
          sum(x["type"]=="aerodrome" for x in chosen),"aérodromes")
    if errors:print("Sources partiellement indisponibles",errors)

if __name__=="__main__":main()
