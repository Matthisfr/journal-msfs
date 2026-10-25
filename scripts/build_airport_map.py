"""Generate verified airport coordinates from OurAirports for the journal map."""
import csv, io, json, pathlib, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
PUBLIC=ROOT/"public"
OUT=PUBLIC/"airport_coordinates.json"
URL="https://raw.githubusercontent.com/datasets/airport-codes/master/data/airport-codes.csv"
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
                code=(row.get("gps_code") or "").upper()
                if code not in codes: continue
                coord=(row.get("coordinates") or "").split(",")
                if len(coord)!=2: continue
                try: lon,lat=map(float,coord)
                except ValueError: continue
                if -90<=lat<=90 and -180<=lon<=180:
                    result[code]={"lat":lat,"lon":lon,"name":row.get("name",""),"source":"OurAirports / airport-codes"}
    except Exception as exc:
        print(f"Source de coordonnées indisponible, cache conservé : {exc}")
    result={k:v for k,v in result.items() if k in codes}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Carte : {len(result)}/{len(codes)} codes géolocalisés, aucun point inventé")
if __name__=="__main__": main()
