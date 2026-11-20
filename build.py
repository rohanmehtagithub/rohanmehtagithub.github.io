#!/usr/bin/env python3
"""Regenerate the site in each font variant.

Edit CONTENT (and TEMPLATE) here, then run `python3 build.py`. Every variant page
is rewritten from the same source, so the versions can never drift apart.

Fonts are subset from the local TeX Live OTF originals and written as woff2 into
static/fonts/<slug>/. All of them are OFL-licensed, so shipping them is fine.
"""
import datetime, hashlib, html as htmllib, json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TL   = "/usr/local/texlive/2022/texmf-dist/fonts/opentype/public"
CMU, LM, NCM = f"{TL}/cm-unicode", f"{TL}/lm", f"{TL}/newcomputermodern"

# Which variant is served as index.html.
# "hybrid": title on its own line, then authors and venue flowing from line two.
# "block":  title, authors, venue each on their own line.
# "inline": everything in one paragraph.
LAYOUT = "hybrid"
DEFAULT = "bright"
# Set False before deploying to drop the "view in" comparison strip.
SHOW_SWITCHER = False

UNICODES = ("U+0000-00FF,U+0100-017F,U+0180-024F,U+0300-036F,U+0370-03FF,"
            "U+2000-206F,U+2070-209F,U+20A0-20BF,U+2100-214F,U+2190-21FF,"
            "U+2200-22FF,U+25A0-25FF,U+FB00-FB06")
FEATURES = "kern,liga,dlig,frac,onum,tnum,ccmp,locl,mark,mkmk"

# slug -> (menu label, CSS family name, page-title suffix, sans?, faces)
# faces: (weight, style, source .otf). A missing 700 face means the browser
# synthesises bold; Dunhill has no bold cut at all.
VARIANTS = {
    "bright": ("Bright", "CMU Bright", "CMU Bright SemiBold", True, [
        # CMU Bright Roman is a light sans and reads too thin on screen, so the
        # whole family is shifted up one step: SemiBold carries the body text and
        # Bold Extended is the bold.
        (400, "normal", f"{CMU}/cmunbsr.otf"),
        (400, "italic", f"{CMU}/cmunbso.otf"),
        (700, "normal", f"{CMU}/cmunbbx.otf"),
        (700, "italic", f"{CMU}/cmunbxo.otf")]),
}

# Per-variant optical tuning. CMU Bright is a sans and runs small, Dunhill's
# stretched ascenders need more leading, Concrete is wide and heavy.
# "stroke" adds a synthetic outline in the text colour. CMU Concrete has no
# weight between Roman and Bold Extended, so a fraction of a pixel is the only
# way to firm it up without jumping a whole step.
TUNING = {
    "bright":   {"body": "17px",   "name": "32px", "line": "1.44", "stroke": "0"},
}

NAME  = "Rohan Mehta"
# Written out rather than a mailto: link, which keeps address scrapers off it.
EMAIL = ('rohanmehta@g<span class="dot">[dot]</span>harvard'
         '<span class="dot">[dot]</span>edu')
BIO = ('I am a PhD student at Harvard University, where I am advised by '
       '<a href="https://lukin.physics.harvard.edu/" target="_blank" rel="noopener">Mikhail Lukin</a>. '
       'I work in quantum error correction and am broadly interested in developing useful '
       'quantum computers. Previously, I completed my undergraduate degree at the University of '
       'Chicago, where I was advised by '
       '<a href="https://pme.uchicago.edu/directory/liang-jiang" target="_blank" rel="noopener">Liang Jiang</a>.')
# Search-result snippet and link-preview text. Kept under 160 characters so
# Google shows it whole; it names the field and the group, which is what a
# search for a common name needs to land here.
DESCRIPTION = ("Rohan Mehta, PhD student at Harvard University advised by Mikhail Lukin. "
               "Quantum error correction, quantum LDPC codes, magic state factories, "
               "fault tolerance.")
# Browser-tab and search-result title. The heading on the page stays the bare
# name; the suffix tells a search engine which Rohan Mehta this is.
PAGE_TITLE = f"{NAME} – Quantum Error Correction, Harvard University"
SITE_URL = "https://rohanmehtagithub.github.io/"
# Topics listed in the structured data and on the link-preview card.
TOPICS = ["Quantum error correction", "Quantum LDPC codes",
          "Fault-tolerant quantum computation", "Magic state distillation"]

# Publications in CHRONOLOGICAL order, oldest first. The page renders them
# reversed, so newest appears at the top. Add new papers to the bottom.
# Each entry: (authors_html, title, href, venue_html, note_or_None)
PUBS = [
 ('<strong>R.M.</strong>, Gideon Lee, Liang Jiang',
  'Analysis and Suppression of Errors in Quantum Random Access Memory under Extended Noise Models.',
  'https://arxiv.org/abs/2412.10318',
  'arXiv:2412.10318, 2024.', None),
 ('Varun Menon,* J. Pablo Bonilla Ataides,* <strong>R.M.</strong>, Andi Gu, Daniel Bochen Tan, '
  'Mikhail D. Lukin',
  'Magic Tricycles: Efficient Magic-State Generation with Finite Block-Length Quantum LDPC Codes.',
  'https://doi.org/10.1103/ghhp-cytl',
  '<em>Physical Review X</em>, vol. 16, no. 2, 2026.', '[QEC 26 Talk] [TQC 26 Talk]'),
 ('Xiao Xiao, Dominik Hangleiter, J. Pablo Bonilla Ataides, <strong>R.M.</strong>, Varun Menon, '
  'Mikhail D. Lukin, Michael J. Gullans',
  'Efficient Fidelity Simulation of High-Rate Magic Distillation Circuits.',
  'https://arxiv.org/abs/2610.03605',
  'arXiv:2610.03605, 2026.', None),
 ('<strong>R.M.</strong>, Varun Menon, Hengyun Zhou, Mikhail D. Lukin, J. Pablo Bonilla Ataides',
  'The Practical Cost of Magic State Cultivation.',
  'https://arxiv.org/abs/2610.06828',
  'arXiv:2610.06828, 2026.', None),
 ('Nishad Maskara, <strong>R.M.</strong>, Zhiyang He, Varun Menon, J. Pablo Bonilla Ataides, '
  'Mikhail D. Lukin, Hengyun Zhou',
  'Efficient Logic with Ultra-High-Rate Quantum Codes.',
  'https://arxiv.org/abs/2610.06749',
  'arXiv:2610.06749, 2026.', None),
 ('Varun Menon,* <strong>R.M.,*</strong> Andi Gu, Andrei C. Diaconu, Daniel Bochen Tan, Xiao Xiao, '
  'Michael J. Gullans, Qian Xu, Hengyun Zhou, Mikhail D. Lukin, J. Pablo Bonilla Ataides',
  'Single-Shot Magic State Factories for Quantum LDPC Codes.',
  'https://arxiv.org/abs/2610.10731',
  'arXiv:2610.10731, 2026.', None),
]


# Talks in CHRONOLOGICAL order, oldest first, like PUBS. The page reverses them.
# Each entry: (title, venue_html, optional note such as '[Invited]')
TALKS = [
 ('Dynamically Generated Logical Gates.',
  'QI Group Meeting, MIT. January 2025.', '[Invited]'),
 ('Efficient Magic State Generation with Tricycle Codes.',
  'TQC 2026, Sherbrooke, Canada.'),
 ('Single-Shot Magic State Factories for Quantum LDPC Codes.',
  'PsiQuantum / University of Sydney Fault-Tolerance Seminar. November 1, 2026.', '[Invited]'),
]



def vhash(path):
    """Short content hash, appended to asset URLs so a changed file can never be
    served from a stale browser cache. Browsers cache CSS heuristically when the
    server sends no Cache-Control header, which silently hides edits."""
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()[:8]


def subset_fonts(slug, faces):
    outdir = os.path.join(ROOT, "static", "fonts", slug)
    os.makedirs(outdir, exist_ok=True)
    made = []
    for weight, style, src in faces:
        if not os.path.exists(src):
            sys.exit(f"missing font source: {src}")
        out = os.path.join(outdir, f"{weight}-{style}.woff2")
        subprocess.run([
            "pyftsubset", src, f"--output-file={out}", "--flavor=woff2",
            f"--unicodes={UNICODES}", f"--layout-features={FEATURES}",
            "--name-IDs=*", "--no-hinting", "--desubroutinize",
        ], check=True, capture_output=True)
        made.append((weight, style, out))
    return made


def write_font_css(slug, family, is_sans, made):
    t = TUNING[slug]
    stack = f"'{family}', " + ("sans-serif" if is_sans else
                               "Georgia, 'Times New Roman', serif")
    css = [f"/* {family} - generated by build.py, do not edit by hand */"]
    cssdir = os.path.join(ROOT, "static", "fonts")
    for weight, style, path in made:
        # URLs in a stylesheet resolve relative to the stylesheet, not the page.
        rel = os.path.relpath(path, cssdir)
        css.append("@font-face {\n"
                   f"  font-family: '{family}';\n"
                   f"  src: url('{rel}') format('woff2');\n"
                   f"  font-weight: {weight}; font-style: {style}; font-display: swap;\n"
                   "}")
    css.append(":root {\n"
               f"  --body-font: {stack};\n"
               f"  --body-size: {t['body']};\n"
               f"  --name-size: {t['name']};\n"
               f"  --line: {t['line']};\n"
               f"  --text-stroke: {t['stroke']};\n"
               "}")
    out = os.path.join(ROOT, "static", "fonts", f"{slug}.css")
    open(out, "w").write("\n".join(css) + "\n")
    return out


def plain(fragment):
    """Author or venue HTML reduced to text: tags gone, entities decoded."""
    return htmllib.unescape(re.sub(r"<[^>]+>", "", fragment))


def author_names(authors_html):
    """Full names from an authors fragment, R.M. expanded, asterisks dropped."""
    text = plain(authors_html).replace("R.M.", NAME)
    names = [n.replace("*", "").strip() for n in text.split(",")]
    return [n for n in names if n and n not in ("\u2026", "...")]


PERSON_ID = SITE_URL + "#person"


def pub_jsonld(authors, title, href, venue, note):
    """One schema.org ScholarlyArticle for a PUBS entry."""
    v = plain(venue)
    item = {"@type": "ScholarlyArticle", "headline": title.rstrip("."),
            "author": [{"@id": PERSON_ID, "@type": "Person", "name": NAME} if n == NAME
                       else {"@type": "Person", "name": n} for n in author_names(authors)]}
    if href:
        item["url"] = href
    year = re.search(r"\b(?:19|20)\d{2}\b", v)
    if year:
        item["datePublished"] = year.group(0)
    arxiv = re.search(r"arXiv:(\d{4}\.\d{4,5})", v)
    if arxiv:
        item["identifier"] = f"arXiv:{arxiv.group(1)}"
        item["sameAs"] = f"https://arxiv.org/abs/{arxiv.group(1)}"
    doi = re.search(r"doi\.org/(.+)$", href or "")
    if doi:
        item["identifier"] = f"doi:{doi.group(1)}"
        item["sameAs"] = href
    journal = re.search(r"<em>(.*?)</em>", venue)
    if journal:
        item["isPartOf"] = {"@type": "Periodical", "name": plain(journal.group(1))}
    return item


def jsonld(og_url):
    """schema.org graph: the profile page, the person, and every paper. Search
    engines use it to tell this Rohan Mehta apart from the others and to attach
    the papers to him. Rendered inside a <script> so '</' must be escaped."""
    person = {
        "@type": "Person", "@id": PERSON_ID, "name": NAME,
        "givenName": "Rohan", "familyName": "Mehta",
        "url": SITE_URL, "image": og_url, "jobTitle": "PhD student",
        "description": DESCRIPTION,
        "affiliation": {"@type": "CollegeOrUniversity", "name": "Harvard University",
                        "url": "https://www.harvard.edu/"},
        "alumniOf": {"@type": "CollegeOrUniversity", "name": "University of Chicago",
                     "url": "https://www.uchicago.edu/"},
        "knowsAbout": TOPICS,
    }
    page = {"@type": "ProfilePage", "@id": SITE_URL, "url": SITE_URL,
            "name": PAGE_TITLE, "description": DESCRIPTION, "inLanguage": "en",
            "mainEntity": person}
    papers = [pub_jsonld(*p[:5]) for p in reversed(PUBS)]
    graph = {"@context": "https://schema.org", "@graph": [page] + papers}
    return json.dumps(graph, ensure_ascii=False, indent=2).replace("</", "<\\/")


def make_og_image():
    """1200x630 card shown when the link is pasted into Slack, iMessage, X and
    the like. Drawn from the same CMU Bright face and the favicon's matrix cells
    so it matches the page. Output is deterministic, so the committed PNG only
    changes when this function or the icon does."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  Pillow missing, kept existing og-image.png")
        return
    W, H, M = 1200, 630, 96
    img = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(img)
    face = f"{CMU}/cmunbsr.otf"
    name_f, sub_f, url_f = (ImageFont.truetype(face, n) for n in (104, 40, 32))
    # Matrix mark at top right, as in the page header.
    svg = open(os.path.join(ROOT, "static", "favicon.svg"), encoding="utf-8").read()
    cells = re.findall(r'<rect x="(\d+)" y="(\d+)" width="10" height="10" fill="(#[0-9a-fA-F]{6})"', svg)
    # Text block sits a little above centre, URL alone at the bottom.
    base = 262
    size = 200
    sc = size / 64
    # The mark's top lines up with the cap height of the name (about 0.7 em).
    x0, y0 = W - M - size + 10 * sc, base - 0.7 * 104 - 10 * sc
    for x, y, fill in cells:
        x, y = int(x), int(y)
        d.rectangle([x0 + x * sc, y0 + y * sc, x0 + (x + 10) * sc - 1, y0 + (y + 10) * sc - 1], fill=fill)
    d.text((M, base), NAME, font=name_f, fill="#1a1a1d", anchor="ls")
    d.text((M, base + 78), "PhD student, Harvard University", font=sub_f, fill="#3b3c41", anchor="ls")
    topics = "Quantum error correction  \u00b7  quantum LDPC codes  \u00b7  fault tolerance"
    # Shrink the topics line until it fits inside the margins.
    tf, n = sub_f, 40
    while d.textlength(topics, font=tf) > W - 2 * M and n > 24:
        n -= 1
        tf = ImageFont.truetype(face, n)
    d.text((M, base + 136), topics, font=tf, fill="#3b3c41", anchor="ls")
    d.text((M, H - M), SITE_URL.replace("https://", "").rstrip("/"), font=url_f,
           fill="#0f4a6e", anchor="ls")
    out = os.path.join(ROOT, "static", "og-image.png")
    img.save(out, optimize=True)
    return out


def write_seo_files(page_html):
    """robots.txt and a one-URL sitemap. lastmod moves to today only when the
    rendered page differs from the one on disk, so an unchanged rebuild does not
    pretend the page is new."""
    open(os.path.join(ROOT, "robots.txt"), "w").write(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}sitemap.xml\n")
    index = os.path.join(ROOT, "index.html")
    old = open(index, encoding="utf-8").read() if os.path.exists(index) else ""
    sm = os.path.join(ROOT, "sitemap.xml")
    prev = None
    if os.path.exists(sm):
        prev = re.search(r"<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>", open(sm).read())
    lastmod = (prev.group(1) if prev and old == page_html
               else datetime.date.today().isoformat())
    open(sm, "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url>\n    <loc>{SITE_URL}</loc>\n    <lastmod>{lastmod}</lastmod>\n  </url>\n'
        '</urlset>\n')


def render_page(slug, css_v, font_css_v):
    icon_v = vhash(os.path.join(ROOT, "static", "favicon.svg"))
    og_path = os.path.join(ROOT, "static", "og-image.png")
    og_url = f"{SITE_URL}static/og-image.png?v={vhash(og_path)}"
    desc = htmllib.escape(DESCRIPTION, quote=True)
    ptitle = htmllib.escape(PAGE_TITLE, quote=True)
    ld = jsonld(og_url)
    label, family, title_suffix, is_sans, faces = VARIANTS[slug]
    pubs = []
    for authors, title, href, venue, note, *rest in reversed(PUBS):
        note_html = f' <span class="note">{note}</span>' if note else ""
        eq_text = rest[0] if rest and rest[0] else '* denotes equal contribution.'
        eq = (f'\n            <div class="eq">{eq_text}</div>'
              if '*' in authors else '')
        if LAYOUT == "hybrid":
            t = title.rstrip('.')
            t_html = (f'<a href="{href}" target="_blank" rel="noopener">{t}</a>'
                      if href else t)
            # An author list that trails off in an ellipsis takes no closing period.
            sep = ' ' if authors.rstrip().endswith(('&hellip;', '\u2026')) else '. '
            pubs.append(
                f'          <li>\n'
                f'            <div class="pub-title">{t_html}</div>\n'
                f'            <div class="pub-rest">{authors}{sep}{venue}{note_html}</div>{eq}\n'
                f'          </li>')
        elif LAYOUT == "block":
            # Title leads on its own line, so no quotes and no trailing period.
            t = title.rstrip('.')
            t_html = (f'<a href="{href}" target="_blank" rel="noopener">{t}</a>'
                      if href else t)
            pubs.append(
                f'          <li>\n'
                f'            <div class="pub-title">{t_html}</div>\n'
                f'            <div class="pub-authors">{authors}</div>\n'
                f'            <div class="pub-venue">{venue}{note_html}</div>{eq}\n'
                f'          </li>')
        else:
            t_html = (f'<a href="{href}" target="_blank" rel="noopener">{title}</a>'
                      if href else f'<span class="title">{title}</span>')
            pubs.append(
                f'          <li>\n            &ldquo;{t_html}&rdquo; '
                f'{authors}.\n            {venue}{note_html}{eq}\n          </li>')

    pubs = "\n".join(pubs)

    footnote = ""

    def talk_note(rest):
        return f' <span class="note">{rest[0]}</span>' if rest and rest[0] else ""
    if LAYOUT in ("block", "hybrid"):
        talks = "\n".join(
            f'          <li>\n            <div class="talk-title">{t.rstrip(".")}</div>\n'
            f'            <div class="talk-venue">{v}{talk_note(rest)}</div>\n          </li>'
            for t, v, *rest in reversed(TALKS))
    else:
        talks = "\n".join(
            f'          <li>\n            &ldquo;<span class="title">{t}</span>&rdquo;\n'
            f'            {v}{talk_note(rest)}\n          </li>'
            for t, v, *rest in reversed(TALKS))
    talks_section = ("" if not TALKS else
        '\n      <div class="section-group" id="talks">\n'
        '        <h2>Selected talks</h2>\n'
        '        <ul class="talks">\n' + talks + '\n        </ul>\n'
        '      </div>')

    switcher = ""
    if SHOW_SWITCHER:
        items = []
        for s, (lab, _f, _t, _sans, _fa) in VARIANTS.items():
            page = "index.html" if s == DEFAULT else f"{s}.html"
            cls = ' class="here"' if s == slug else ''
            items.append(f'<a href="{page}"{cls}>{lab}</a>')
        switcher = ('\n    <div class="switcher">\n      <span>view in</span>\n      '
                    + "\n      ".join(items) + "\n    </div>\n")

    preload = f"static/fonts/{slug}/400-normal.woff2"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light only">
  <title>{ptitle}</title>
  <meta name="description" content="{desc}">
  <meta name="author" content="{NAME}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <meta name="theme-color" content="#ffffff">
  <link rel="canonical" href="{SITE_URL}">
  <meta property="og:type" content="profile">
  <meta property="profile:first_name" content="Rohan">
  <meta property="profile:last_name" content="Mehta">
  <meta property="og:title" content="{ptitle}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{SITE_URL}">
  <meta property="og:site_name" content="{NAME}">
  <meta property="og:locale" content="en_US">
  <meta property="og:image" content="{og_url}">
  <meta property="og:image:type" content="image/png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{NAME}, quantum error correction, Harvard University">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{ptitle}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{og_url}">
  <link rel="icon" href="favicon.ico?v={icon_v}" sizes="any">
  <link rel="icon" type="image/svg+xml" href="static/favicon.svg?v={icon_v}">
  <link rel="icon" type="image/png" sizes="32x32" href="static/favicon-32.png?v={icon_v}">
  <link rel="icon" type="image/png" sizes="16x16" href="static/favicon-16.png?v={icon_v}">
  <link rel="apple-touch-icon" sizes="180x180" href="static/apple-touch-icon.png?v={icon_v}">
  <link rel="preload" href="{preload}" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="style.css?v={css_v}">
  <link rel="stylesheet" href="static/fonts/{slug}.css?v={font_css_v}">
  <!-- Typeface: {title_suffix}. Regenerate with: python3 build.py -->
  <!-- Uncomment to render LaTeX in titles:
  <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  -->
  <script type="application/ld+json">
{ld}
  </script>
</head>
<body>
  <div class="container">

    <header>
      <div class="ident">
        <h1 class="name">{NAME}</h1>
        <p class="email">{EMAIL}</p>
      </div>
      <img class="mark" src="static/favicon.svg?v={icon_v}"
           alt="Sparse parity-check matrix" width="64" height="64">
    </header>

    <main>
    <section class="about">
      <p>{BIO}</p>
    </section>

    <section class="content">
      <div class="section-group" id="publications">
        <h2>Publications</h2>
        <ol class="publications">
{pubs}
        </ol>
{footnote}
      </div>
{talks_section}
    </section>
    </main>
{switcher}
  </div>
</body>
</html>
"""


def main():
    # Remove pages for variants that were dropped. Only files carrying the
    # build.py marker are touched, so hand-written files are never deleted.
    keep = {"index.html"} | {f"{s}.html" for s in VARIANTS if s != DEFAULT}
    for entry in sorted(os.listdir(ROOT)):
        # Underscore-prefixed pages are scratch previews, never generated output.
        if not entry.endswith(".html") or entry in keep or entry.startswith("_"):
            continue
        path = os.path.join(ROOT, entry)
        if "Regenerate with: python3 build.py" in open(path, encoding="utf-8").read():
            os.remove(path)
            print(f"  removed dropped page {entry}")

    # Clear out stale generated font dirs.
    fontroot = os.path.join(ROOT, "static", "fonts")
    for entry in os.listdir(fontroot) if os.path.isdir(fontroot) else []:
        p = os.path.join(fontroot, entry)
        stale = (os.path.isdir(p) and entry not in VARIANTS) or \
                (entry.endswith(".woff2") and os.path.isfile(p)) or \
                (entry.endswith(".css") and entry[:-4] not in VARIANTS)
        if stale:
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
            print(f"  removed stale {entry}")

    make_og_image()
    for slug, (label, family, title_suffix, is_sans, faces) in VARIANTS.items():
        made = subset_fonts(slug, faces)
        write_font_css(slug, family, is_sans, made)
        page = "index.html" if slug == DEFAULT else f"{slug}.html"
        html = render_page(slug, vhash(os.path.join(ROOT, "style.css")),
                           vhash(os.path.join(ROOT, "static", "fonts", f"{slug}.css")))
        if slug == DEFAULT:
            write_seo_files(html)
        open(os.path.join(ROOT, page), "w").write(html)
        kb = sum(os.path.getsize(p) for _w, _s, p in made) / 1024
        bold = "synthesised bold" if not any(w == 700 for w, _s, _p in faces) else "4 faces"
        print(f"  {page:<18} {title_suffix:<28} {kb:6.0f} KB  ({bold})")


if __name__ == "__main__":
    main()
