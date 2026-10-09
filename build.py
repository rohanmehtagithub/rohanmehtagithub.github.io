#!/usr/bin/env python3
"""Regenerate the site in each font variant.

Edit CONTENT (and TEMPLATE) here, then run `python3 build.py`. Every variant page
is rewritten from the same source, so the versions can never drift apart.

Fonts are subset from the local TeX Live OTF originals and written as woff2 into
static/fonts/<slug>/. All of them are OFL-licensed, so shipping them is fine.
"""
import hashlib, os, shutil, subprocess, sys

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
DESCRIPTION = ("PhD student at Harvard University working in quantum error correction, "
               "advised by Mikhail Lukin.")

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
# Each entry: (title, venue_html)
TALKS = [
 ('Dynamically Generated Logical Gates.',
  'QI Group Meeting, MIT. January 2025.'),
 ('Efficient Magic State Generation with Tricycle Codes.',
  'TQC 2026, Sherbrooke, Canada.'),
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


def render_page(slug, css_v, font_css_v):
    icon_v = vhash(os.path.join(ROOT, "static", "favicon.svg"))
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

    if LAYOUT in ("block", "hybrid"):
        talks = "\n".join(
            f'          <li>\n            <div class="talk-title">{t.rstrip(".")}</div>\n'
            f'            <div class="talk-venue">{v}</div>\n          </li>'
            for t, v in reversed(TALKS))
    else:
        talks = "\n".join(
            f'          <li>\n            &ldquo;<span class="title">{t}</span>&rdquo;\n'
            f'            {v}\n          </li>'
            for t, v in reversed(TALKS))
    talks_section = ("" if not TALKS else
        '\n      <div class="section-group">\n'
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
  <title>{NAME}</title>
  <meta name="description" content="{DESCRIPTION}">
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

    <section class="about">
      <p>{BIO}</p>
    </section>

    <section class="content">
      <div class="section-group">
        <h2>Publications</h2>
        <ol class="publications">
{pubs}
        </ol>
{footnote}
      </div>
{talks_section}
    </section>
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

    for slug, (label, family, title_suffix, is_sans, faces) in VARIANTS.items():
        made = subset_fonts(slug, faces)
        write_font_css(slug, family, is_sans, made)
        page = "index.html" if slug == DEFAULT else f"{slug}.html"
        open(os.path.join(ROOT, page), "w").write(
            render_page(slug, vhash(os.path.join(ROOT, "style.css")),
                        vhash(os.path.join(ROOT, "static", "fonts", f"{slug}.css"))))
        kb = sum(os.path.getsize(p) for _w, _s, p in made) / 1024
        bold = "synthesised bold" if not any(w == 700 for w, _s, _p in faces) else "4 faces"
        print(f"  {page:<18} {title_suffix:<28} {kb:6.0f} KB  ({bold})")


if __name__ == "__main__":
    main()
