"""Vérification automatique des versions publiées sur les dépôts officiels.
Ne confond pas préversion et version stable, et ne déduit pas une version de
la modification d'une page web.
"""
from __future__ import annotations
import datetime as dt
import html
import json
import re
import urllib.request

UTC = dt.timezone.utc
NOW = dt.datetime.now(UTC)
REPOS = [
    ("MobiFlight/MobiFlight-Connector", "MOBIFLIGHT", "MobiFlight", "MF"),
    ("FSLiveTrafficLiveries/base", "Trafic IA", "FSLTL Base Models (avions et livrées)", "FSLTL"),
]

def release_items(previous=None):
    known = {x.get("url") for x in (previous or [])}
    found, errors = [], []
    for repo, category, product, topic in REPOS:
        url = f"https://api.github.com/repos/{repo}/releases?per_page=6"
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "JournalMSFS/1.1",
                "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                releases = json.loads(resp.read(1_000_000))
            if not isinstance(releases, list):
                raise ValueError("Format des versions inattendu")
            stable, preview = False, False
            for x in releases:
                if x.get("draft"): continue
                is_preview = bool(x.get("prerelease"))
                if (is_preview and preview) or (not is_preview and stable): continue
                date_str = x.get("published_at")
                if not date_str: continue
                date = dt.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if date > NOW + dt.timedelta(minutes=5) or NOW - date > dt.timedelta(days=60): continue
                link = x.get("html_url", "")
                if not link.startswith(f"https://github.com/{repo}/releases/"): continue
                tag = str(x.get("tag_name") or "").strip()
                if not tag: continue
                body = re.sub(r"<[^>]*>", " ", x.get("body") or "")
                body = re.sub(r"!\[[^]]*]\([^)]*\)|\[[^]]*]\([^)]*\)", " ", body)
                body = re.sub(r"[\r\n#*]+", " ", body)
                body = re.sub(r"\s+", " ", html.unescape(body)).strip()
                summary = (body[:237].rsplit(" ", 1)[0] + "…") if len(body) > 240 else body
                channel = "préversion" if is_preview else "version stable"
                found.append({
                    "id": f"github-{repo.replace('/', '-')}-{tag}",
                    "title": f"{product} : {channel} {tag}",
                    "category": category,
                    "topic": topic,
                    "date": date.date().isoformat(),
                    "source": f"GitHub Releases officiel — {repo}",
                    "url": link,
                    "summary": summary or f"Publication officielle {tag}.",
                    "impact": ("Préversion : ne pas installer sur le cockpit principal sans sauvegarde et vérification de compatibilité."
                               if is_preview else "Vérifier le changelog officiel et sauvegarder les configurations avant installation."),
                    "new": link not in known and NOW-date < dt.timedelta(hours=48),
                })
                if is_preview: preview = True
                else: stable = True
        except Exception as exc:
            errors.append(f"{repo} : {type(exc).__name__}: {str(exc)[:110]}")
    return found, errors
