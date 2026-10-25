"""Generate verified airport coordinates from OurAirports for the journal map."""
import csv, io, json, pathlib, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
PUBLIC=ROOT/"public"
OUT=PUBLIC/"airport_coordinates.json"
URL="https://raw.githubusercontent.com/datasets/airport-codes/main/data/airport-codes.csv"
def main():
    airports=json.loads((PUBLIC/"airports.json").read_text(encoding="utf-8"))
    codes={a.get("icao","").upper() for a in airports}
    codes={c for c in codes if len(c)==4 and c.isalnum() and not c.startswith("(") and c!="KLVB"}
    existing=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    result=dict(existing)
    try:
        req=urllib.request.Request(URL,headers={"User-Agent":"MSFS-Journal-Map/1.0"})
        with urllib.request.urlopen(req,timeout=25) as response:
            reader=csv.DictReader(io.TextIOWrapper(response,encoding="utf-8"))
            for row in reader:
                candidates=[str(row.get(key) or "").strip().upper() for key in ("gps_code","ident")]
                code=next((value for value in candidates if value in codes),None)
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
    if len(result) < 120: raise RuntimeError(f"Seulement {len(result)} coordonnées : publication interrompue")
    reference={"KDEN":(39.86,-104.67),"KLAX":(33.94,-118.41),"CYVR":(49.19,-123.18),"PANC":(61.17,-150.00),"CYUL":(45.47,-73.74),"BGSF":(67.01,-50.72),"LFPG":(49.01,2.55),"KJFK":(40.64,-73.78)}
    missing_major=[code for code in ("KDEN","KLAX","CYVR","PANC","KSEA","KSFO") if code in codes and code not in result]
    if missing_major: raise ValueError(f"Aéroports majeurs absents des coordonnées : {missing_major}")
    for code,(lat,lon) in reference.items():
        if code in result and (abs(result[code]["lat"]-lat)>0.5 or abs(result[code]["lon"]-lon)>0.5):
            raise ValueError(f"Coordonnées suspectes pour {code}: {result[code]}")
    for code,loc in result.items():
        if not (-90 <= loc["lat"] <= 90 and -180 <= loc["lon"] <= 180):
            raise ValueError(f"Coordonnées invalides : {code}")
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Carte : {len(result)}/{len(codes)} codes géolocalisés, aucun point inventé")
if __name__=="__main__": main()
