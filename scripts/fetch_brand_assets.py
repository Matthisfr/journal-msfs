"""Fetch original brand marks for the MSFS journal.
Logos remain unchanged; CSS applies the shared frame. Unavailable logos fall
back to the already bundled custom SVG. Never block the journal for a logo.
"""
from __future__ import annotations

import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
DEST = PUBLIC / "brand"
DEST.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "si": ("https://api.sayintentions.ai/images/si_logo_blue.png", "png", "SayIntentions.AI — logo officiel"),
    "fenix": ("https://www.google.com/s2/favicons?domain=fenixsim.com&sz=128", "png", "Fenix Simulations — favicon du site"),
    "msfs": ("https://docs.flightsimulator.com/msfs2024/cover.png", "png", "Microsoft Flight Simulator — visuel SDK officiel"),
    "winctrl": ("https://cdn.fsnews.eu/uploads/2025/12/QmRMv8ypExsv1B4rbGsQWAxeSRqjCrEVNDFEkAuyRHJaWx-scaled.jpg", "jpg", "WINCTRL — visuel de marque publié par FSNews"),
    "gsx": ("https://assets-global.website-files.com/5b27a494dc3d312fe5c01da8/63cc77b9b0c560cfb0f3392e_gsxpro.jpg", "jpg", "GSX Pro — visuel promotionnel reproduit par Threshold"),
    "navigraph": ("https://www.google.com/s2/favicons?domain=navigraph.com&sz=128", "png", "Navigraph — favicon du site"),
    "fshud": ("https://www.google.com/s2/favicons?domain=fshud.com&sz=128", "png", "FSHud — favicon du site"),
}

def valid(data: bytes, ext: str) -> bool:
    if not 100 < len(data) < 3_000_000:
        return False
    if ext == "png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == "jpg":
        return data.startswith(b"\xff\xd8\xff")
    return False

def run():
    # Official MobiFlight favicon.svg is imported directly from its GitHub website.
    manifest = {"mf": {"path": "icons/mf.svg", "source": "MobiFlight/mobiflight-website — favicon.svg officiel"}}
    for kind, (url, ext, credit) in SOURCES.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; MSFS-Journal/1.0)", "Accept": "image/*"})
            with urllib.request.urlopen(req, timeout=13) as resp:
                data = resp.read(3_000_001)
            if not valid(data, ext):
                raise ValueError("Format image invalide ou taille anormale")
            path = DEST / f"{kind}.{ext}"
            path.write_bytes(data)
            manifest[kind] = {"path": f"brand/{kind}.{ext}", "source": credit, "origin": url}
            print(f"Logo source récupéré : {kind} ({len(data)} octets)")
        except Exception as exc:
            print(f"Logo source indisponible : {kind} ({type(exc).__name__}: {exc}); pictogramme local conservé")
    (PUBLIC / "brand-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Logos originaux disponibles : {len(manifest)} / {len(SOURCES) + 1}")

if __name__ == "__main__":
    run()
