"""SayIntentions: public RSS/Atom discovery, strict publication-date validation.
Never treat an SPA shell or a changed hash as a published article.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import email.utils
import re
import xml.etree.ElementTree as ET

BLOG="https://www.sayintentions.ai/blog"
class Feeds(HTMLParser):
    def __init__(self):
        super().__init__(); self.urls=[]
    def handle_starttag(self,tag,attrs):
        if tag!="link":return
        a=dict(attrs)
        if a.get("rel","").lower()=="alternate" and ("rss" in a.get("type","") or "atom" in a.get("type","")):
            self.urls.append(urljoin(BLOG,a.get("href","")))
def fetch(url):
    if urlparse(url).hostname not in ("www.sayintentions.ai","sayintentions.ai"):raise ValueError("Unexpected feed host")
    with urlopen(Request(url,headers={"User-Agent":"JournalMSFS/1.6","Accept":"text/html,application/rss+xml,application/atom+xml"}),timeout=14) as r:
        return r.read(1500000).decode("utf-8","replace")
def collect_sayintentions(previous):
    try: page=fetch(BLOG)
    except Exception:return [],"unavailable"
    feeds=Feeds();feeds.feed(page)
    candidates=list(dict.fromkeys(feeds.urls+[
        "https://www.sayintentions.ai/blog/rss.xml",
        "https://www.sayintentions.ai/blog/feed",
        "https://www.sayintentions.ai/rss.xml"
    ]))
    known={x.get("url") for x in previous}
    now=datetime.now(timezone.utc)
    found={}
    for url in candidates:
        try:
            root=ET.fromstring(fetch(url))
            nodes=root.findall("./channel/item")
            atom=False
            if not nodes:
                nodes=root.findall("{http://www.w3.org/2005/Atom}entry")
                atom=True
            for node in nodes:
                if atom:
                    ns="{http://www.w3.org/2005/Atom}"
                    title=node.findtext(ns+"title") or ""
                    link=next((x.attrib.get("href","") for x in node.findall(ns+"link") if x.attrib.get("rel","alternate")=="alternate"),"")
                    published=node.findtext(ns+"published") or node.findtext(ns+"updated") or ""
                    date=datetime.fromisoformat(published.replace("Z","+00:00")).astimezone(timezone.utc)
                    summary=node.findtext(ns+"summary") or ""
                else:
                    title=node.findtext("title") or ""
                    link=node.findtext("link") or ""
                    published=node.findtext("pubDate") or ""
                    date=email.utils.parsedate_to_datetime(published).astimezone(timezone.utc)
                    summary=node.findtext("description") or ""
                if not title.strip() or not link.startswith(BLOG+"?p="):continue
                if date>now+timedelta(minutes=5) or now-date>timedelta(days=45):continue
                summary=re.sub(r"<[^>]+>"," ",summary)
                summary=re.sub(r"\\s+"," ",summary).strip()[:320]
                found[link]={"id":"sayintentions-"+re.sub(r"[^a-z0-9]+","-",link.split("?p=",1)[-1].lower()),
                    "title":title.strip(),"category":"SayIntentions","topic":"SayIntentions",
                    "date":date.date().isoformat(),"source":"SayIntentions — blog officiel",
                    "url":link,"summary":summary or title.strip(),
                    "impact":"Consulter les nouveautés et vérifier les effets sur MSFS 2024 et le Fenix.",
                    "new":link not in known and now-date<timedelta(hours=48)}
        except Exception:continue
    return sorted(found.values(),key=lambda x:x["date"],reverse=True)[:20],("ok" if found else "no_public_feed")
