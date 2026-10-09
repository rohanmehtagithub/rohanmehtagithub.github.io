# Research website

Static site, no JavaScript and no dependencies to serve. The same page is generated in two
typefaces so they can be compared side by side.

| Page | Typeface | Fonts |
|---|---|---|
| `index.html` | CMU Bright SemiBold (sans) | 135 KB |
| `concrete.html` | CMU Concrete Roman | 167 KB |

Each page loads only its own fonts, so the byte cost above is per visitor, not cumulative.

## Editing

Both pages are generated from `build.py`. Do not edit the HTML by hand, it will be overwritten.
Change the content there and regenerate:

    python3 build.py

Inside `build.py`:

- `PUBS` is the publication list, one tuple per paper: authors, title, link, venue, optional note.
  Numbering is automatic. Bold your own name with `<strong>`.
- `BIO`, `NAME`, and `EMAIL` are the header and About text.
- `DEFAULT` picks which typeface is served as `index.html`.
- `SHOW_SWITCHER` controls the "view in" strip at the bottom. Set it to `False` before deploying.
- `TUNING` holds per-typeface body size, name size, and line height, since the two fonts do not
  render at the same optical size.

Dropping a variant from `VARIANTS` also deletes its page on the next run. Only files carrying the
build.py marker comment are ever removed, so hand-written files in this directory are safe.

Shared layout lives in `style.css`. Each page loads it first, then `static/fonts/<variant>.css`,
which sets the font family and the size variables. That order matters: the variant stylesheet has
to come second so its values win.

## Fonts

Subset to Latin, Greek, punctuation, and math symbols from the OTF originals in the local TeX Live
install, then converted to woff2 by `build.py` via `pyftsubset`. Both are OFL-licensed, so shipping
them is fine. Sources are in `texmf-dist/fonts/opentype/public/cm-unicode`.

CMU Bright is a light sans by design and its Roman cut reads too thin on a screen. The whole family
is therefore shifted up one step: SemiBold carries the body text and Bold Extended is the bold.
If it still reads light, the alternative is New Computer Modern Sans Book, which is a separate
family in `texmf-dist/fonts/opentype/public/newcomputermodern`.

Regenerating requires `pyftsubset` (from `fonttools`, with `brotli` installed) and a TeX Live
install at the path set in `build.py`. The generated woff2 files are committed, so deploying does
not need either.

## Preview locally

    python3 serve.py

then open http://127.0.0.1:8000. This is the standard library file server with one change: every
response carries `Cache-Control: no-store`, so a plain reload always shows the current files.
Without it, browsers cache HTML, CSS and icons heuristically and edits silently fail to appear.

Serve over HTTP rather than opening the file directly, because browsers block web font loads over
`file://` and you will silently get a fallback serif.

## Deployment

Live at https://rohanmehtagithub.github.io/, served by GitHub Pages from the `main` branch of
`rohanmehtagithub/rohanmehtagithub.github.io`. To publish a change:

    python3 build.py
    git add -A && git commit -m "Describe the change"
    git push

Pages rebuilds within a minute or two. `.nojekyll` stops GitHub from running Jekyll over the tree,
and `.gitignore` keeps the scratch previews and font comparison sheets out of the repository.
`SHOW_SWITCHER` in `build.py` is off for deployment; turn it on locally to compare typefaces.

## Icons

`static/favicon.svg` is a 4x4 sparse parity-check matrix, dark cells against the page background.
PNG fallbacks at 16 and 32 pixels cover browsers that ignore SVG favicons, and
`apple-touch-icon.png` is a squared-off 180 pixel version for the iOS home screen. All four are
rasterised from the same SVG. To change the icon, drop a different file from
`static/favicon-options/` onto `static/favicon.svg` and re-render the PNGs.

## Not part of the site

- `static/favicon-options/` holds 24 rejected icon designs.
- `_favicons.html` previews them at 16, 32 and 64 pixels.
- `_colors.html` compares emphasis colours on real page content.
- `font-specimen.png` compares twelve Computer Modern variants.
- `font-weights.png` compares the sans weight options at body size.
- `favicon-options.png` is a still of the first icon preview.
- `font-demos/` was not created by this build and is left untouched.
