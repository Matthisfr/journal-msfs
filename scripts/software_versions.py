"""Catalogue logiciel MSFS : versions vérifiées, changements et notes officielles.
Jamais de version inférée à partir d'un changement de page ou d'une annonce vague.
Les produits sans API publique restent explicitement NON PUBLIÉ / À VÉRIFIER.
"""
from __future__ import annotations
import datetime as dt
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/"public"
NOW=dt.datetime.now(dt.timezone.utc)
TODAY=NOW.date().isoformat()

class Text(HTMLParser):
    def __init__(self):
        super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript","svg"):self.skip+=1
        if not self.skip and tag in ("p","div","br","li","h1","h2","h3","h4"):self.parts.append("\n")
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript","svg"):self.skip=max(0,self.skip-1)
        if not self.skip and tag in ("p","div","li","h1","h2","h3","h4"):self.parts.append("\n")
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
def text_html(raw):
    p=Text();p.feed(raw);return html.unescape("".join(p.parts))
def get(url,accept="text/html"):
    req=urllib.request.Request(url,headers={"User-Agent":"JournalMSFS/1.4 (public version monitor)","Accept":accept})
    with urllib.request.urlopen(req,timeout=18) as r:
        if r.status!=200:raise ValueError("HTTP "+str(r.status))
        return r.read(1200000).decode("utf-8","replace")
def github_version(repo):
    data=json.loads(get("https://api.github.com/repos/"+repo+"/releases?per_page=12","application/vnd.github+json"))
    if not isinstance(data,list):raise ValueError("Réponse GitHub invalide")
    stable=next((x for x in data if not x.get("draft") and not x.get("prerelease") and x.get("tag_name")),None)
    preview=next((x for x in data if not x.get("draft") and x.get("prerelease") and x.get("tag_name")),None)
    if not stable and not preview:raise ValueError("Aucune release officielle")
    def release(x):
        return {"version":str(x["tag_name"]).lstrip("vV"),"url":x["html_url"],
            "published_at":x.get("published_at"),"notes":str(x.get("body") or "")[:12000]}
    return release(stable) if stable else None,release(preview) if preview else None
def simapppro_version():
    url="https://winwingsim.com/mobileview/simapppro.html"
    raw=text_html(get(url))
    # Only a version with a numbered change list counts. The site contains
    # many old changelogs; use the highest first explicitly documented entry.
    matches=list(re.finditer(r"(?<!\d)(1\.\d+\.\d+)\s*:",raw))
    if not matches:raise ValueError("Changelog SimAppPro absent")
    m=matches[0]
    notes=raw[m.end():matches[1].start() if len(matches)>1 else m.end()+6000].strip()
    if not re.search(r"\b\d+\s*[\.\)]",notes):raise ValueError("Version sans notes")
    return {"version":m.group(1),"url":url,"published_at":None,"notes":notes[:12000]}
def msfs_official():
    url="https://www.flightsimulator.com/category/releases/"
    raw=get(url)
    # Only official MSFS 2024 release-notes headlines, never beta builds.
    m=re.search(r"Release Notes[^<]{0,140}Sim Update\s*(\d+(?:\.\d+)?)\s*\[\s*(\d+\.\d+\.\d+\.\d+)\s*\][^<]{0,30}Now Available",text_html(raw),re.I)
    if not m:raise ValueError("Aucune release MSFS 2024 explicite dans la page officielle")
    link=re.search(r'href=["\'](https://www\.flightsimulator\.com/[^"\']+)["\'][^>]*>[^<]*Release Notes[^<]{0,140}Sim Update\s*'+re.escape(m.group(1)),raw,re.I)
    page=link.group(1) if link else url
    return {"version":m.group(2),"url":page,"published_at":None,
            "notes":"MSFS 2024 Sim Update "+m.group(1)+" : "+m.group(2)+". Notes officielles et corrections sur la page liée."}
def fenix_official():
    url="https://fenixsim.com/status/"
    raw=text_html(get(url))
    m=re.search(r"major\s+V(\d+)\s+update",raw,re.I)
    if not m:
        raw=text_html(get("https://fenixsim.com/blog/"))
        m=re.search(r"Fenix\s+A32X\s+Version\s+(\d+)\s+Released",raw,re.I)
    if not m:
        # La page d'accueil peut ne plus présenter la sortie du 21 octobre.
        # Vérifier alors la page de publication officielle, jamais un forum.
        raw=text_html(get("https://fenixsim.com/blog/entries/2026-10-21_v3_update/"))
        m=re.search(r"Fenix\s+A32X\s+Version\s+(\d+)\s+Released",raw,re.I)
    if not m:raise ValueError("Branche Fenix non explicitement publiée sur le blog")
    # Version majeure, PAS numéro exact de build de l'installateur Fenix.
    return {"version":"V"+m.group(1)+" (branche)","url":"https://fenixsim.com/blog/entries/2026-10-21_v3_update/" if m.group(1)=="3" else url,
            "published_at":None,"notes":"Version majeure confirmée. Numéro exact du launcher non public : consulter le journal des modifications Fenix."}

def siminnovations_version():
    url="https://docs.siminnovations.com/air_manager_5/release_notes/"
    raw=text_html(get(url))
    m=re.search(r"\bV(5\.\d+(?:\.\d+)?)\b",raw,re.I)
    if not m:raise ValueError("Version Air Manager 5 introuvable")
    return {"version":m.group(1),"url":url,"published_at":None,
            "notes":"Version publiée dans les notes officielles Air Manager 5."}

def short_notes(text):
    lines=[re.sub(r"\s+"," ",line).strip(" -*#\t") for line in str(text).splitlines()]
    lines=[x for x in lines if x and not x.startswith("![")]
    return " · ".join(lines[:6])[:900]
def update():
    catalog=json.loads((PUBLIC/"software_catalog.json").read_text())
    previous_path=PUBLIC/"software_versions.json"
    previous=json.loads(previous_path.read_text()) if previous_path.exists() else {}
    old={x["id"]:x for x in previous.get("items",[])}
    rows=[];news=[];errors=[]
    for entry in catalog:
        row={k:v for k,v in entry.items() if k!="repo"}
        row.update({"version":None,"preview_version":None,"state":"not_public","checked_at":NOW.isoformat(),
                    "reason":"Aucun numéro de version exploitable sur un flux public structuré. Site officiel suivi chaque jour."})
        try:
            stable=preview=None
            if entry["method"]=="github_release":
                stable,preview=github_version(entry["repo"])
            elif entry["method"]=="simapppro":
                stable=simapppro_version()
            elif entry["method"]=="msfs_official":
                stable=msfs_official()
            elif entry["method"]=="fenix_official":
                stable=fenix_official()
            elif entry["method"]=="siminnovations":
                stable=siminnovations_version()
            if stable:
                row.update({"version":stable["version"],"state":"verified","version_url":stable["url"],
                            "published_at":stable["published_at"],"reason":"Version vérifiée sur le changelog officiel"})
            if preview:
                row["preview_version"]=preview["version"]
                row["preview_url"]=preview["url"]
            prior=old.get(entry["id"],{})
            # Compare only the same channel and two explicit versions. The
            # initial run establishes a baseline, not 23 false NEWS badges.
            for channel,current in (("stable",stable),("preview",preview)):
                if not current:continue
                key="version" if channel=="stable" else "preview_version"
                previous_version=prior.get(key)
                if previous_version and previous_version!=current["version"]:
                    row["state"]="changed" if channel=="stable" else row["state"]
                    row["changed_at"]=NOW.isoformat()
                    row["previous_version"]=previous_version
                    news.append({
                        "id":f"software-{entry['id']}-{channel}-{current['version']}",
                        "title":f"{entry['name']} : nouvelle {('version' if channel=='stable' else 'préversion')} {current['version']}",
                        "category":"LOGICIELS / VERSIONS","topic":entry["name"],
                        "date":TODAY,"source":"Notes officielles — "+entry["name"],
                        "url":current["url"],"new":True,
                        "summary":f"Version précédente {previous_version} → {current['version']}. "+short_notes(current["notes"]),
                        "impact":"Consulter le changelog officiel complet et vérifier la compatibilité Fenix / MSFS 2024 avant installation.",
                        "details":"\n".join(line.strip() for line in str(current["notes"]).splitlines() if line.strip())[:3800],
                        "changelog_url":current["url"],
                        "version_before":previous_version,"version_after":current["version"]
                    })
            if prior.get("changed_at") and not row.get("changed_at"):
                row["last_change_at"]=prior.get("changed_at") or prior.get("last_change_at")
            if not prior.get("version") and stable:
                row["baseline_at"]=TODAY
            elif prior.get("baseline_at"):
                row["baseline_at"]=prior["baseline_at"]
        except Exception as e:
            row["state"]="unavailable"
            row["reason"]=f"Source inaccessible : {type(e).__name__} {str(e)[:130]}"
            errors.append(entry["id"]+": "+row["reason"])
            prior=old.get(entry["id"],{})
            if prior.get("version"):
                row["version"]=prior["version"]
                row["version_url"]=prior.get("version_url",row["source_url"])
                row["last_confirmed_at"]=prior.get("last_confirmed_at") or prior.get("checked_at")
                row["reason"]="Source inaccessible aujourd'hui ; dernière version confirmée conservée à titre historique, non revérifiée."
        # Ne pas masquer les versions déjà documentées quand le flux officiel
        # n'est pas exploitable aujourd'hui : les afficher comme références datées.
        if not row.get("version"):
            prior=old.get(entry["id"],{})
            reference=entry.get("reference_version") or prior.get("reference_version")
            if reference:
                row["reference_version"]=reference
                row["reference_checked_at"]=entry.get("reference_checked_at") or prior.get("reference_checked_at")
                row["reference_source_url"]=entry.get("reference_source_url") or prior.get("reference_source_url") or entry.get("source_url")
                row["reference_note"]=entry.get("reference_note") or prior.get("reference_note") or "Dernière référence connue, non revérifiée aujourd'hui."
            elif prior.get("version"):
                row["version"]=prior["version"]
                row["version_url"]=prior.get("version_url") or entry.get("source_url")
                row["last_confirmed_at"]=prior.get("checked_at")
                row["reason"]="Dernière version confirmée conservée ; nouvelle vérification nécessaire."
                row["state"]="historical"
        # Afficher une version de référence sourcée plutôt qu'une cellule vide.
        # Ne jamais présenter une référence historique comme une vérification du jour.
        if not row.get("version") and entry.get("reference_version"):
            row["version"]=entry["reference_version"]
            row["version_url"]=entry.get("reference_source_url") or entry["source_url"]
            row["last_confirmed_at"]=entry.get("reference_checked_at")
            row["reason"]="Référence vérifiée antérieurement (non revérifiée aujourd'hui) : "+entry.get("reference_note","")
            row["state"]="historical"
        if not row.get("version") and old.get(entry["id"],{}).get("version"):
            prior=old[entry["id"]]
            row["version"]=prior["version"]
            row["version_url"]=prior.get("version_url") or row["source_url"]
            row["last_confirmed_at"]=prior.get("checked_at")
            row["reason"]="Dernière version précédemment enregistrée, non revérifiée aujourd'hui."
            row["state"]="historical"
        rows.append(row)
    data={"checked_at":NOW.isoformat(),"total":len(rows),
          "verified":sum(x["state"] in ("verified","changed") for x in rows),
          "changed":sum(x["state"]=="changed" for x in rows),
          "items":rows,"errors":errors}
    previous_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    print("Versions logiciels:",data["verified"],"/",len(rows),"changements:",len(news),"erreurs:",len(errors))
    return data,news,errors
if __name__=="__main__":update()
