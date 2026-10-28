"""Public news extraction: RSS/Atom, JSON-LD and HTML article links.
Fail closed when no dated articles are discoverable. No authenticated access.
"""
from __future__ import annotations
import datetime as dt
import email.utils
import html
from html.parser import HTMLParser
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen

BLOG="https://www.sayintentions.ai/blog"
HOSTS={"www.sayintentions.ai","sayintentions.ai"}
AGE_DAYS=45

def clean(s):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]*>"," ",str(s or "")))).strip()

def valid_link(u):
    p=urlparse(u)
    return p.scheme=="https" and p.hostname in HOSTS and p.path.startswith("/blog/") and len(p.path)>6

class Discover(HTMLParser):
    def __init__(self):
        super().__init__();self.feeds=[];self.articles=[];self.scripts=[];self.in_json=False;self.buffer=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="link" and a.get("rel","").lower()=="alternate" and any(t in a.get("type","") for t in ("rss","atom")):
            self.feeds.append(urljoin(BLOG,a.get("href","")))
        if tag=="a" and a.get("href"):
            u=urljoin(BLOG,a["href"])
            if valid_link(u):self.articles.append(u)
        if tag=="script" and a.get("type","").lower()=="application/ld+json":
            self.in_json=True;self.buffer=[]
    def handle_data(self,data):
        if self.in_json:self.buffer.append(data)
    def handle_endtag(self,tag):
        if tag=="script" and self.in_json:
            self.scripts.append("".join(self.buffer));self.in_json=False

def fetch(url):
    if urlparse(url).hostname not in HOSTS:raise ValueError("host not allowed")
    with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 JournalMSFS/2.0","Accept":"text/html,application/rss+xml,application/atom+xml"}),timeout=12) as response:
        return response.read(1200000).decode("utf-8","replace")

def parse_date(value):
    if not value:return None
    try:return dt.datetime.fromisoformat(str(value).replace("Z","+00:00")).astimezone(dt.timezone.utc)
    except ValueError:
        try:return email.utils.parsedate_to_datetime(value).astimezone(dt.timezone.utc)
        except (ValueError,TypeError):return None

def ld_articles(obj):
    if isinstance(obj,list):
        for v in obj:yield from ld_articles(v)
    elif isinstance(obj,dict):
        if str(obj.get("@type","")).lower() in ("blogposting","article","newsarticle"):
            yield {"title":obj.get("headline") or obj.get("name"),"url":obj.get("url") or obj.get("mainEntityOfPage"),
                   "published":obj.get("datePublished"),"summary":obj.get("description") or obj.get("abstract")}
        for key in ("@graph","itemListElement","mainEntity"):
            if key in obj:yield from ld_articles(obj[key])

def parse_feed(xml):
    root=ET.fromstring(xml)
    result=[]
    for n in root.findall("./channel/item"):
        result.append({"title":n.findtext("title"),"url":n.findtext("link"),
                       "published":n.findtext("pubDate"),"summary":n.findtext("description")})
    ns="{http://www.w3.org/2005/Atom}"
    for n in root.findall(ns+"entry"):
        link=next((x.get("href") for x in n.findall(ns+"link") if x.get("rel","alternate")=="alternate"),None)
        result.append({"title":n.findtext(ns+"title"),"url":link,
                       "published":n.findtext(ns+"published") or n.findtext(ns+"updated"),
                       "summary":n.findtext(ns+"summary") or n.findtext(ns+"content")})
    return result

def parse_html_articles(page):
    parser=Discover();parser.feed(page)
    result=[]
    for raw in parser.scripts:
        try:result.extend(ld_articles(json.loads(raw)))
        except (ValueError,TypeError):pass
    return result,parser

def normalize(records,previous,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    known={x.get("url") for x in previous}
    found={}
    for item in records:
        u=item.get("url")
        if isinstance(u,dict):u=u.get("@id")
        if not isinstance(u,str):continue
        u=urljoin(BLOG,u).split("#",1)[0]
        if not valid_link(u):continue
        date=parse_date(item.get("published"))
        if not date or date>now+dt.timedelta(minutes=5) or now-date>dt.timedelta(days=AGE_DAYS):continue
        title=clean(item.get("title"))
        if len(title)<6:continue
        summary=clean(item.get("summary"))[:320] or title
        found[u]={"id":"si-"+re.sub(r"[^a-z0-9]+","-",urlparse(u).path.lower()).strip("-"),
            "title":title,"category":"SayIntentions","topic":"SayIntentions",
            "date":date.date().isoformat(),"source":"SayIntentions — blog officiel",
            "url":u,"summary":summary,
            "impact":"Vérifier les nouveautés pour MSFS 2024, le Fenix et le cockpit.",
            "new":u not in known and now-date<=dt.timedelta(hours=48)}
    return sorted(found.values(),key=lambda x:x["date"],reverse=True)[:20]

def collect_sayintentions(previous):
    try:page=fetch(BLOG)
    except Exception:return [],"unavailable"
    structured,parser=parse_html_articles(page)
    feeds=list(dict.fromkeys(parser.feeds+[
        "https://www.sayintentions.ai/blog/rss.xml",
        "https://www.sayintentions.ai/blog/feed",
        "https://www.sayintentions.ai/rss.xml",
        "https://www.sayintentions.ai/feed.xml"
    ]))
    for u in feeds:
        try:structured.extend(parse_feed(fetch(u)))
        except (OSError,ValueError,ET.ParseError):pass
    # HTML article pages can expose structured publication metadata even when the listing is JS-rendered.
    for u in list(dict.fromkeys(parser.articles))[:25]:
        try:
            records,_=parse_html_articles(fetch(u))
            structured.extend(records)
        except (OSError,ValueError):pass
    result=normalize(structured,previous)
    return result,("ok" if result else "no_dated_articles")
