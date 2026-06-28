#!/usr/bin/env python3
"""build-geowood-cards.py — embed the 'Geometric Wood' batch into index.html.

Dedicated clone of build-rock-cards.py for the dimensional-WOOD wall-art line.
Idempotent: the batch lives between <!--GEO_WOOD_START--> / _END comments, so it
can be re-run as renders land (placeholder -> real image) without touching the
other catalog sections.

Usage:
  build-geowood-cards.py --meta ../pipeline/geowood-meta.json --marker GEO_WOOD \\
                         --renders ../renders/geometric-wood
Run on the Mac to embed real thumbnails (needs Pillow + the render PNGs). Run
anywhere to (re)scaffold 'render pending' placeholders — Pillow is only imported
once a real PNG exists.
"""
import os, io, re, json, base64, html as H, urllib.parse, argparse, datetime

HERE  = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "index.html")
THUMB_W, JPEG_Q = 480, 72

def esc(s): return H.escape(str(s), quote=True)

def img_uri(path):
    """Return (data_uri, is_real). Real render -> resized JPEG; else 'pending' SVG."""
    if path and os.path.exists(path) and os.path.getsize(path) > 200_000:
        try:
            from PIL import Image
            im = Image.open(path).convert("RGB"); w, h = im.size
            if w > THUMB_W: im = im.resize((THUMB_W, round(h*THUMB_W/w)), Image.LANCZOS)
            buf = io.BytesIO(); im.save(buf, "JPEG", quality=JPEG_Q, optimize=True)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), True
        except Exception as e:
            print("  ! PIL failed on", os.path.basename(path), e)
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='480' height='600'>"
           "<rect width='100%' height='100%' fill='#e9e6df'/>"
           "<rect x='0' y='0' width='100%' height='100%' fill='none' stroke='#cfc8ba' stroke-width='2'/>"
           "<text x='50%' y='47%' fill='#8a8475' font-family='Georgia,serif' font-size='22' "
           "text-anchor='middle'>STILLGROVE</text>"
           "<text x='50%' y='54%' fill='#a59c8c' font-family='Georgia,serif' font-size='15' "
           "text-anchor='middle'>render pending</text></svg>")
    return "data:image/svg+xml," + urllib.parse.quote(svg), False

def copy_for(cat):
    # Dedicated builder — every card in this batch is a dimensional wood wall relief.
    return dict(
        src_tag="Dimensional wood wall art",
        piece="A dimensional wood wall relief built from hundreds of precisely-cut blocks set at varied "
              "depths and finished with layered stain that lets the natural grain show through — crisp "
              "geometric structure with warm, hand-crafted character. Arrives ready to hang on a concealed "
              "aluminium French cleat.",
        materials="Precision-cut hardwood blocks (oak, walnut, ash, maple), layered stain &amp; matte paint, "
                  "protective topcoat, pre-installed aluminium French cleat with bubble level",
        size="~18×36 in to 36×84 in &nbsp;·&nbsp; wall-mounted &nbsp;·&nbsp; larger sizes ship as aligned multi-panels")

def card_html(r, renders_dir):
    cat = r["cat"]; c = copy_for(cat)
    src, _ = img_uri(os.path.join(renders_dir, r["file"]))
    name_search = esc(f'{r["name"]} {r["based_on"]} {r["dna"]} {cat}'.lower())
    label = r.get("label", "geometric wood")
    dna = r["dna"]; dna = dna if dna.endswith(".") else dna + "."
    return (
        f'<article class="card" data-cat="{esc(cat)}" data-name="{name_search}" data-price="{r["price"]}" data-num="{r["num"]}">\n'
        f'      <div class="imgwrap">\n          <img class="ph studio" src="{src}" alt="{esc(r["name"])} studio" loading="lazy">\n        </div>\n'
        f'      <div class="body">\n        <div class="hdr"><span class="num">{r["num"]}</span><h3>{esc(r["name"])}</h3></div>\n'
        f'        <div class="price">${r["price"]} <span class="margin">· {esc(label)}</span></div>\n'
        f'        <div class="from"><span class="lbl">Inspired by</span> {esc(r["based_on"])}</div>\n'
        f'        <div class="tags"><span class="src">{esc(c["src_tag"])}</span><span class="cat">{esc(cat)}</span></div>\n'
        f'        <details>\n          <summary>Design details</summary>\n'
        f'          <p><b>Design DNA:</b> {esc(dna)[0].upper()+esc(dna)[1:]}</p>\n'
        f'          <p><b>STILLGROVE piece:</b> {c["piece"]}</p>\n'
        f'          <p><b>Materials:</b> {c["materials"]}</p>\n'
        f'          <p><b>Size:</b> {c["size"]}</p>\n        </details>\n      </div>\n    </article>'
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", required=True)
    ap.add_argument("--marker", default="GEO_WOOD", help="e.g. GEO_WOOD")
    ap.add_argument("--renders", required=True, help="dir holding this batch's PNGs")
    a = ap.parse_args()
    meta = os.path.join(HERE, a.meta) if not os.path.isabs(a.meta) else a.meta
    rdir = os.path.join(HERE, a.renders) if not os.path.isabs(a.renders) else a.renders
    recs = json.load(open(meta, encoding="utf-8"))
    cat  = recs[0]["cat"]
    START, END = f"<!--{a.marker}_START-->", f"<!--{a.marker}_END-->"

    doc = open(INDEX, encoding="utf-8").read()
    bak = INDEX + ".bak-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    open(bak, "w", encoding="utf-8").write(doc)

    real = sum(1 for r in recs if img_uri(os.path.join(rdir, r["file"]))[1])
    block = START + "\n" + "".join(card_html(r, rdir) for r in recs) + "\n" + END

    if START in doc and END in doc:
        doc = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, doc, flags=re.S)
    else:
        di = doc.find('<section id="detail"')
        gi = doc.rfind("</div>", 0, di) if di > 0 else -1
        if gi < 0:  # fallback: before </main> or end of grid
            gi = doc.rfind("</div>")
        doc = doc[:gi] + block + "\n" + doc[gi:]

    # category filter button (idempotent) — insert before the search spacer
    if f'data-cat="{cat}"' not in re.sub(r'<article.*?</article>', '', doc, flags=re.S):
        btn = f'<button class="catbtn" data-cat="{esc(cat)}">{esc(cat)}</button>\n  '
        doc = doc.replace('<span class="spacer"></span>', btn + '<span class="spacer"></span>', 1)

    open(INDEX, "w", encoding="utf-8").write(doc)
    print(f'[{a.marker}] {cat}: {len(recs)} cards ({real} real, {len(recs)-real} pending). backup -> {os.path.basename(bak)}')

if __name__ == "__main__":
    main()
