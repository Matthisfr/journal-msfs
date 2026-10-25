"""Vérification prudente des versions publiques Aerosoft pour les scènes identifiées.
Les fiches de compte, variantes MSFS 2020/2024 ambiguës et les pages inaccessibles
ne sont jamais assimilées à une version vérifiée.
"""
from __future__ import annotations
import concurrent.futures
import datetime as dt
import html
from html.parser import HTMLParser
import re
import urllib.request

# Identifiants exacts de dossiers : évite de confondre plusieurs scènes du même ICAO.
PRODUCTS = {
 'aerosoft-airport-ebbr-brussels': ('Aerosoft Mega Airport Brussels', '1.0.5'),
 'aerosoft-airport-eddf-frankfurt': ('Aerosoft Mega Airport Frankfurt', '1.1.2'),
 'simwings-airport-eddh-hamburg': ('sim-wings Hamburg', '1.0.4'),
 'aerosoft-airport-eddk-cologne-bonn': ('Aerosoft Airport Cologne/Bonn', '1.1.1'),
 'aerosoft-airport-eddl-dusseldorf': ('Aerosoft Airport Dusseldorf', '1.0.3'),
 'simwings-airport-eddm-munich': ('sim-wings Munich V2', '2.5.1'),
 'aerosoft-airport-engm-oslo': ('Aerosoft Mega Airport Oslo-Gardermoen', '1.0.2'),
 'simwings-airport-panc-anchorage': ('sim-wings Anchorage', '1.1.0'),
}

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ('script','style') and self.hidden: self.hidden-=1
    def handle_data(self,data):
        if not self.hidden: self.parts.append(data)

def parse_version(raw, expected_name):
    parser=VisibleText()
    parser.feed(raw)
    visible=re.sub(r'\s+',' ',html.unescape(' '.join(parser.parts)))
    # Vérifie l'identité du produit : un autre produit de même aéroport n'est pas valable.
    if expected_name.lower() not in visible.lower():
        return None
    match=re.search(r'\bCurrent\s+version\s*:\s*[vV]?\s*(\d+(?:\.\d+){1,4})\b',visible,re.I)
    return match.group(1) if match else None

def get_product_version(a):
    url=a['source_url']
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; JournalMSFS/1.0)','Accept-Language':'en-US,en;q=0.8'})
    with urllib.request.urlopen(req,timeout=18) as resp:
        if resp.status!=200: raise ValueError('Réponse non 200')
        data=resp.read(1_500_000).decode('utf-8',errors='replace')
    product=PRODUCTS[a['folder']][0]
    version=parse_version(data,product)
    if not version: raise ValueError('Version ou identité du produit non confirmée')
    return version

def update_versions(airports):
    candidates=[a for a in airports if a.get('folder') in PRODUCTS and a.get('source_url','').startswith('https://www.aerosoft.com/')]
    successes=0
    errors=[]
    def check(a):
        try: return a,get_product_version(a),None
        except Exception as e: return a,None,str(e)[:100]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for a,version,error in pool.map(check,candidates):
            a['last_attempt_at']=dt.datetime.now(dt.timezone.utc).isoformat()
            if version:
                a['server_version']=version
                a['version_checked_at']=dt.datetime.now(dt.timezone.utc).date().isoformat()
                a['version_check_state']='verified'
                a.pop('version_check_reason',None)
                a['status']='verified'
                successes+=1
            else:
                a['version_check_state']='unavailable'
                a['version_check_reason']=error or 'Version non confirmée'
                a['status']='UNK-S'
                errors.append(a.get('icao','?')+': '+(error or 'non vérifié'))
    return {'eligible':len(candidates),'verified_today':successes,'unavailable':len(errors)},errors
