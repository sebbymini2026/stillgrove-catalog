#!/usr/bin/env python3
"""
build-variations.py  —  embed extra style variations into index.html

The catalog (index.html) shows one card per style. Clicking a card opens a
per-style "variations" page. Variation 1 of every style is the render already
embedded in its card. This script embeds Variation 2, 3, ... from render files.

WHERE RENDERS LIVE
  Default: ~/Projects/Stillgrove/renders/
  Override with the STILLGROVE_RENDERS env var.

FILE NAMING CONVENTION (this is how a new variation "appears")
  Variation 1 (already in the card, do NOT add here):
      trend-<NN>-<slug>-studio.png
      trend-<NN>-<slug>-lifestyle.png
  Extra variations (this script picks these up):
      trend-<NN>-<slug>-v<K>-studio.png       <- required  (K = 2,3,4,...)
      trend-<NN>-<slug>-v<K>-lifestyle.png     <- optional
  <NN> must match the card's catalog number. The studio image is required;
  the in-room (lifestyle) image is optional. Add files, run this, redeploy.

USAGE
  python3 build-variations.py            # rebuild EXTRA_VARIATIONS in index.html
  python3 build-variations.py --dry-run  # report what it would embed, no write

It rewrites only the block between
  /* === STILLGROVE_VARIATIONS_START ... */ ... /* === STILLGROVE_VARIATIONS_END === */
so it is safe to run repeatedly and never touches the rest of the page.
"""
import os, re, io, sys, json, base64, hashlib

HERE    = os.path.dirname(os.path.abspath(__file__))
INDEX   = os.environ.get("STILLGROVE_INDEX", os.path.join(HERE, "index.html"))
RENDERS = os.environ.get(
    "STILLGROVE_RENDERS",
    os.path.expanduser("~/Projects/Stillgrove/renders"),
)
THUMB_W = 480     # match the existing in-card thumbnails (480x720)
JPEG_Q  = 72
DRY     = "--dry-run" in sys.argv

# Optional art-inspiration credits: {num: {k: "After Artist — Work (year)"}}.
# Used as each variation's label so the catalog lists the exact source artwork.
CREDITS_PATH = os.environ.get(
    "STILLGROVE_CREDITS", os.path.join(HERE, "..", "pipeline", "credits.json")
)
try:
    with open(CREDITS_PATH, encoding="utf-8") as _cf:
        CREDITS = json.load(_cf)
except Exception:
    CREDITS = {}

PAT = re.compile(r'^trend-(\d+)-(.+?)-v(\d+)-(studio|lifestyle)\.png$', re.I)
START = "/* === STILLGROVE_VARIATIONS_START"
END   = "/* === STILLGROVE_VARIATIONS_END === */"


def thumb_data_uri(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if w > THUMB_W:
        im = im.resize((THUMB_W, round(h * THUMB_W / w)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=JPEG_Q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def collect():
    if not os.path.isdir(RENDERS):
        print(f"renders dir not found: {RENDERS}"); return {}
    groups = {}  # num -> { k -> {studio,life} }
    for fn in sorted(os.listdir(RENDERS)):
        m = PAT.match(fn)
        if not m:
            continue
        num, k, kind = int(m.group(1)), int(m.group(3)), m.group(4).lower()
        slot = "studio" if kind == "studio" else "life"
        groups.setdefault(num, {}).setdefault(k, {})[slot] = os.path.join(RENDERS, fn)
    return groups


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    groups = collect()
    extra, total, skipped_dup = {}, 0, 0
    seen_md5 = {}  # md5 -> first "trend-N vK" that used it (render order = numeric num,k)
    for num in sorted(groups):
        arr = []
        for k in sorted(groups[num]):
            imgs = groups[num][k]
            if "studio" not in imgs:
                print(f"  skip trend-{num} v{k}: missing studio image"); continue
            # Skip byte-identical duplicates (stale images saved when ChatGPT was rate-capped).
            digest = _md5(imgs["studio"])
            if digest in seen_md5:
                print(f"  skip trend-{num} v{k}: duplicate of {seen_md5[digest]}"); skipped_dup += 1; continue
            seen_md5[digest] = f"trend-{num} v{k}"
            credit = (CREDITS.get(str(num)) or {}).get(str(k))
            entry = {"label": credit or f"Variation {k}",
                     "note": f"Variation {k}" if credit else "",
                     "studio": "<studio>" if DRY else thumb_data_uri(imgs["studio"])}
            if "life" in imgs:
                entry["life"] = "<life>" if DRY else thumb_data_uri(imgs["life"])
            arr.append(entry); total += 1
            print(f"  trend-{num} v{k}: {credit or '(no credit)'}")
        if arr:
            extra[num] = arr

    block_inner = "const EXTRA_VARIATIONS = " + json.dumps(extra, separators=(",", ":")) + ";"
    print(f"\n{total} extra variation(s) across {len(extra)} style(s); {skipped_dup} duplicate(s) skipped.")
    if DRY:
        print("dry-run: index.html not modified."); return

    html = open(INDEX, encoding="utf-8").read()
    s = html.find(START); e = html.find(END)
    if s == -1 or e == -1:
        print("FATAL: variation markers not found in index.html"); sys.exit(1)
    line_start = html.rfind("\n", 0, s) + 1  # keep marker comment line, replace the const line
    head = html[:s]
    new_block = (html[s:e].split("\n")[0] + "\n" + block_inner + "\n" + END)
    html2 = head + new_block + html[e + len(END):]
    open(INDEX, "w", encoding="utf-8").write(html2)
    print(f"updated {INDEX}")


if __name__ == "__main__":
    main()
