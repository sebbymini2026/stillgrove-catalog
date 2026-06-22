#!/usr/bin/env python3
"""
build-architecture-cards.py — insert/refresh the "Abstract Architecture" section
(#63-92) in index.html. Idempotent: replaces everything between the markers
  <!--ARCH_SECTION_START--> ... <!--ARCH_SECTION_END-->
so it is safe to run now (placeholder product images) and again after the renders
land (real studio JPEGs embedded the same way as the existing cards).

Reads pipeline/architecture-batch.json. Studio-only cards (no in-room toggle) —
the catalog JS already null-checks .ph.life, so these render correctly in both
the grid and the detail/variation view.
"""
import os, io, re, json, base64, html, urllib.parse

HERE   = os.path.dirname(os.path.abspath(__file__))
INDEX  = os.path.join(HERE, "index.html")
BATCH  = os.path.join(HERE, "..", "pipeline", "architecture-batch.json")
RENDERS= os.environ.get("STILLGROVE_RENDERS", os.path.expanduser("~/Projects/Stillgrove/renders"))
THUMB_W, JPEG_Q = 480, 72
START, END = "<!--ARCH_SECTION_START-->", "<!--ARCH_SECTION_END-->"

def studio_uri(num, slug):
    path = os.path.join(RENDERS, f"trend-{num}-{slug}-studio.png")
    if os.path.exists(path) and os.path.getsize(path) > 50_000:
        from PIL import Image
        im = Image.open(path).convert("RGB")
        w, h = im.size
        if w > THUMB_W:
            im = im.resize((THUMB_W, round(h*THUMB_W/w)), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=JPEG_Q, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), True
    # placeholder tile (renders pending)
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='480' height='600'>"
           "<rect width='100%' height='100%' fill='#e9e6df'/>"
           "<rect x='0' y='0' width='100%' height='100%' fill='none' stroke='#cfc8ba' stroke-width='2'/>"
           "<text x='50%' y='47%' fill='#8a8475' font-family='Georgia,serif' font-size='22' "
           "text-anchor='middle'>STILLGROVE</text>"
           "<text x='50%' y='54%' fill='#a59c8c' font-family='Georgia,serif' font-size='15' "
           "text-anchor='middle'>render pending</text></svg>")
    return "data:image/svg+xml," + urllib.parse.quote(svg), False

def esc(s): return html.escape(str(s), quote=True)

def card_html(r):
    src, real = studio_uri(r["num"], r["slug"])
    p = r["photo"]
    name = esc(f'{r["title"]} {r["building"]} {r["dna"]}'.lower())
    if p.get("img"):
        insp = (f'<div class="insp"><img src="{esc(p["img"])}" alt="{esc(p["alt"])}" loading="lazy" '
                f'referrerpolicy="no-referrer" onerror="this.closest(\'.insp\').classList.add(\'noimg\')">'
                f'<div class="inspcap"><span class="ilbl">Inspiration · the building</span>{esc(r["buildingShort"])}'
                f'<a href="{esc(p["page"])}" target="_blank">photo: {esc(p["credit"])}</a></div></div>')
    else:
        insp = '<div class="insp noimg-note">Inspiration: abstract architecture</div>'
    return (
        f'<article class="card" data-cat="Architecture" data-name="{name}" data-price="{r["price"]}" data-num="{r["num"]}">\n'
        f'      <div class="imgwrap">\n'
        f'          <img class="ph studio" src="{src}" alt="{esc(r["title"])} studio" loading="lazy">\n'
        f'        </div>\n'
        f'      <div class="body">\n'
        f'        <div class="hdr"><span class="num">{r["num"]:02d}</span><h3>{esc(r["title"])}</h3></div>\n'
        f'        <div class="price">{esc(r["band"])} <span class="margin">· {esc(r["margin"])}</span></div>\n'
        f'        <div class="from"><span class="lbl">Based on</span> {esc(r["building"])}</div>\n'
        f'        <div class="tags"><span class="src">Abstract architecture</span><span class="cat">Architecture</span></div>\n'
        f'        <details>\n          <summary>Design details</summary>\n          {insp}\n'
        f'          <p><b>Design DNA borrowed:</b> {esc(r["dna"])}</p>\n'
        f'          <p><b>STILLGROVE piece:</b> {esc(r["piece"])}</p>\n'
        f'          <p><b>Materials:</b> {esc(r["materials"])}</p>\n'
        f'          <p><b>Size:</b> {esc(r["size"])}</p>\n'
        f'        </details>\n      </div>\n    </article>'
    )

def main():
    recs = json.load(open(BATCH, encoding="utf-8"))
    html_doc = open(INDEX, encoding="utf-8").read()
    if not os.path.exists(INDEX + ".bak"):
        open(INDEX + ".bak", "w", encoding="utf-8").write(html_doc)

    real = sum(1 for r in recs if studio_uri(r["num"], r["slug"])[1])
    block = START + "\n" + "".join(card_html(r) for r in recs) + "\n" + END

    if START in html_doc and END in html_doc:
        html_doc = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, html_doc, flags=re.S)
    else:
        di = html_doc.find('<section id="detail"')
        gi = html_doc.rfind("</div>", 0, di)            # grid-closing </div>
        html_doc = html_doc[:gi] + block + "\n" + html_doc[gi:]

    # add the Architecture category filter button (after "All"), once
    if 'data-cat="Architecture"' not in re.sub(re.escape(START)+r".*?"+re.escape(END), "", html_doc, flags=re.S):
        html_doc = html_doc.replace(
            '<button class="catbtn on" data-cat="All">All</button>',
            '<button class="catbtn on" data-cat="All">All</button><button class="catbtn" data-cat="Architecture">Architecture</button>',
            1)

    open(INDEX, "w", encoding="utf-8").write(html_doc)
    print(f"inserted/refreshed {len(recs)} Architecture cards ({real} with real renders, {len(recs)-real} placeholders).")

if __name__ == "__main__":
    main()
