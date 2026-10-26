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
    "www.flightsim.to", "fr.flightsim.to", "fsdg-online.com", "www.fsdg-online.com",
    "beautifulmodelworld.com", "www.beautifulmodelworld.com",
    "forum.inibuilds.com",
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

def parse_version(raw, expected_name=None, store=None, edition=None, icao=None):
    """Retourne la version affichée dans la fiche, pas une version inférée."""
    text=visible_text(raw)
    if expected_name and expected_name.lower() not in text.lower():
        return None
    if store in ("beautifulmodelworld.com","www.beautifulmodelworld.com"):
        # Le catalogue liste chaque ICAO suivi de sa propre version.
        # Ne jamais prendre la version d'une autre scène du catalogue.
        if not icao or not re.fullmatch(r"[A-Z0-9]{4}",str(icao).upper()):
            return None
        code=re.escape(str(icao).upper())
        pattern=rf"\[\s*{code}\s*\].{{0,110}}?\bVersion\s*:?\s*[vV]?(\d+(?:\.\d+){{1,4}})\b"
        matches=re.findall(pattern,text,re.I)
        return matches[0] if len(set(matches))==1 and matches else None
    if store=="forum.inibuilds.com":
        # Bulletin officiel de mise à jour : le titre annonce explicitement
        # l'ICAO et la version du produit, contrairement aux posts utilisateurs.
        if not icao: return None
        match=re.search(r"iniBuilds\s+.{0,95}?\(\s*"+re.escape(str(icao))+r"\s*\)\s+for\s+MSFS(?:\s+2024)?\s+v(\d+(?:\.\d+){1,4})\s+Released",text,re.I)
        return match.group(1) if match else None
    if store=="orbxdirect.com":
        # Orbx Central a les versions; les pages OrbxDirect ne les publient pas.
        return None
    if store in ("flightsim.to","www.flightsim.to","fr.flightsim.to"):
        match=re.search(r"\bVersion\s+([vV]?\d+(?:\.\d+){1,4})\b",text,re.I)
        return match.group(1).lstrip("vV") if match else None
    if store=="glideslope.pro":
        match=re.search(r"\bProduct\s+version\s*:?\s*([vV]?\d+(?:\.\d+){1,4})\b",text,re.I)
        return match.group(1).lstrip("vV") if match else None
    if store in ("inibuilds.com","www.inibuilds.com"):
        match=re.search(r"\b(?:Product\s+Version|Current\s+Version)\s*:?\s*([vV]?\d+(?:\.\d+){1,4})\b",text,re.I)
        return match.group(1).lstrip("vV") if match else None
    if store in ("www.aerosoft.com","aerosoft.com"):
        # Deux éditions peuvent figurer dans le même champ (EDLW).
        m=re.search(r"\bCurrent\s+version\s*:\s*(.{0,105})",text,re.I)
        if not m: m=re.search(r"\bVersion\s+actuelle\s*:\s*(.{0,105})",text,re.I)
        if not m: return None
        line=m.group(1)
        pair=re.findall(r"(\d+(?:\.\d+){1,4})\s*\(\s*MSFS\s*(2020|2024)\s*\)",line,re.I)
        if len(pair)>1:
            edition_label=str(edition or "").strip().upper()
            target="2024" if edition_label in ("2024","MSFS 2024") else "2020" if edition_label in ("2020","MSFS 2020") else None
            if target:
                for version,sim in pair:
                    if sim==target: return version
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
        match=re.search(r"\b(?:Product\s+Version|Current\s+Version|Version)\s*:?\s*([vV]?\d+(?:\.\d+){1,4})\b",text,re.I)
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
        if re.fullmatch(r"\d{2}\.\d{1,2}\.\d{1,2}",left):
            yy,mm,dd=map(int,left.split("."))
            left=f"{2000+yy}.{mm}.{dd}"
        if re.fullmatch(r"20\d{2}\.\d{1,2}\.\d{1,2}",right):
            yyyy,mm,dd=map(int,right.split("."))
            if 1<=mm<=12 and 1<=dd<=31:
                right=f"{yyyy}.{mm}.{dd}"
    # Mex High Flight MUHA : la boutique affiche seulement "2" pour la
    # branche 2.0.0. Autoriser ce cas exact, pas tous les numéros d'articles.
    if folder=="mexhighflight-airport-muha-jose-marti" and right=="2" and left=="2.0.0":
        right="2.0.0"
    # Formats 1.01, 1.03, 1.00 : interpréter comme 1.0.1/1.0.3/1.0.0
    # seulement lorsque le manifeste local possède exactement cette forme.
    if re.fullmatch(r"\d+\.0\d{1,2}",right) and re.fullmatch(r"\d+\.\d+\.\d+",left):
        major,compressed=right.split(".")
        if len(compressed)==2:
            right=f"{major}.{int(compressed[0])}.{int(compressed[1])}"
        elif len(compressed)==3:
            right=f"{major}.{int(compressed[0])}.{int(compressed[1:])}"
    # France VFR : 1.31 signifie 1.3.1, 1.10 signifie 1.1.0.
    if folder.startswith(PACKED_VENDOR_PREFIXES) and re.fullmatch(r"\d+\.\d{2}",right):
        major,compressed=right.split(".")
        right=f"{major}.{compressed[0]}.{compressed[1]}"
    a,b=version_parts(left),version_parts(right)
    if not a or not b:return None,None
    # 1.2 et 1.2.0 sont équivalents, tout comme 2.0 et 2.0.0.
    # Ne jamais convertir 1.01 en 1.1, ni comparer deux branches majeures.
    if len(a)!=len(b):
        if len(a)==3 and len(b)==2 and len(right.split(".")[1])==1:
            b=b+(0,)
        elif len(a)==2 and len(b)==3 and len(left.split(".")[1])==1:
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
    """Une seconde tentative seulement pour les erreurs réseau temporaires.

    Les refus d'accès et les pages sans version restent UNKNOWN : jamais de
    version déduite d'une ancienne réponse ou d'un numéro de catalogue.
    """
    import time
    for attempt in range(2):
        try:
            return fetch(url), None
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(1.5)
                continue
            label = "accès compte ou robot" if exc.code in (401, 403, 429) else "page inaccessible"
            return None, f"HTTP {exc.code} — {label}"
        except (TimeoutError, urllib.error.URLError, ConnectionError) as exc:
            if attempt == 0:
                time.sleep(1.5)
                continue
            return None, f"Réseau indisponible après 2 essais : {type(exc).__name__}: {str(exc)[:75]}"
        except Exception as exc:
            return None, f"{type(exc).__name__}: {str(exc)[:95]}"


def find_official_bulletins(raw, icao):
    """Découvre des annonces iniBuilds liées depuis une fiche, sans liste d'aéroports.

    L'ICAO doit être présent dans le titre ou l'URL, et le lien doit appartenir
    au forum officiel. Un simple lien de discussion ne suffit pas.
    """
    if not re.fullmatch(r"[A-Z0-9]{4}",str(icao or "").upper()): return []
    from html.parser import HTMLParser
    class Links(HTMLParser):
        def __init__(self):
            super().__init__();self.links=[];self.href=None;self.words=[]
        def handle_starttag(self,tag,attrs):
            if tag=="a": self.href=dict(attrs).get("href");self.words=[]
        def handle_data(self,data):
            if self.href is not None:self.words.append(data)
        def handle_endtag(self,tag):
            if tag=="a" and self.href is not None:
                self.links.append((self.href," ".join(self.words)))
                self.href=None;self.words=[]
    parser=Links();parser.feed(raw)
    found=[]
    for href,title in parser.links:
        url=urllib.parse.urljoin("https://inibuilds.com/",href)
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme!="https" or parsed.hostname!="forum.inibuilds.com":continue
        if not parsed.path.startswith("/topic/"):continue
        if str(icao).upper() not in (title+" "+parsed.path).upper():continue
        if not re.search(r"released|update|version|v\\d",title+" "+parsed.path,re.I):continue
        found.append(url.split("?")[0].split("#")[0])
    return list(dict.fromkeys(found))[:5]

def update_versions(airports):
    # Référence produit officielle EDDB : l'annonce de blog ne contient pas
    # nécessairement le champ « Current version » de la fiche commerciale.
    for airport in airports:
        if airport.get("folder")=="aerosoft-airport-eddb-berlin-brandenburg":
            airport["source_url"]="https://www.aerosoft.com/en/shop/flight/microsoft-flight-simulator/msfs-2020/msfs-sceneries/msfs-europe/3252/aerosoft-mega-airport-berlin-brandenburg-v3"
            airport["source_edition"]="MSFS 2024"
            airport["source_store"]="Aerosoft"
    for airport in airports:
        if airport.get("folder")=="bmw-airport-lipz-venice-marco-polo":
            airport["source_url"]="https://beautifulmodelworld.com/"
            airport["source_store"]="Beautiful Model of the World"
    unique={}
    for a in airports:
        url=str(a.get("source_url") or "")
        host=urllib.parse.urlparse(url).hostname or ""
        if url.startswith("https://") and host in ALLOWED and a.get("source_scope")!="parent_reference_only":
            unique[url]=None
    # Une requête par fiche, même quand plusieurs scènes y font référence.
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        fetched=dict(zip(unique,pool.map(check_page,unique)))
    # Découverte générique : chercher les annonces officielles liées par la
    # boutique, puis comparer uniquement les versions explicitement annoncées.
    bulletin_urls={}
    for a in airports:
        url=a.get("source_url") or ""
        host=urllib.parse.urlparse(url).hostname
        if host not in ("inibuilds.com","www.inibuilds.com"):continue
        body,error=fetched.get(url,(None,None))
        if not body or error:continue
        for bulletin in find_official_bulletins(body,a.get("icao")):
            bulletin_urls.setdefault(bulletin,[]).append(a)
    if bulletin_urls:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            bulletin_pages=dict(zip(bulletin_urls,pool.map(check_page,bulletin_urls)))
    else: bulletin_pages={}
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
            state,reason="no_source",("Catalogue / source de référence disponible, mais aucune version produit actuelle publiée" if a.get("source_catalog_url") else "Aucune fiche officielle du produit exact identifiée")
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
                    "inibuilds-airport-kdtw-detroit":("detroit","kdtw"),
                    "inibuilds-airport-lowi-innsbruck":("innsbruck","lowi"),
                    "simwings-airport-eddm-munich":("munich","sim-wings"),
                    "aerosoft-airport-eddb-berlin-brandenburg":("berlin","brandenburg"),
                    "dfflyerdirect-city-rio-de-janeiro":("rio de janeiro","dfflyer"),
                }.get(a.get("folder"))
                if not identity and identity_alias:
                    identity=all(word in (title+" "+url.lower()) for word in identity_alias)
                if not identity:
                    state,reason="inconsistent","Code de scène absent de la fiche produit : association à revoir"
                else:
                    version=parse_version(body,store=host,edition=a.get("source_edition"),icao=code)
                    # Une annonce liée à la fiche peut corriger une version
                    # boutique obsolète, jamais une version d'un autre produit.
                    candidates=[]
                    for bulletin,linked in bulletin_urls.items():
                        if a not in linked:continue
                        bulletin_body,bulletin_error=bulletin_pages[bulletin]
                        if bulletin_error or not bulletin_body:continue
                        candidate=parse_version(bulletin_body,store="forum.inibuilds.com",icao=code)
                        if candidate and compare_versions(a.get("installed"),candidate,a.get("folder",""))!="incomparable":
                            candidates.append((candidate,bulletin))
                    if candidates:
                        candidates.sort(key=lambda item:version_parts(item[0]) or (),reverse=True)
                        candidate,bulletin=candidates[0]
                        if not version or compare_versions(version,candidate,a.get("folder",""))=="update":
                            version=candidate
                            a["version_source_url"]=bulletin
                    if not version:
                        state,reason="no_version",("Version visible uniquement dans Orbx Central (connexion au compte requise)" if host=="orbxdirect.com" else "Fiche accessible, mais aucun numéro de version public fiable ou édition ambiguë")
                    else:
                        a["server_version"]=version
                        a["version_checked_at"]=TODAY
                        a["version_source_url"]=a.get("version_source_url") or url
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
