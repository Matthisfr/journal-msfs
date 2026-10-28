"""Generate verified airport coordinates from OurAirports for the journal map."""
import csv, io, json, pathlib, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
PUBLIC=ROOT/"public"
OUT=PUBLIC/"airport_coordinates.json"
URL="https://raw.githubusercontent.com/datasets/airport-codes/main/data/airport-codes.csv"
def main():
    airports=json.loads((PUBLIC/"airports.json").read_text(encoding="utf-8"))
    codes={a.get("icao","").upper() for a in airports}
    codes={c for c in codes if len(c)==4 and c.isalnum() and not c.startswith("(") and c not in {"KLVB","OMDU"}}
    existing=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    result=dict(existing)
    all_airports={}
    try:
        req=urllib.request.Request(URL,headers={"User-Agent":"MSFS-Journal-Map/1.0"})
        with urllib.request.urlopen(req,timeout=25) as response:
            reader=csv.DictReader(io.TextIOWrapper(response,encoding="utf-8"))
            for row in reader:
                candidates=[str(row.get(key) or "").strip().upper() for key in ("gps_code","ident")]
                code=next((value for value in candidates if value in codes),None)
                icao=str(row.get("gps_code") or row.get("ident") or "").strip().upper()
                world_coord=(row.get("coordinates") or "").split(",")
                if len(icao)==4 and icao.isalpha() and len(world_coord)==2:
                    try:
                        la,lo=map(float,world_coord)
                        if -90<=la<=90 and -180<=lo<=180:
                            all_airports[icao]=[round(la,5),round(lo,5),str(row.get("name") or "")[:90]]
                    except ValueError: pass
                if code is None: continue
                coord=(row.get("coordinates") or "").split(",")
                if len(coord)!=2: continue
                try: lat,lon=map(float,coord)
                except ValueError: continue
                if -90<=lat<=90 and -180<=lon<=180:
                    result[code]={"lat":lat,"lon":lon,"name":row.get("name",""),"source":"OurAirports / airport-codes"}
    except Exception as exc:
        raise RuntimeError(f"Source de coordonnées indisponible : {exc}") from exc
    result={k:v for k,v in result.items() if k in codes}
    missing=sorted(codes-set(result))
    if missing: raise RuntimeError(f"Coordonnées manquantes pour les aéroports vérifiables : {missing}")
    reference={"KDEN":(39.86,-104.67),"KLAX":(33.94,-118.41),"CYVR":(49.19,-123.18),"PANC":(61.17,-150.00),"CYUL":(45.47,-73.74),"BGSF":(67.01,-50.72),"LFPG":(49.01,2.55),"KJFK":(40.64,-73.78)}
    missing_major=[code for code in ("KDEN","KLAX","CYVR","PANC","KSEA","KSFO") if code in codes and code not in result]
    if missing_major: raise ValueError(f"Aéroports majeurs absents des coordonnées : {missing_major}")
    for code,(lat,lon) in reference.items():
        if code in result and (abs(result[code]["lat"]-lat)>0.5 or abs(result[code]["lon"]-lon)>0.5):
            raise ValueError(f"Coordonnées suspectes pour {code}: {result[code]}")
    for code,loc in result.items():
        if not (-90 <= loc["lat"] <= 90 and -180 <= loc["lon"] <= 180):
            raise ValueError(f"Coordonnées invalides : {code}")
    # Classification indicative pour la seule silhouette des repères.
    # OurAirports: identifiants aéroport et caractéristiques des pistes.
    # Ne constitue PAS une validation opérationnelle des performances A320.
    try:
        def remote_rows(filename):
            url="https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/" + filename
            request=urllib.request.Request(url,headers={"User-Agent":"MSFS-Journal-Map/1.0"})
            with urllib.request.urlopen(request,timeout=35) as response:
                return list(csv.DictReader(io.TextIOWrapper(response,encoding="utf-8-sig")))

        airport_ids={}
        for row in remote_rows("airports.csv"):
            keys={str(row.get(field) or "").strip().upper() for field in ("ident","gps_code","icao_code")}
            for code in keys.intersection(result):
                airport_ids.setdefault(str(row.get("id") or ""),set()).add(code)
        best={}
        found=set()
        for row in remote_rows("runways.csv"):
            codes=airport_ids.get(str(row.get("airport_ref") or ""),())
            if not codes or str(row.get("closed") or "0").strip()=="1":
                continue
            try:
                length=float(row.get("length_ft") or 0)*0.3048
                width=float(row.get("width_ft") or 0)*0.3048
            except ValueError:
                continue
            surface=str(row.get("surface") or "").upper()
            paved=any(t in surface for t in ("ASP","CON","PEM","BIT","TAR","PAV"))
            for code in codes:
                found.add(code)
                if length>=1800 and width>=30 and paved:
                    best[code]=True
        # Aéroports commerciaux à pistes courtes : ne pas les confondre avec des aérodromes légers.
        commercial_airports={"LGMK","LGSR","EKVG","LESO","VQPR"}
        for code in result:
            if code in found:
                result[code]["aircraft_marker"]="airliner" if best.get(code) or code in commercial_airports else "cessna"
            else:
                result[code]["aircraft_marker"]="unknown"
        for code in commercial_airports.intersection(result):
            result[code]["aircraft_marker"]="airliner"
        print(f"Silhouettes : {sum(v.get('aircraft_marker')=='airliner' for v in result.values())} A320 indicatifs, {sum(v.get('aircraft_marker')=='cessna' for v in result.values())} avions légers")
    except Exception as exc:
        # Ne pas bloquer la publication ni inventer de catégories en cas de panne.
        print(f"Classification pistes indisponible : {exc}; données précédentes conservées")
        for code in result:
            result[code]["aircraft_marker"]=existing.get(code,{}).get("aircraft_marker","unknown")
    if all_airports:
        (PUBLIC/"world_airports.json").write_text(json.dumps(all_airports,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
        print(f"Index mondial : {len(all_airports)} aéroports ICAO")
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Carte : {len(result)}/{len(codes)} codes géolocalisés, aucun point inventé")
if __name__=="__main__": main()
