#!/usr/bin/env python3
"""Collecte météo de l'après-midi : METAR/TAF uniquement, sans scanner les scènes."""
import json
from pathlib import Path
from update import collect_weather, PUBLIC

airports=json.loads((PUBLIC/'airports.json').read_text(encoding='utf-8'))
previous=PUBLIC/'weather_all.json'
original=previous.read_bytes() if previous.exists() else None
try:
    top,coverage,metar_state,taf_state,errors=collect_weather(airports)
    current=json.loads(previous.read_text(encoding='utf-8'))
    if not current.get('stations') or metar_state=='error':
        raise RuntimeError('Collecte météo vide ou en erreur : conservation des données précédentes')
    print('METAR actualisés:',coverage,'statut:',metar_state,'TAF:',taf_state,'erreurs:',errors)
except Exception:
    if original is not None:
        previous.write_bytes(original)
    else:
        previous.unlink(missing_ok=True)
    raise
