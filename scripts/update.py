#!/usr/bin/env python3
"""Collecte gratuite : METAR/TAF récents NOAA et annonces MSFS officielles.
Aucune version de scène inventée, aucun appel à un modèle payant.
"""
from __future__ import annotations
import datetime as dt
import email.utils
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
UTC = dt.timezone.utc
NOW = dt.datetime.now(UTC)
USER_AGENT = 'LeJournalMSFS/1.0 (noncommercial aviation weather dashboard)'
API = 'https://aviationweather.gov/api/data/'
OFFICIAL_RSS = 'https://forums.flightsimulator.com/c/official/news-and-announcements/141.rss'
MAX_METAR_AGE = dt.timedelta(hours=3)

def iso(value):
    if not value: return None
    if isinstance(value, (int, float)): return dt.datetime.fromtimestamp(value, UTC)
    if isinstance(value, str):
        try:
            d = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
            return d if d.tzinfo else d.replace(tzinfo=UTC)
        except ValueError: return None
    return None

def get(url, timeout=25):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/json, application/rss+xml, application/xml;q=0.9, */*;q=0.8'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return b'' if r.status == 204 else r.read(3_000_000)

def chunks(items, n=45):
    for i in range(0,len(items),n): yield items[i:i+n]

def severity(m):
    """Score indicatif non utilisable pour une décision opérationnelle réelle."""
    raw = str(m.get('rawOb') or m.get('raw') or '').upper()
    wx = str(m.get('wxString') or '').upper()
    tokens = set(re.split(r'\s+', wx+' '+raw))
    def num(key):
        try: return float(m[key]) if m.get(key) is not None else None
        except (ValueError, TypeError): return None
    vis, gust, ceil = num('visib'), num('wgst'), num('ceil')
    ts = any(re.search(r'(?:\+|\-|VC)?TS(?:RA|GR|GS|SN)?',t) for t in tokens)
    sn = any(re.search(r'(?<![A-Z])(?:\+|\-)?SN(?:$|[A-Z])',t) for t in tokens)
    fg = any(re.search(r'^(?:\+|\-|VC)?(?:FG|FZFG)$',t) for t in tokens)
    ra = any(re.search(r'^(?:\+|\-|VC)?(?:RA|SHRA|DZ|FZRA)',t) for t in tokens)
    score, notes = 0, []
    if ts: score+=110; notes.append('orage')
    if sn: score+=75; notes.append('neige')
    if fg: score+=65; notes.append('brouillard')
    if vis is not None:
        if vis<1: score+=80; notes.append('visibilité < 1 SM')
        elif vis<3: score+=45; notes.append('visibilité < 3 SM')
        elif vis<5: score+=20; notes.append('visibilité < 5 SM')
    if ceil is not None:
        if ceil<500: score+=65; notes.append('plafond < 500 ft')
        elif ceil<1000: score+=45; notes.append('plafond < 1 000 ft')
        elif ceil<2000: score+=20; notes.append('plafond < 2 000 ft')
    if gust is not None:
        if gust>=35: score+=45; notes.append('rafales ≥ 35 kt')
        elif gust>=25: score+=22; notes.append('rafales ≥ 25 kt')
    if ra: score+=12; notes.append('précipitations')
    if ts: icon,phenomenon='⛈️','Orage'
    elif sn: icon,phenomenon='🌨️','Neige'
    elif fg: icon,phenomenon='🌫️','Brouillard'
    elif ra: icon,phenomenon='🌧️','Précipitations'
    elif gust is not None and gust>=25: icon,phenomenon='💨','Vent fort'
    elif re.search(r'\b(?:OVC|BKN)\d{3}',raw): icon,phenomenon='☁️','Ciel couvert'
    elif re.search(r'\b(?:SCT|FEW)\d{3}',raw): icon,phenomenon='🌤️','Éclaircies'
    elif re.search(r'\b(?:CLR|SKC|CAVOK|NSC)\b',raw): icon,phenomenon='☀️','Ciel dégagé'
    else: icon,phenomenon='☁️','Ciel non précisé'
    level='Très dégradé' if score>=110 else 'Dégradé' if score>=50 else 'À surveiller' if score>=20 else 'Faible contrainte'
    return score,', '.join(notes) if notes else phenomenon,icon,phenomenon,level

def collect_weather(airports):
    icaos=sorted({a['icao'] for a in airports if re.fullmatch('[A-Z]{4}',a.get('icao','')) and a['icao']!='KLVB'})
    names={}
    for a in airports: names.setdefault(a['icao'],a.get('name',''))
    rows,failures=[],[]
    for batch in chunks(icaos):
        url=API+'metar?'+urllib.parse.urlencode({'ids':','.join(batch),'format':'json','hours':'3'})
        try:
            blob=get(url)
            data=json.loads(blob) if blob else []
            if not isinstance(data,list): raise ValueError('Réponse METAR non-list')
            rows.extend(data)
        except (OSError,ValueError) as e: failures.append(str(e)[:140])
        time.sleep(.35)
    fresh={}
    for m in rows:
        code=str(m.get('icaoId') or m.get('station') or '').upper()
        if code not in icaos: continue
        observed=iso(m.get('obsTime') or m.get('reportTime') or m.get('observation_time'))
        if not observed or observed>NOW+dt.timedelta(minutes=10) or NOW-observed>MAX_METAR_AGE: continue
        if code in fresh and fresh[code][0]>=observed: continue
        fresh[code]=(observed,m)
    ranked=[]
    for code,(observed,m) in fresh.items():
        score,summary,icon,phenomenon,level=severity(m)
        ranked.append({'icao':code,'name':names.get(code,''),'observed_at':observed.isoformat(),
            'raw':str(m.get('rawOb') or m.get('raw') or ''),'score':score,
            'summary':summary,'icon':icon,'phenomenon':phenomenon,'level':level,
            'source_url':'https://aviationweather.gov/'})
    ranked.sort(key=lambda a:(-a['score'],a['icao']))
    top=ranked[:10]
    taf_status='no_data'
    if top:
        try:
            url=API+'taf?'+urllib.parse.urlencode({'ids':','.join(x['icao'] for x in top),'format':'json'})
            blob=get(url)
            tafs=json.loads(blob) if blob else []
            if not isinstance(tafs,list): raise ValueError('Réponse TAF non-list')
            by_id={str(t.get('icaoId') or '').upper():t for t in tafs}
            for x in top:
                t=by_id.get(x['icao'])
                if t: x['taf_raw']=str(t.get('rawTAF') or t.get('rawTaf') or '')
            taf_status='ok' if tafs else 'no_data'
        except (OSError,ValueError) as e: failures.append('TAF : '+str(e)[:130]);taf_status='error'
    if failures and not fresh: raise RuntimeError(' ; '.join(failures[:3]))
    return top,{'eligible':len(icaos),'received':len({str(m.get('icaoId') or '') for m in rows}),'fresh':len(fresh)},'partial' if failures else 'ok',taf_status,failures

def text_from_html(value):
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',value or ''))).strip()

def collect_news(previous):
    blob=get(OFFICIAL_RSS)
    if not blob: raise ValueError('Flux officiel vide')
    root=ET.fromstring(blob)
    known={a.get('url') for a in previous}
    results=[]
    for item in root.findall('.//item'):
        title=(item.findtext('title') or '').strip()
        link=(item.findtext('link') or '').strip()
        if not title or not link.startswith('https://forums.flightsimulator.com/'): continue
        if re.search(r'\b(?:msfs|flight simulator)\s*2020\b',title,re.I): continue
        try: published=email.utils.parsedate_to_datetime(item.findtext('pubDate') or '').astimezone(UTC)
        except (ValueError,TypeError): continue
        if NOW-published>dt.timedelta(days=21): continue
        desc=text_from_html(item.findtext('description') or '')
        if len(desc)>240: desc=desc[:237].rsplit(' ',1)[0]+'…'
        results.append({'id':link.rsplit('/',1)[-1],'title':title,'category':'MSFS officiel',
            'date':published.date().isoformat(),'source':'Forum officiel Microsoft Flight Simulator',
            'url':link,'summary':desc,
            'impact':'Consulter la publication officielle pour les détails et la compatibilité avec les add-ons.',
            'new':bool(link not in known and NOW-published<dt.timedelta(hours=36))})
    results.sort(key=lambda x:x['date'],reverse=True)
    return results[:10]

def run():
    status_path=PUBLIC/'status.json'
    status=json.loads(status_path.read_text(encoding='utf-8'))
    airports=json.loads((PUBLIC/'airports.json').read_text(encoding='utf-8'))
    status['last_run']=NOW.isoformat()
    status['edition']=NOW.date().isoformat()
    status['errors']=[]
    src=status.setdefault('source_status',{})
    try:
        top,coverage,metar_state,taf_state,errors=collect_weather(airports)
        status['weather']=top
        status['weather_coverage']=coverage
        status['weather_checked_at']=NOW.isoformat()
        src['metar']=metar_state
        src['taf']=taf_state
        status['errors'].extend(errors)
        print('METAR:',coverage,'top:',len(top))
    except Exception as e:
        src['metar']='error'
        src['taf']='error'
        status['errors'].append('METAR: '+str(e)[:250])
        print('METAR failure:',e,file=sys.stderr)
    try:
        news=collect_news(status.get('news',[]))
        if news: status['news']=news
        status['news_checked_at']=NOW.isoformat()
        src['official_news']='ok' if news else 'no_data'
        print('News:',len(news))
    except Exception as e:
        src['official_news']='error'
        status['errors'].append('Actualités: '+str(e)[:250])
        print('News failure:',e,file=sys.stderr)
    src['airport_versions']='non_verified'
    status['note']='METAR et annonces officielles automatisés ; vérification des versions de scènes et veille éditoriale ChatGPT non automatisées.'
    status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Updated',status_path)

if __name__=='__main__': run()
