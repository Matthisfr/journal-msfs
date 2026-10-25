"""Contrôle quotidien de versions par fiche EXACTE de scène MSFS.
Une page produit n'est pas une version : seuls les champs explicites Version,
Product Version, Current version ou leurs équivalents sont acceptés.
Ne jamais déduire une version d'un numéro d'article, d'un avis, d'une date ou
du nom du dossier local. Les différences de canal/édition sont signalées.
"""
from __future__ import annotations
import concurrent.futures
import datetime as dt
import html
from html.parser import HTMLParser
import re
import urllib.error
import urllib.parse
import urllib.request

NOW = dt.datetime.now(dt.timezone.utc)
TODAY = NOW.date().isoformat()
# Maintenu pour compatibilité avec les autres scripts; les URL sont
# maintenant pilotées par le champ source_url de chaque scène.
PRODUCTS = {}
ALLOWED = {
    "www.aerosoft.com", "aerosoft.com", "contrail.shop", "inibuilds.com",
    "www.inibuilds.com", "secure.simmarket.com", "orbxdirect.com",
    "glideslope.pro", "www.glideslope.pro", "flightsim.to",
    "www.flightsim.to", "fsdg-online.com", "www.fsdg-online.com",
}
VERSION = r"([vV]?\d+(?:\.\d+){0,4})"
LABELS = [
    # Prefer explicit product metadata; not "version" in patch notes.
    rf"\bCurrent\s+version\s*:\s*{VERSION}\b",
    rf"\bVersion\s+actuelle\s*:\s*{VERSION}\b",
    rf"\bProduct\s+version\s*:?\s*{VERSION}\b",
    rf"\bVersion\s*:?\s*{VERSION}\b",
]

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.hidden=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","svg","noscript","nav","footer"):
            self.hidden.append(tag)
        elif not self.hidden and tag in ("p","div","span","li","h1","h2","h3","h4","td","th","dt","dd","br"):
            self.parts.append(" ")
    def handle_endtag(self,tag):
        if self.hidden and self.hidden[-1]==tag:
            self.hidden.pop()
        elif not self.hidden and tag in ("p","div","span","li","h1","h2","h3","h4","td","th","dt","dd","br"):
            self.parts.append(" ")
    def handle_data(self,data):
        if not self.hidden:
            self.parts.append(data)

def visible_text(raw):
    parser=VisibleText()
    parser.feed(raw)
    return re.sub(r"\s+"," ",html.unescape(" ".join(parser.parts))).strip()

def parse_version(raw, expected_name=None, store=None, edition=None):
    """Retourne la version affichée dans la fiche, pas une version inférée."""
    text=visible_text(raw)
    if expected_name and expected_name.lower() not in text.lower():
        return None
    if store=="orbxdirect.com":
        # Orbx Central a les versions; les pages OrbxDirect ne les publient pas.
        return None
    if store=="flightsim.to":
        match=re.search(r"\bVersion\s+([vV]?\d+(?:\.\d+){1,4})\b",text,re.I)
        return match.group(1).lstrip("vV") if match else None
    if store=="glideslope.pro":
        match=re.search(r"\bProduct\s+version\s*:?\s*([vV]?\d+(?:\.\d+){1,4})\b",text,re.I)
        return match.group(1).lstrip("vV") if match else None
    if store in ("inibuilds.com","www.inibuilds.com"):
        match=re.search(r"\bProduct\s+Version\s*:?\s*([vV]?\d+(?:\.\d+){1,4})\b",text,re.I)
        return match.group(1).lstrip("vV") if match else None
    if store in ("www.aerosoft.com","aerosoft.com"):
        # Deux éditions peuvent figurer dans le même champ (EDLW).
        m=re.search(r"\bCurrent\s+version\s*:\s*(.{0,105})",text,re.I)
        if not m: m=re.search(r"\bVersion\s+actuelle\s*:\s*(.{0,105})",text,re.I)
        if not m: return None
        line=m.group(1)
        pair=re.findall(r"(\d+(?:\.\d+){1,4})\s*\(\s*MSFS\s*(2020|2024)\s*\)",line,re.I)
        if len(pair)>1:
            if edition in ("2020","2024"):
                for version,sim in pair:
                    if sim==edition: return version
            return None  # édition installée non identifiée
        match=re.match(r"\s*[vV]?\s*(\d+(?:\.\d+){1,4})\b",line)
        return match.group(1) if match else None
    if store=="secure.simmarket.com":
        # Le champ version peut être absent (et l'app simInstaller est alors
        # la seule source fiable). N'utiliser que le premier bloc Details.
        main=text[:min(len(text),11000)]
        match=re.search(r"\b(?:Version|Version actuelle)\s*:?\s*([vV]?\d+(?:\.\d+){0,4})\b",main,re.I)
        return match.group(1).lstrip("vV") if match else None
    if store=="contrail.shop":
        match=re.search(r"\bVersion\s*:?\s*([vV]?\d+(?:\.\d+){1,4})\b",text,re.I)
        return match.group(1).lstrip("vV") if match else None
    if store=="fsdg-online.com":
        match=re.search(r"\bVersion\s*:\s*([vV]?\d+(?:\.\d+){1,4})\b",text,re.I)
        return match.group(1).lstrip("vV") if match else None
    return None

def version_parts(value):
    value=str(value or "").strip().lstrip("vV")
    if not re.fullmatch(r"\d+(?:\.\d+){1,4}",value): return None
    parts=value.split(".")
    # '1.01' and '1.0.1' may denote DIFFERENT vendor schemes.
    if any(len(x)>1 and x.startswith("0") for x in parts): return None
    return tuple(map(int,parts))

# Règles explicites, spécifiques à la scène et à l'éditeur. La conversion
# 1.31 -> 1.3.1 est autorisée seulement pour France VFR, dont les manifestes
# utilisent 1.3.1 alors que la boutique écrit 1.31.
PACKED_VENDOR_PREFIXES=("francevfr-",)
# Les versions 2025.08.05 de EuroScene ont été publiées sous la forme
# 25.8.5 dans les manifestes MSFS. Jamais appliquer à un autre éditeur.
DATE_SCENES={"euroscene-airport-lepa-palma-de-mallorca"}

def comparable_parts(installed,online,folder=""):
    left=str(installed or "").strip().lstrip("vV")
    right=str(online or "").strip().lstrip("vV")
    if folder in DATE_SCENES:
        if re.fullmatch(r"\d{2}\\.\d{1,2}\\.\d{1,2}",left):
            yy,mm,dd=map(int,left.split("."))
            left=f"{2000+yy}.{mm}.{dd}"
    # Formats 1.01, 1.03, 1.00 : interpréter comme 1.0.1/1.0.3/1.0.0
    # seulement lorsque le manifeste local possède exactement cette forme.
    if re.fullmatch(r"\d+\\.0\d{1,2}",right) and re.fullmatch(r"\d+\\.\d+\\.\d+",left):
        major,compressed=right.split(".")
        if len(compressed)==2:
            right=f"{major}.{int(compressed[0])}.{int(compressed[1])}"
        elif len(compressed)==3:
            right=f"{major}.{int(compressed[0])}.{int(compressed[1:])}"
    # France VFR : 1.31 signifie 1.3.1, 1.10 signifie 1.1.0.
    if folder.startswith(PACKED_VENDOR_PREFIXES) and re.fullmatch(r"\d+\\.\d{2}",right):
        major,compressed=right.split(".")
        right=f"{major}.{compressed[0]}.{compressed[1]}"
    a,b=version_parts(left),version_parts(right)
    if not a or not b:return None,None
    # 1.2 et 1.2.0 sont équivalents, tout comme 2.0 et 2.0.0.
    # Ne jamais convertir 1.01 en 1.1, ni comparer deux branches majeures.
    if len(a)!=len(b):
        if len(a)==3 and len(b)==2 and not right.split(".")[1].startswith("0"):
            b=b+(0,)
        elif len(a)==2 and len(b)==3 and not left.split(".")[1].startswith("0"):
            a=a+(0,)
        else:return None,None
    if a[0]!=b[0] and folder not in DATE_SCENES:return None,None
    return a,b

def compare_versions(installed,online,folder=""):
    a,b=comparable_parts(installed,online,folder)
    if a is None:return "incomparable"
    return "update" if b>a else "equal" if b==a else "source_older"

def is_newer(installed,online,folder=""):
    return compare_versions(installed,online,folder)=="update"

def fetch(url):
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (compatible; JournalMSFS/1.2)",
        "Accept-Language":"en-US,en;q=0.8,fr;q=0.5",
        "Accept":"text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"})
    with urllib.request.urlopen(req,timeout=15) as resp:
        if resp.status!=200: raise ValueError(f"HTTP {resp.status}")
        if not any(s in resp.headers.get("Content-Type","").lower() for s in ("html","text/")):
            raise ValueError("Réponse non HTML")
        return resp.read(1_900_000).decode("utf-8",errors="replace")

def check_page(url):
    try: return fetch(url),None
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code} — {'accès compte ou robot' if exc.code in (401,403,429) else 'page inaccessible'}"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {str(exc)[:95]}"

def update_versions(airports):
    unique={}
    for a in airports:
        url=str(a.get("source_url") or "")
        host=urllib.parse.urlparse(url).hostname or ""
        if url.startswith("https://") and host in ALLOWED and a.get("source_scope")!="parent_reference_only":
            unique[url]=None
    # Une requête par fiche, même quand plusieurs scènes y font référence.
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        fetched=dict(zip(unique,pool.map(check_page,unique)))
    counters={"verified_today":0,"eligible":len(unique),"unavailable":0,
              "no_version":0,"inconsistent":0,"not_automatable":0,
              "no_source":0,"source_older":0,"total_checked":len(airports)}
    errors=[]
    for a in airports:
        a["last_attempt_at"]=NOW.isoformat()
        a["last_audited_at"]=NOW.isoformat()
        url=str(a.get("source_url") or "")
        host=urllib.parse.urlparse(url).hostname or ""
        if a.get("icao")=="KLVB":
            state,reason="not_automatable","Piste fictive : hors contrôle des aéroports réels"
        elif a.get("source_scope")=="parent_reference_only":
            state,reason="not_automatable","Sous-scène : la version du produit parent n'est pas la version de ce module"
        elif not url:
            state,reason="no_source","Aucune fiche officielle du produit exact identifiée"
        elif host not in ALLOWED:
            state,reason="not_automatable","Boutique non prise en charge ou source non fiable"
        else:
            body,error=fetched.get(url,(None,"Fiche non consultée"))
            if error:
                state,reason="unavailable",error
            else:
                # Pour les fiches déjà associées au bon produit, contrôler
                # a minima que l'ICAO apparaît sur la page ou son URL.
                code=a.get("icao","")
                identity=(code in (url+" "+visible_text(body)[:16000]).upper()) if re.fullmatch(r"[A-Z0-9]{4}",code) else True
                # Les éditeurs omettent parfois l'ICAO de la fiche (EDDM
                # "Munich", EDDB "Berlin Brandenburg"). Le nom exact du
                # produit et l'éditeur sont alors recoupés séparément.
                title=visible_text(body)[:3500].lower()
                identity_alias={
                    "simwings-airport-eddm-munich":("munich","sim-wings"),
                    "aerosoft-airport-eddb-berlin-brandenburg":("berlin","brandenburg"),
                    "dfflyerdirect-city-rio-de-janeiro":("rio de janeiro","dfflyer"),
                }.get(a.get("folder"))
                if not identity and identity_alias:
                    identity=all(word in (title+" "+url.lower()) for word in identity_alias)
                if not identity:
                    state,reason="inconsistent","Code de scène absent de la fiche produit : association à revoir"
                else:
                    version=parse_version(body,store=host,edition=a.get("source_edition"))
                    if not version:
                        state,reason="no_version","Fiche accessible, mais aucun numéro de version public fiable ou édition ambiguë"
                    else:
                        a["server_version"]=version
                        a["version_checked_at"]=TODAY
                        a["version_source_url"]=url
                        comparison=compare_versions(a.get("installed"),version,a.get("folder",""))
                        a["version_comparison"]=comparison
                        if comparison=="incomparable":
                            state,reason="inconsistent",f"Numérotation / édition différente : installée {a.get('installed')}, boutique {version} ; comparaison interdite"
                        elif comparison=="source_older":
                            state,reason="source_older",f"Fiche {version} plus ancienne que l'installation {a.get('installed')} : vérifier le canal éditeur, ne pas rétrograder"
                        else:
                            state,reason="verified",("Version plus récente publiée sur la fiche exacte" if comparison=="update"
                                                      else "Version équivalente publiée sur la fiche exacte")
        a["version_check_state"]=state
        a["version_check_reason"]=reason
        a["status"]="verified" if state=="verified" else {
            "no_source":"UNK-P","unavailable":"UNK-S","no_version":"UNK-V",
            "not_automatable":"UNK-C","inconsistent":"UNK-C","source_older":"UNK-C"}.get(state,"UNK-V")
        if state=="verified": counters["verified_today"]+=1
        else:
            counters[state]+=1
            if state in ("unavailable","inconsistent","source_older"):
                errors.append(f"{a.get('icao','?')} / {a.get('publisher','?')} : {reason}")
    counters["with_source"]=sum(bool(a.get("source_url")) for a in airports)
    counters["missing_source"]=len(airports)-counters["with_source"]
    counters["updates_confirmed"]=sum(a.get("version_check_state")=="verified"
        and is_newer(a.get("installed"),a.get("server_version"),a.get("folder","")) for a in airports)
    return counters,errors
