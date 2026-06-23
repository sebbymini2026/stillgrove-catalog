#!/usr/bin/env python3
"""build-sculpture-cards.py — insert/refresh the "Modern Sculpture" section
(#93-152) in index.html. Idempotent (replaces between SCULPT_SECTION markers).
Studio-only cards. Run now (placeholders) and again as renders land."""
import os, io, re, json, base64, html, urllib.parse
HERE   = os.path.dirname(os.path.abspath(__file__))
INDEX  = os.path.join(HERE, "index.html")
BATCH  = os.path.join(HERE, "..", "pipeline", "sculpture-batch.json")
RENDERS= os.environ.get("STILLGROVE_RENDERS", os.path.expanduser("~/Projects/Stillgrove/renders"))
THUMB_W, JPEG_Q = 480, 72
START, END = "<!--SCULPT_SECTION_START-->", "<!--SCULPT_SECTION_END-->"

def studio_uri(num, slug):
    path = os.path.join(RENDERS, f"trend-{num}-{slug}-studio.png")
    if os.path.exists(path) and os.path.getsize(path) > 50_000:
        from PIL import Image
        im = Image.open(path).convert("RGB"); w, h = im.size
        if w > THUMB_W: im = im.resize((THUMB_W, round(h*THUMB_W/w)), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=JPEG_Q, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), True
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='480' height='600'>"
           "<rect width='100%' height='100%' fill='#e9e6df'/><rect x='0' y='0' width='100%' height='100%' "
           "fill='none' stroke='#cfc8ba' stroke-width='2'/><text x='50%' y='47%' fill='#8a8475' "
           "font-family='Georgia,serif' font-size='22' text-anchor='middle'>STILLGROVE</text>"
           "<text x='50%' y='54%' fill='#a59c8c' font-family='Georgia,serif' font-size='15' "
           "text-anchor='middle'>render pending</text></svg>")
    return "data:image/svg+xml," + urllib.parse.quote(svg), False

def esc(s): return html.escape(str(s), quote=True)

def card_html(r):
    src, _ = studio_uri(r["num"], r["slug"]); p = r["photo"]
    name = esc(f'{r["title"]} {r["building"]} {r["dna"]}'.lower())
    if p.get("img"):
        insp = (f'<div class="insp"><img src="{esc(p["img"])}" alt="{esc(p["alt"])}" loading="lazy" '
                f'referrerpolicy="no-referrer" onerror="this.closest(\'.insp\').classList.add(\'noimg\')">'
                f'<div class="inspcap"><span class="ilbl">Inspiration · the sculpture</span>{esc(r["buildingShort"])}'
                f'<a href="{esc(p["page"])}" target="_blank">photo: {esc(p["credit"])}</a></div></div>')
    else:
        insp = (f'<div class="insp noimg-note">Inspiration · the sculpture: {esc(r["buildingShort"])} — '
                f'<a href="{esc(p["page"])}" target="_blank">see it on Wikipedia</a></div>')
    return (
        f'<article class="card" data-cat="Sculpture" data-name="{name}" data-price="{r["price"]}" data-num="{r["num"]}">\n'
        f'      <div class="imgwrap">\n          <img class="ph studio" src="{src}" alt="{esc(r["title"])} studio" loading="lazy">\n        </div>\n'
        f'      <div class="body">\n        <div class="hdr"><span class="num">{r["num"]}</span><h3>{esc(r["title"])}</h3></div>\n'
        f'        <div class="price">{esc(r["band"])} <span class="margin">· {esc(r["margin"])}</span></div>\n'
        f'        <div class="from"><span class="lbl">Based on</span> {esc(r["building"])}</div>\n'
        f'        <div class="tags"><span class="src">Modern sculpture</span><span class="cat">Sculpture</span></div>\n'
        f'        <details>\n          <summary>Design details</summary>\n          {insp}\n'
        f'          <p><b>Design DNA borrowed:</b> {esc(r["dna"])}</p>\n'
        f'          <p><b>STILLGROVE piece:</b> {esc(r["piece"])}</p>\n'
        f'          <p><b>Materials:</b> {esc(r["materials"])}</p>\n'
        f'          <p><b>Size:</b> {esc(r["size"])}</p>\n        </details>\n      </div>\n    </article>'
    )

def main():
    recs = json.load(open(BATCH, encoding="utf-8"))
    doc = open(INDEX, encoding="utf-8").read()
    if not os.path.exists(INDEX + ".bak2"): open(INDEX + ".bak2","w",encoding="utf-8").write(doc)
    real = sum(1 for r in recs if studio_uri(r["num"], r["slug"])[1])
    block = START + "\n" + "".join(card_html(r) for r in recs) + "\n" + END
    if START in doc and END in doc:
        doc = re.sub(re.escape(START)+r".*?"+re.escape(END), lambda m: block, doc, flags=re.S)
    else:
        di = doc.find('<section id="detail"'); gi = doc.rfind("</div>", 0, di)
        doc = doc[:gi] + block + "\n" + doc[gi:]
    if 'data-cat="Sculpture"' not in re.sub(re.escape(START)+r".*?"+re.escape(END), "", doc, flags=re.S):
        doc = doc.replace('<button class="catbtn" data-cat="Architecture">Architecture</button>',
                          '<button class="catbtn" data-cat="Architecture">Architecture</button><button class="catbtn" data-cat="Sculpture">Sculpture</button>', 1)
    open(INDEX,"w",encoding="utf-8").write(doc)
    print(f"inserted/refreshed {len(recs)} Sculpture cards ({real} real, {len(recs)-real} placeholders)")

if __name__ == "__main__":
    main()
