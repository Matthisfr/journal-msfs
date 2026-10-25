"""Capture the most recent public SimBrief OFP for the journal. Never invent flight details."""
import datetime as dt
import json
import pathlib
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "simbrief_last.json"
URL = "https://www.simbrief.com/api/xml.fetcher.php?" + urllib.parse.urlencode({"username": "Matthis", "json": "v2"})


def run():
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "JournalMSFS/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=18) as response:
            data = json.load(response)
        origin, destination = data.get("origin") or {}, data.get("destination") or {}
        if not origin.get("icao_code") or not destination.get("icao_code"):
            raise ValueError("SimBrief has no published flight for this username")
        general, aircraft, times = data.get("general") or {}, data.get("aircraft") or {}, data.get("times") or {}
        record = {
            "state": "ok", "username": "Matthis", "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "origin": {"icao": origin.get("icao_code"), "name": origin.get("name")},
            "destination": {"icao": destination.get("icao_code"), "name": destination.get("name")},
            "flight_number": general.get("flight_number") or general.get("callsign"),
            "aircraft": aircraft.get("icaocode") or aircraft.get("name"),
            "route": general.get("route"), "altitude": general.get("initial_altitude"),
            "enroute_time": times.get("est_time_enroute"),
            "generated_at": (data.get("params") or {}).get("time_generated"),
        }
        OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("SimBrief OFP captured:", record["origin"]["icao"], record["destination"]["icao"])
    except Exception as exc:
        print("SimBrief unavailable:", type(exc).__name__, str(exc)[:180])
        if not OUT.exists():
            OUT.write_text(json.dumps({"state": "unavailable", "username": "Matthis"}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()
