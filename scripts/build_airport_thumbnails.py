"""Build map thumbnails from the installed scenes' ContentInfo folders."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

PUBLIC = Path(__file__).resolve().parents[1] / "public"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenes", type=Path)
    args = parser.parse_args()
    if not args.scenes.is_dir():
        parser.error("Le dossier des scènes est introuvable.")

    airports = json.loads((PUBLIC / "airports.json").read_text(encoding="utf-8"))
    folders = {row["folder"] for row in airports if row.get("folder")}
    scenes = {}
    for manifest in args.scenes.rglob("manifest.json"):
        folder = manifest.parent
        key = folder.name.casefold()
        if key in scenes:
            raise ValueError(f"Dossier de scène ambigu : {folder.name}")
        scenes[key] = folder

    target = PUBLIC / "airport-thumbnails"
    target.mkdir(exist_ok=True)
    index = {}
    for name in sorted(folders):
        folder = scenes.get(name.casefold())
        if folder is None:
            continue
        candidates = sorted(
            p for p in (folder / "ContentInfo").rglob("*")
            if p.is_file() and p.stem.casefold() == "thumbnail"
            and p.suffix.casefold() in {".jpg", ".jpeg", ".png", ".webp"}
        )
        matching = [p for p in candidates if p.parent.name.casefold() == folder.name.casefold()]
        candidates = matching or candidates
        if len(candidates) != 1:
            if len(candidates) > 1:
                print(f"Plusieurs miniatures : {name}")
            continue
        try:
            with Image.open(candidates[0]) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((560, 315), Image.Resampling.LANCZOS)
                filename = hashlib.sha256(name.encode("utf-8")).hexdigest()[:24] + ".webp"
                image.save(target / filename, format="WEBP", quality=76, method=6)
                index[name] = filename
        except (OSError, UnidentifiedImageError) as error:
            print(f"Image illisible pour {name} : {error}")

    (PUBLIC / "airport-thumbnails.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    used = set(index.values())
    for image in target.glob("*.webp"):
        if image.name not in used:
            image.unlink()
    print(f"{len(index)} miniatures pour {len(folders)} scènes du journal.")


if __name__ == "__main__":
    main()
