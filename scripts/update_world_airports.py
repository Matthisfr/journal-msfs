"""Met à jour uniquement l'index mondial ICAO, à la demande."""
import csv
import io
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "world_airports.json"
URL = "https://raw.githubusercontent.com/datasets/airport-codes/main/data/airport-codes.csv"

def main():
    request = urllib.request.Request(URL, headers={"User-Agent": "MSFS-Journal-Map/1.0"})
    airports = {}
    with urllib.request.urlopen(request, timeout=60) as response:
        for row in csv.DictReader(io.TextIOWrapper(response, encoding="utf-8")):
            code = str(row.get("gps_code") or row.get("ident") or "").strip().upper()
            coordinates = (row.get("coordinates") or "").split(",")
            if len(code) != 4 or not code.isalpha() or len(coordinates) != 2:
                continue
            try:
                lat, lon = map(float, coordinates)
            except ValueError:
                continue
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                airports[code] = [round(lat, 5), round(lon, 5), str(row.get("name") or "")[:90]]
    if len(airports) < 15000:
        raise RuntimeError(f"Index incomplet : seulement {len(airports)} aéroports ; fichier précédent conservé.")
    for code in ("LFPG", "LFMN", "SBGL", "SBRJ", "KJFK"):
        if code not in airports:
            raise RuntimeError(f"Code de référence absent : {code}")
    OUT.write_text(json.dumps(airports, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Index mondial validé : {len(airports)} aéroports, écrit dans {OUT}")

if __name__ == "__main__":
    main()
