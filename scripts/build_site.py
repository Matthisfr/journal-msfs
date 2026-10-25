"""Build a fully populated, no-JavaScript airport table and a standalone fallback page.
Run AFTER the daily collector and BEFORE uploading the GitHub Pages artifact.
Only the published artifact is modified; the source index.html stays a template.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
MAP_ID = "1smgM-lIXr_QPyWKxPrS68bmU0FsMjYM"

def h(value):
    return html.escape(str(value if value is not None else ""), quote=True)

def compare(installed, online):
    a = [int(x) for x in re.findall(r"\d+", str(installed or ""))]
    b = [int(x) for x in re.findall(r"\d+", str(online or ""))]
    if not a or not b:
        return "À COMPARER", "flag-v"
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        if y > x:
            return "MISE À JOUR", "flag-s"
        if y < x:
            return "INSTALLÉE + RÉCENTE", "flag-v"
    return "À JOUR", "flag-ok"

def render_rows(airports):
    out = []
    cls = {"UNK-P": "p", "UNK-V": "v", "UNK-C": "c", "UNK-S": "s"}
    for a in airports:
        original = a.get("original") or ""
        icao = a.get("icao") or ""
        code = f'<span class="code">{h(icao)}</span>'
        if original != icao:
            code += f'<small>Source : {h(original)}</small>'
        name = f'<b>{h(a.get("name") or "")}</b><small>{h(a.get("note") or a.get("folder") or "")}</small>'
        installed = h(a.get("installed") or "Non renseignée")
        url = str(a.get("source_url") or "")
        source = f'<small><a href="{h(url)}" target="_blank" rel="noopener noreferrer">Fiche éditeur ↗</a></small>' if url.startswith("https://") else ""
        online = a.get("server_version")
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        verified_today = (a.get("version_check_state") == "verified"
                          and a.get("version_checked_at") == today)
        if online and verified_today:
            label, flag = compare(a.get("installed"), online)
            status = f'<b>{h(online)}</b><small><span class="flag {flag}">{h(label)}</span></small>{source}'
            status += f'<small>Vérifiée le {h(a["version_checked_at"])}</small>'
        elif online:
            state = str(a.get("status") or "UNK-V")
            if state == "verified":
                state = "UNK-V"
            status = (f'<b>{h(online)}</b><small>Dernière version connue, non revalidée aujourd’hui</small>'
                      f'<small><span class="flag flag-{cls.get(state, "v")}">{h(state)}</span></small>{source}')
            if a.get("version_checked_at"):
                status += f'<small>Dernière confirmation : {h(a["version_checked_at"])}</small>'
        else:
            state = str(a.get("status") or "UNK-V")
            status = f'<span class="flag flag-{cls.get(state, "v")}">{h(state)}</span>{source}'
        out.append(
            f'<tr><td>{code}</td><td>{name}</td><td>{h(a.get("publisher") or "")}</td>'
            f'<td><b>{installed}</b></td><td>{status}</td></tr>'
        )
    return "\n".join(out)

def news_topic(a):
    s = " ".join(str(a.get(k) or "") for k in ("topic", "category", "title")).lower()
    if "sayintention" in s:
        return "SI", "si"
    if "mobiflight" in s:
        return "MF", "mf"
    if "fenix" in s:
        return "FX", "fenix"
    if "winctrl" in s or "winwing" in s:
        return "WC", "winctrl"
    if "gsx" in s:
        return "GSX", "gsx"
    if "navigraph" in s:
        return "NAV", "navigraph"
    if "fshud" in s:
        return "ATC", "fshud"
    if "fsltl" in s or "aig" in s:
        return "AI", "traffic"
    if "santiluib3" in s or "s3" in s:
        return "S3", "s3"
    if "atc" in s:
        return "ATC", "atc"
    if "metar" in s or "stratawx" in s:
        return "WX", "weather"
    if "msfs" in s or "flight simulator" in s:
        return "FS", "msfs"
    return "✈", "generic"

def brand_icon(kind, manifest):
    entry = manifest.get(kind, {})
    path = entry.get("path") or f"icons/{kind}.svg"
    fallback = f"icons/{kind}.svg"
    if not (PUBLIC / path).is_file():
        path = fallback
    branded = " brand-original" if kind in manifest and path == entry.get("path") else ""
    return (
        f'<span class="topic-icon topic-{kind}{branded}" aria-hidden="true">'
        f'<img src="{h(path)}" width="42" height="42" alt="" decoding="async"'
        f' onerror="this.onerror=null;this.src=&#39;{h(fallback)}&#39;">'
        '</span>'
    )

def static_brand_icons(index, manifest):
    pattern = r'<span class="topic-icon topic-([a-z0-9-]+)"([^>]*)><img src="icons/[a-z0-9-]+\.svg"[^>]*></span>'
    def replace(match):
        kind, attrs = match.groups()
        img = brand_icon(kind, manifest)
        # Preserve aria-label and aria-hidden from the source template.
        return re.sub(r' aria-hidden="true"', attrs if attrs.strip() else ' aria-hidden="true"', img, count=1)
    return re.sub(pattern, replace, index)

def build_news(status, editorial, manifest):
    editorial_news = editorial.get("news") or []
    superseded = {url for a in editorial_news for url in a.get("supersedes", [])}
    seen = set()
    news = []
    for a in editorial_news + [x for x in status.get("news", []) if x.get("url") not in superseded]:
        url = str(a.get("url") or "")
        if url in seen or not url.startswith("https://"):
            continue
        seen.add(url)
        news.append(a)
    news.sort(key=lambda a: str(a.get("date") or ""), reverse=True)
    cards = []
    homes = []
    for a in news:
        label, kind = news_topic(a)
        icon = brand_icon(kind, manifest)
        title = h(a.get("title") or "")
        date = h(a.get("date") or "")
        category = h(a.get("category") or "ACTUALITÉS")
        url = h(a["url"])
        source = h(a.get("source") or "Source officielle")
        cards.append(
            '<article class="news-card"><div class="news-meta">' + category + ' · ' + date +
            ('<span class="new-tag">NEWS</span>' if a.get("new") else "") +
            '</div><div class="news-heading">' + icon + '<h3>' + title + '</h3></div>' +
            ('<p>' + h(a["summary"]) + '</p>' if a.get("summary") else "") +
            ('<div class="news-impact"><b>Impact / action :</b> ' + h(a["impact"]) + '</div>' if a.get("impact") else "") +
            '<div class="news-source"><a href="' + url + '" target="_blank" rel="noopener noreferrer">' + source + ' ↗</a></div></article>'
        )
        homes.append(
            '<article><div class="home-news-row">' + icon + '<div class="home-news-content"><small>' +
            category + ' · ' + date + '</small><strong>' + title +
            '</strong><a href="' + url + '" target="_blank" rel="noopener noreferrer">Source officielle ↗</a></div></div></article>'
        )
    return "\n".join(cards), "\n".join(homes[:3])

def render_watch(watch):
    rows = watch.get("sources", [])
    totals = watch.get("totals", {})
    checked = h(watch.get("checked_at", "Non exécutée"))
    count = len(rows)
    ok = totals.get("ok", 0) + totals.get("changed", 0)
    changed = totals.get("changed", 0)
    restricted = totals.get("restricted", 0)
    unavailable = totals.get("unavailable", 0)
    changes = watch.get("changes", [])
    recent = []
    for x in reversed(changes):
        try:
            at = dt.datetime.fromisoformat(x["detected_at"].replace("Z", "+00:00"))
            if dt.datetime.now(dt.timezone.utc) - at > dt.timedelta(days=14):
                continue
        except (KeyError, ValueError):
            continue
        recent.append(x)
        if len(recent) >= 6: break
    highlights = "".join(
        f'<li><a href="{h(x["url"])}" target="_blank" rel="noopener noreferrer">{h(x["name"])}</a>'
        f' — changement détecté le {h(x["detected_at"][:10])}, à confirmer</li>'
        for x in recent
    )
    items = []
    labels = {"ok": "OK", "changed": "À CONTRÔLER", "restricted": "ACCÈS LIMITÉ", "unavailable": "INACCESSIBLE"}
    for x in rows:
        state = x.get("state", "unavailable")
        note = " · " + h(x.get("reason", "")) if x.get("reason") else ""
        items.append(
            f'<div class="watch-source"><span class="watch-pill {h(state)}">{labels.get(state,"UNKNOWN")}</span>'
            f'<div><a href="{h(x["url"])}" target="_blank" rel="noopener noreferrer">{h(x["name"])} ↗</a>'
            f'<small>{h(x["group"])}{note}</small></div></div>'
        )
    return (
        '<div class="overline">CONTRÔLE AUTOMATIQUE DES SOURCES</div>'
        '<h3>Sites et logiciels sous surveillance</h3>'
        f'<p class="watch-intro">Dernier contrôle : {checked} (UTC). '
        'Un changement de page déclenche une alerte à examiner, jamais une version inventée.</p>'
        '<div class="watch-kpis">'
        f'<span><strong>{count}</strong> sources inscrites</span>'
        f'<span><strong>{ok}</strong> accessibles</span>'
        f'<span><strong>{changed}</strong> modifications détectées</span>'
        f'<span><strong>{restricted+unavailable}</strong> UNKNOWN / accès bloqué</span>'
        '</div>'
        + ('<div class="watch-changes"><b>Modifications récentes à vérifier :</b><ul>' + highlights + '</ul></div>'
           if highlights else '<p class="watch-intro">Aucune modification confirmée depuis la première référence disponible.</p>')
        + f'<details><summary>Afficher les {count} sources et leurs résultats de contrôle</summary>'
        + '<div class="watch-list">' + "".join(items) + '</div></details>'
    )

def build():
    airports = json.loads((PUBLIC / "airports.json").read_text(encoding="utf-8"))
    assert len(airports) == 171, f"Inventaire incomplet : {len(airports)} scènes"
    rows = render_rows(airports)
    status = json.loads((PUBLIC / "status.json").read_text(encoding="utf-8"))
    editorial = json.loads((PUBLIC / "editorial.json").read_text(encoding="utf-8"))
    from zoneinfo import ZoneInfo
    updated = status.get("last_run")
    if updated:
        dt_utc = dt.datetime.fromisoformat(updated.replace("Z", "+00:00"))
        paris = dt_utc.astimezone(ZoneInfo("Europe/Paris"))
        home_updated = "Le " + paris.strftime("%d/%m/%Y à %H:%M") + " (Paris)"
    else:
        home_updated = "En attente de la première collecte"
    editorial_updated = editorial.get("last_updated") or "Non actualisées"
    manifest_file = PUBLIC / "brand-manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.is_file() else {}
    index = (PUBLIC / "index.html").read_text(encoding="utf-8")
    watch_file = PUBLIC / "watch.json"
    watch = json.loads(watch_file.read_text(encoding="utf-8")) if watch_file.is_file() else {}
    index = index.replace('<div id="watch-container" class="watch-panel"><p>La surveillance quotidienne des sites sera affichée après la collecte.</p></div>',
                          '<div id="watch-container" class="watch-panel">' + render_watch(watch) + '</div>')
    index = static_brand_icons(index, manifest)
    index = index.replace("</body>", '<script type="application/json" id="brand-manifest">' +
                          json.dumps(manifest, ensure_ascii=False).replace("<", "\\u003c") +
                          '</script></body>')
    cards, home_cards = build_news(status, editorial, manifest)
    index = index.replace('<div id="news-container" class="news-grid"></div>',
                          '<div id="news-container" class="news-grid">' + cards + '</div>')
    index = index.replace('<div id="home-news" class="home-news"></div>',
                          '<div id="home-news" class="home-news">' + home_cards + '</div>')
    index = index.replace('id="home-updated">En attente de la première collecte</strong>',
                          'id="home-updated">' + h(home_updated) + '</strong>')
    index = index.replace('id="home-editorial-updated">Édition en préparation</strong>',
                          'id="home-editorial-updated">' + h(editorial_updated) + '</strong>')
    marker = '<tbody id="airport-body"></tbody>'
    assert index.count(marker) == 1, "Emplacement du tableau introuvable"
    index = index.replace(marker, f'<tbody id="airport-body">\n{rows}\n</tbody>')
    # The HTML query string alone does not invalidate Safari's cached app.js.
    rev = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    index = index.replace('src="app.js"', f'src="app.js?rev={rev}"')
    index = index.replace('href="styles.css"', f'href="styles.css?rev={rev}"')
    index = index.replace(
        '<div class="tablebox"><table>',
        '<p class="standalone-link"><a href="airports.html">↗ Afficher les 171 scènes sur une page indépendante (sans JavaScript)</a></p><div class="tablebox"><table>',
        1,
    )
    (PUBLIC / "index.html").write_text(index, encoding="utf-8")

    css = (PUBLIC / "styles.css").read_text(encoding="utf-8")
    table = (
        '<div class="tablebox"><table><thead><tr><th>ICAO</th><th>Scène / aéroport</th>'
        '<th>Éditeur</th><th>Installée</th><th>Serveur / statut</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )
    independent = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Le Journal MSFS — Inventaire complet</title>
<link rel="stylesheet" href="styles.css?rev={rev}">
<style>
body{{background:#f5f5f1}}
.independent-header{{background:#071b2c;color:white;padding:25px 0;border-bottom:4px solid #c6a073}}
.independent-header a{{color:#bfe4ff}}
.independent-header h1{{font:700 35px Georgia,serif;margin:12px 0}}
.independent-content{{padding:30px 0}}
.independent-content .tablebox{{max-height:none}}
.standalone-note{{margin:12px 0 20px}}
</style></head><body>
<header class="independent-header"><div class="shell">
<a href="./index.html#aeroports">← Retour au journal</a>
<h1>Mes 171 scènes et aéroports</h1>
<p>Inventaire complet issu d'Export APT 5.xlsx · {len(airports)} scènes · versions installées et vérifications officielles</p>
</div></header>
<main class="shell independent-content">
<p class="standalone-note">Cette page affiche toutes les scènes même si JavaScript est bloqué ou en cache dans Safari.</p>
{table}
<div class="map-section"><div class="overline">CARTE GOOGLE MY MAPS</div><h2>Mes aéroports sur la carte</h2>
<p><a href="https://www.google.com/maps/d/viewer?mid={MAP_ID}" target="_blank" rel="noopener noreferrer">Ouvrir la carte Google My Maps ↗</a></p>
<div class="map-box"><iframe title="Carte Google My Maps des aéroports" loading="eager" allowfullscreen src="https://www.google.com/maps/d/embed?mid={MAP_ID}&amp;ehbc=2E312F"></iframe></div>
</div></main></body></html>"""
    (PUBLIC / "airports.html").write_text(independent, encoding="utf-8")
    assert index.count("<tr>") >= len(airports), "Lignes statiques manquantes"
    assert "id=\"home-updated\">Le " in index, "Horodatage accueil absent"
    assert index.count('class="news-card"') >= 4, "Actualités officielles manquantes"
    assert index.count('class="watch-source"') >= 30, "Surveillance des sources manquante"
    assert index.count('class="topic-icon topic-') >= 15, "Pictogrammes graphiques manquants"
    assert index.count('src="brand/') >= 6, "Logos authentiques attendus absents du HTML publié"
    import xml.etree.ElementTree as ET
    icon_keys = ("si", "fenix", "mf", "winctrl", "msfs", "airport", "weather", "s3", "generic", "gsx", "atc", "fshud", "hardware", "navigraph", "traffic")
    for kind in icon_keys:
        svg_file = PUBLIC / "icons" / (kind + ".svg")
        assert svg_file.is_file(), f"Icône absente : {svg_file}"
        ET.parse(svg_file)  # Valider le SVG pour éviter les pictogrammes blancs dans Safari.
    for ref in re.findall(r'src="icons/([^"]+\.svg)"', index):
        assert (PUBLIC / "icons" / ref).is_file(), f"Icône HTML manquante : {ref}"
    assert independent.count("<tr>") >= len(airports), "Page indépendante incomplète"
    print(f"Publication : {len(airports)} scènes HTML statiques + page indépendante ; rev={rev}")

if __name__ == "__main__":
    build()
