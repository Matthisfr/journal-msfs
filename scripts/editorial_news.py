"""Reusable public article ingestion for editorial sources (FSElite, etc.)."""
from __future__ import annotations
import datetime as dt
import html
from html.parser import HTMLParser
import json
import re
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen

SOURCES=[
    {"id":"gsx_fselite_news","url":"https://fselite.net/developer/fsdreamteam/","host":"fselite.net","category":"GSX Pro","topic":"GSX","source":"FSElite — FSDreamTeam","keywords":("gsx","ground services","fsdreamteam")},
    {"id":"aig_fselite_news","url":"https://fselite.net/developer/alpha-india-group/","host":"fselite.net","category":"Trafic AI","topic":"AIG","source":"FSElite — Alpha India Group","keywords":("aig","alpha india group","alphaindiagroup","ai manager","traffic controller","traffic models","ai traffic","liveries")},
]

class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.jsonld=[];self._ld=False;self._buf=[];self.headings=[];self._h3=False;self._heading=[];self._heading_url=None;self._after_heading=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="a" and a.get("href"):
            self.links.append(a["href"])
            if self._h3:self._heading_url=a["href"]
        if tag=="h3":self._h3=True;self._heading=[];self._heading_url=None
        if tag=="script" and a.get("type","").lower()=="application/ld+json":
            self._ld=True;self._buf=[]
    def handle_data(self,data):
        if self._ld:self._buf.append(data)
        if self._h3:self._heading.append(data)
        elif self._after_heading is not None and data.strip():
            self.headings[self._after_heading]["nearby"]+=" "+data.strip()
            if len(self.headings[self._after_heading]["nearby"])>350:self._after_heading=None
    def handle_endtag(self,tag):
        if tag=="h3" and self._h3:
            self._h3=False
            if self._heading_url:
                self.headings.append({"url":self._heading_url,"title":" ".join(self._heading).strip(),"nearby":""})
                self._after_heading=len(self.headings)-1
        if tag=="script" and self._ld:
            try:self.jsonld.append(json.loads("".join(self._buf)))
            except (ValueError,TypeError):pass
            self._ld=False

def articles(obj):
    if isinstance(obj,list):
        for x in obj:yield from articles(x)
    elif isinstance(obj,dict):
        kind=obj.get("@type",[])
        if isinstance(kind,str):kind=[kind]
        if any(t in ("Article","NewsArticle","BlogPosting") for t in kind):yield obj
        for k in ("@graph","itemListElement","item"):
            if k in obj:yield from articles(obj[k])

def fetch(url,host):
    p=urlparse(url)
    if p.scheme!="https" or p.hostname not in (host,"www."+host):raise ValueError("untrusted host")
    with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (JournalMSFS news collector)"}),timeout=12) as r:
        return r.read(1200000).decode("utf-8","replace")

def date_of(value):
    if not value:return None
    try:return dt.datetime.fromisoformat(str(value).replace("Z","+00:00")).astimezone(dt.timezone.utc)
    except (ValueError,TypeError):return None

def clean(s):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]*>"," ",str(s or "")))).strip()

def normalize_article(a,source,now):
    u=a.get("url") or a.get("mainEntityOfPage")
    if isinstance(u,dict):u=u.get("@id") or u.get("url")
    if not isinstance(u,str):return None
    u=urljoin(source["url"],u).split("#")[0].split("?")[0]
    p=urlparse(u)
    if p.scheme!="https" or p.hostname not in (source["host"],"www."+source["host"]):return None
    if p.path.startswith(("/developer/","/category/","/tag/","/page/")) or p.path=="/":return None
    title=clean(a.get("headline") or a.get("name"))
    date=date_of(a.get("datePublished"))
    if not title or not date or date>now+dt.timedelta(minutes=5) or now-date>dt.timedelta(days=60):return None
    combined=(title+" "+clean(a.get("description"))).lower()
    if not any(k in combined for k in source["keywords"]):return None
    summary=clean(a.get("description"))[:320] or title
    return {"id":source["id"]+"-"+re.sub("[^a-z0-9]+","-",p.path.lower()).strip("-"),
            "title":title,"category":source["category"],"topic":source["topic"],
            "date":date.date().isoformat(),"source":source["source"],"url":u,
            "summary":summary,"impact":"Vérifier l'annonce auprès de FSDreamTeam avant de conclure à une nouvelle version.",
            "new":now-date<dt.timedelta(hours=48)}

def collect_source(source,previous,fetcher=fetch,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    try:landing=fetcher(source["url"],source["host"])
    except Exception:return [],"unavailable"
    page=Page();page.feed(landing)
    candidates={}
    for o in page.jsonld:
        for a in articles(o):
            if a.get("url"):candidates[str(a["url"])]=a
    # FSElite publie titre et date directement dans les cartes de sa page éditeur.
    # Cette voie fonctionne même si les pages d'article n'exposent aucun JSON-LD.
    for heading in page.headings:
        m=re.search(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(20\d{2})\b",heading["nearby"],re.I)
        if not m:continue
        published=date_of(f"{m.group(3)}-{dict(Jan='01',Feb='02',Mar='03',Apr='04',May='05',Jun='06',Jul='07',Aug='08',Sep='09',Oct='10',Nov='11',Dec='12')[m.group(2).title()]}-{int(m.group(1)):02d}T12:00:00Z")
        if published:
            u=urljoin(source["url"],heading["url"])
            candidates[u]={"url":u,"headline":heading["title"],"datePublished":published.isoformat(),"description":heading["nearby"]}
    urls=[]
    for link in page.links:
        u=urljoin(source["url"],link).split("#")[0].split("?")[0]
        p=urlparse(u)
        if p.scheme=="https" and p.hostname in (source["host"],"www."+source["host"]) and re.search(r"/20\d\d/",p.path):
            urls.append(u)
    for u in list(dict.fromkeys(urls))[:20]:
        try:
            article_page=Page();article_page.feed(fetcher(u,source["host"]))
            for o in article_page.jsonld:
                for a in articles(o):
                    candidates[str(a.get("url") or u)]=dict(a,url=a.get("url") or u)
        except Exception:continue
    records={}
    for a in candidates.values():
        item=normalize_article(a,source,now)
        if item:records[item["url"]]=item
    known={x.get("url") for x in previous}
    for item in records.values():
        if item["url"] in known:item["new"]=False
    return sorted(records.values(),key=lambda x:x["date"],reverse=True)[:20],("ok" if records else "no_dated_articles")

def collect_editorial_news(previous):
    items=[];statuses={}
    for source in SOURCES:
        found,status=collect_source(source,previous)
        items.extend(found);statuses[source["id"]]=status
    return items,statuses
