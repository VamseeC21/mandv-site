#!/usr/bin/env python3
"""Drop new photos in images/, then run:  python3 build.py
Makes small thumbnails + web-sized full images in photos/ and writes photos.js.
Only new/changed photos are processed, so re-runs are fast."""
import json, os, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).parent
SRC, OUT = ROOT / "images", ROOT / "photos"
THUMB, FULL = 640, 2000
EXTS = {".jpg", ".jpeg", ".png", ".heic"}

(OUT / "thumb").mkdir(parents=True, exist_ok=True)
(OUT / "full").mkdir(parents=True, exist_ok=True)

# one source per name; prefer non-HEIC when both exist (phone exports pairs)
chosen = {}
for p in sorted(SRC.iterdir()):
    if p.suffix.lower() in EXTS and not p.name.startswith("."):
        cur = chosen.get(p.stem)
        if cur is None or (cur.suffix.lower() == ".heic" and p.suffix.lower() != ".heic"):
            chosen[p.stem] = p

manifest = []
for stem, p in sorted(chosen.items()):
    t, f = OUT / "thumb" / f"{stem}.webp", OUT / "full" / f"{stem}.webp"
    src = p
    if not (t.exists() and f.exists() and t.stat().st_mtime >= p.stat().st_mtime):
        if p.suffix.lower() == ".heic":
            tmp = Path(tempfile.mkdtemp()) / f"{stem}.jpg"
            subprocess.run(["sips", "-s", "format", "jpeg", str(p), "--out", str(tmp)],
                           check=True, capture_output=True)
            src = tmp
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        for dest, size, q in ((f, FULL, 82), (t, THUMB, 78)):
            c = im.copy(); c.thumbnail((size, size), Image.LANCZOS)
            c.save(dest, "WEBP", quality=q, method=6)
        print("processed", p.name)
    with Image.open(t) as th:
        w, h = th.size
    manifest.append({"id": stem, "w": w, "h": h})

(ROOT / "photos.js").write_text("window.PHOTOS = " + json.dumps(manifest) + ";\n")
print(f"{len(manifest)} photos -> photos.js")
