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

def h(value):
    return html.escape(str(value if value is not None else ""), quote=True)

def compare(installed, online):
    a = [int(x) for x in re.findall(r"\d+", str(installed or ""))]
    b = [int(x) for x in re.findall(r"\d+", str(online or ""))]
    if not a or not b or len(a)!=len(b):
        return "À COMPARER", "flag-v"
    if a[0]!=b[0]:
        return ("NOUVELLE ÉDITION", "flag-v") if b[0]>a[0] else ("INSTALLÉE + RÉCENTE", "flag-v")
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
        store = str(a.get("source_store") or "Éditeur")
        edition = str(a.get("source_edition") or "")
        source_label = h(store + (" · " + edition if edition else ""))
        source = f'<small><a href="{h(url)}" target="_blank" rel="noopener noreferrer">{source_label} ↗</a></small>' if url.startswith("https://") else ""
        if not source and str(a.get("source_catalog_url") or "").startswith("https://"):
            source = (f'<small><a href="{h(a["source_catalog_url"])}" target="_blank" rel="noopener noreferrer">'
                      'Catalogue éditeur (pas de version confirmée) ↗</a></small>')
        online = a.get("server_version")
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        verified_today = (a.get("version_check_state") == "verified"
                          and a.get("version_checked_at") == today)
        if online and verified_today:
            comparison = a.get("version_comparison")
            label, flag = (("MISE À JOUR", "flag-s") if comparison == "update"
                           else ("À JOUR", "flag-ok") if comparison == "equal"
                           else ("À COMPARER", "flag-v"))
            status = f'<b>{h(online)}</b><small><span class="flag {flag}">{h(label)}</span></small>{source}'
            status += f'<small>Vérifiée le {h(a["version_checked_at"])}</small>'
        elif online:
            state = str(a.get("status") or "UNK-V")
            if state == "verified":
                state = "UNK-V"
            source_today = a.get("version_checked_at") == today
            source_note = ("Version de la fiche contrôlée aujourd’hui, mais comparaison non validée"
                           if source_today else "Dernière version connue, non revalidée aujourd’hui")
            status = (f'<b>{h(online)}</b><small>{source_note}</small>'
                      f'<small><span class="flag flag-{cls.get(state, "v")}">{h(state)}</span></small>{source}')
            if a.get("version_checked_at"):
                status += f'<small>Dernière confirmation : {h(a["version_checked_at"])}</small>'
        else:
            state = str(a.get("status") or "UNK-V")
            status = f'<span class="flag flag-{cls.get(state, "v")}">{h(state)}</span>{source}'
        if a.get("version_check_reason") and a.get("version_check_state")!="verified":
            status += f'<small class="source-note">{h(a["version_check_reason"])}</small>'
        if a.get("source_note"):
            status += f'<small class="source-note">{h(a["source_note"])}</small>'
        if a.get("reference_version") and a.get("reference_source_url"):
            hint_label = ("Référence éditeur contrôlée manuellement" if a.get("reference_confidence") in
                          ("publisher_page_human_checked", "official_support_human_checked")
                          else "Indication tierce non officielle")
            status += (f'<small class="source-note">{hint_label} : '
                       f'<a href="{h(a["reference_source_url"])}" target="_blank" rel="noopener noreferrer">'
                       f'{h(a["reference_version"])} ↗</a> (non utilisée pour les alertes automatiques)</small>')
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

def render_airport_digest(airports):
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    updates = []
    editions = []
    for a in airports:
        if a.get("version_check_state") != "verified" or a.get("version_checked_at") != today:
            continue
        label, _ = compare(a.get("installed"), a.get("server_version"))
        if label not in ("MISE À JOUR", "NOUVELLE ÉDITION"):
            continue
        url = str(a.get("source_url") or "")
        source = (f'<a href="{h(url)}" target="_blank" rel="noopener noreferrer">'
                  f'{h(a.get("source_store") or "Fiche source")} ↗</a>') if url.startswith("https://") else ""
        line = (f'<li><span class="airport-update-code">{h(a.get("icao") or "")}</span>'
                f'<span><strong>{h(a.get("name") or "")}</strong>'
                f'<small>{h(a.get("publisher") or "")} · Installée {h(a.get("installed") or "?")} '
                f'→ Source {h(a.get("server_version") or "?")} · {source}</small></span></li>')
        (updates if label == "MISE À JOUR" else editions).append(line)
    for a in airports:
        if not a.get("new_edition_version") or not a.get("source_url"):
            continue
        edition_status = "Vérifiée aujourd’hui" if a.get("new_edition_checked_at")==today else "Dernière version connue, non revalidée"
        editions.append(
            f'<li><span class="airport-update-code">{h(a.get("icao") or "")}</span>'
            f'<span><strong>{h(a.get("name") or "")} — édition MSFS 2024 distincte</strong>'
            f'<small>Installée {h(a.get("installed") or "?")} · Nouvelle édition '
            f'{h(a["new_edition_version"])} · {h(edition_status)} · '
            f'<a href="{h(a["source_url"])}" target="_blank" rel="noopener noreferrer">'
            f'{h(a.get("source_store") or "Éditeur")} ↗</a></small>'
            f'<small>{h(a.get("source_note") or "")}</small></span></li>'
        )
    checked = sum(a.get("version_check_state") == "verified" and a.get("version_checked_at") == today
                  for a in airports)
    body = ('<div class="airport-update-head"><div class="overline">BILAN QUOTIDIEN DES VERSIONS</div>'
            f'<h3>{len(updates)} mise(s) à jour vérifiée(s) · {checked}/{len(airports)} sources contrôlées</h3>'
            f'<p>État des boutiques publiques au {h(today)} (UTC). '
            'Les changements d’édition majeure sont signalés séparément ; '
            'les autres scènes restent UNKNOWN si leur version ne peut pas être confirmée.</p></div>')
    if updates:
        body += '<ul class="airport-update-list">' + ''.join(updates) + '</ul>'
    else:
        body += '<p class="airport-update-empty">Aucune mise à jour comparable confirmée lors de cette collecte.</p>'
    if editions:
        body += (f'<details><summary>{len(editions)} nouvelle(s) édition(s) majeure(s) '
                 '(tarif et compatibilité à vérifier)</summary><ul class="airport-update-list">'
                 + ''.join(editions) + '</ul></details>')
    return body

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
    now = dt.datetime.now(dt.timezone.utc)
    def published_at(item):
        raw = str(item.get("published_at") or item.get("date") or "")
        try:
            parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=dt.timezone.utc) if parsed.tzinfo is None else parsed.astimezone(dt.timezone.utc)
        except (ValueError, TypeError):
            return dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
    def age_group(item):
        age = now - published_at(item)
        if age <= dt.timedelta(hours=24):
            return 0
        if age <= dt.timedelta(hours=72):
            return 1
        if age <= dt.timedelta(days=7):
            return 2
        return 3
    # Trois groupes : NEWS 0-24 h, normales 24-72 h, OLD 72 h-7 j.
    news.sort(key=lambda item: (age_group(item), -published_at(item).timestamp()))
    cards = []
    homes = []
    for a in news:
        group = age_group(a)
        if group == 3:
            continue
        label, kind = news_topic(a)
        icon = brand_icon(kind, manifest)
        title = h(a.get("title") or "")
        date = h(a.get("date") or "")
        category = h(a.get("category") or "ACTUALITÉS")
        url = h(a["url"])
        source = h(a.get("source") or "Source officielle")
        old = group == 2
        cards.append(
            '<article class="news-card' + (' news-old' if old else '') + '"><div class="news-meta">' + category + ' · ' + date +
            ('<span class="old-tag">OLD</span>' if old else '<span class="new-tag">NEWS</span>' if group == 0 else '') +
            '</div><div class="news-heading">' + icon + '<h3>' + title + '</h3></div>' +
            ('<p>' + h(a["summary"]) + '</p>' if a.get("summary") else "") +
            ('<div class="news-impact"><b>Impact / action :</b> ' + h(a["impact"]) + '</div>' if a.get("impact") else "") +
            '<div class="news-source"><a href="' + url + '" target="_blank" rel="noopener noreferrer">' + source + ' ↗</a></div></article>'
        )
        if group != 0:
            continue
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
    assert len(airports) >= 1, "Inventaire des scènes vide"
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
    index = index.replace('<div id="airport-update-digest" class="airport-update-digest"><p>Les mises à jour confirmées seront affichées après la vérification quotidienne.</p></div>',
                          '<div id="airport-update-digest" class="airport-update-digest">' + render_airport_digest(airports) + '</div>')
    index = static_brand_icons(index, manifest)
    index = index.replace("</body>", '<script type="application/json" id="brand-manifest">' +
                          json.dumps(manifest, ensure_ascii=False).replace("<", "\\u003c") +
                          '</script></body>')
    cards, home_cards = build_news(status, editorial, manifest)
    index = index.replace('<div id="news-container" class="news-grid"></div>',
                          '<div id="news-container" class="news-grid">' + cards + '</div>')
    # AIRAC : référence officielle 2610, entrée en vigueur le 01/10/2026.
    # Cycles de 28 jours. Ne pas assimiler un premier affichage à NEWS.
    today_airac = dt.datetime.now(dt.timezone.utc).date()
    anchor = dt.date(2026, 10, 1)
    step = (today_airac - anchor).days // 28
    start = anchor + dt.timedelta(days=step * 28)
    end = start + dt.timedelta(days=27)
    cycle_month = 10 + step
    cycle_year = 2026 + (cycle_month - 1) // 13
    cycle = f"{cycle_year % 100:02d}{(cycle_month - 1) % 13 + 1:02d}"
    previous = status.get("airac_cycle")
    changed = today_airac == start
    status["airac_cycle"] = cycle
    (PUBLIC / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    airac = ('<div class="airac-banner"><b>NAVIGRAPH AIRAC ' + h(cycle) + '</b> ' +
             ('<span class="new-tag">NEWS</span> ' if changed else '') +
             h(start.strftime("%d/%m/%Y")) + ' – ' + h(end.strftime("%d/%m/%Y")) + '</div>')
    index = index.replace('<main id="main" class="shell main">', '<main id="main" class="shell main">' + airac, 1)
    # Résumé très compact des actualités du jour dans le bandeau héro.
    recent_hero = []
    for item in (editorial.get("news") or []) + (status.get("news") or []):
        raw = str(item.get("published_at") or item.get("date") or "")
        try:
            published = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=dt.timezone.utc)
        except (ValueError, TypeError):
            continue
        if dt.timedelta(0) <= dt.datetime.now(dt.timezone.utc) - published <= dt.timedelta(hours=24):
            recent_hero.append(item)
    recent_hero.sort(key=lambda item: str(item.get("published_at") or item.get("date") or ""), reverse=True)
    hero_items = []
    hero_seen = set()
    for item in recent_hero:
        if item.get("url") in hero_seen:
            continue
        hero_seen.add(item.get("url"))
        summary = str(item.get("summary") or item.get("title") or "").strip()
        hero_items.append('<div class="hero-news-item">' +
                          brand_icon(news_topic(item)[1], manifest) +
                          '<span>' + h(summary) + '</span></div>')
    hero_summary = '<div class="hero-news-summary" aria-label="Actualités des dernières 24 heures">' + (
        "".join(hero_items) if hero_items else '<span class="hero-news-empty">Aucune nouvelle publication officielle ces dernières 24 h</span>'
    ) + '</div>'
    index = index.replace('<button class="cta" data-goto="nouveautes">', hero_summary + '<button class="cta" data-goto="nouveautes">', 1)
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
        f'<p class="standalone-link"><a href="airports.html">↗ Afficher les {len(airports)} scènes sur une page indépendante (sans JavaScript)</a></p><div class="tablebox"><table>',
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
<h1>Mes {len(airports)} scènes et aéroports</h1>
<p>Inventaire complet synchronisé depuis le dernier Excel disponible · {len(airports)} scènes · versions installées et vérifications officielles</p>
</div></header>
<main class="shell independent-content">
<p class="standalone-note">Cette page affiche toutes les scènes même si JavaScript est bloqué ou en cache dans Safari.</p>
<div class="airport-update-digest">{render_airport_digest(airports)}</div>
{table}
<div class="map-section"><h2>Carte interactive des aéroports</h2><p><a href="./index.html#aeroports">Ouvrir la carte interactive avec repères colorés</a></p><div id="airport-leaflet-map" hidden></div></div></div></main></body></html>"""
    (PUBLIC / "airports.html").write_text(independent, encoding="utf-8")
    assert index.count("<tr>") >= len(airports), "Lignes statiques manquantes"
    assert "id=\"home-updated\">Le " in index, "Horodatage accueil absent"
    assert index.count('class="news-card') >= 4, "Actualités officielles manquantes"
    assert index.count('class="watch-source"') >= 30, "Surveillance des sources manquante"
    assert 'id="airport-update-digest"' in index, "Bilan des mises à jour de scènes absent"
    assert 'class="airport-update-digest"' in independent, "Bilan de secours absent"
    assert index.count('class="topic-icon topic-') >= 1, "Pictogrammes graphiques manquants"
    assert 'icons/mf.svg' in index, "Logo MobiFlight officiel absent"
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
