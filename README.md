# Blog

Quarto website for the pivotools blog.

## Rendering

Posts are **notebooks** (e.g. `posts/agentic_coding_arc_agi/index.ipynb`). You must pass **`--execute`** when rendering so that notebook cells are run; otherwise Quarto does not execute them by default.

The project also uses **freeze** for posts (`posts/_metadata.yml`): during a **global** project render (`quarto render .`), code in posts is not re-executed—cached output in `_freeze/` is reused. **`--execute` does not override freeze**: a full `quarto render . --execute` still uses the frozen cache for posts, so the HTML will not reflect changes to code or data unless you do one of the following.

### Single command from project root that always runs the post

From the **blog** directory, render the post by path (incremental render). This always executes code and ignores freeze:

```bash
quarto render posts/agentic_coding_arc_agi/index.ipynb --execute
```

Use this when you’ve changed the notebook, `src/`, or `data/` and want updated HTML for that post.

### Full site render (all pages, may use frozen cache)

To build the whole site (e.g. before publishing):

```bash
quarto render . --execute
```

With freeze enabled, posts still use `_freeze/` and do not re-run. There is **no** `--no-freeze` CLI option in Quarto.

### Full site render with fresh execution (override freeze)

To force all posts to re-execute from the project root in one go, clear the freeze cache and then render:

```bash
rm -rf _freeze && quarto render . --execute
```

This is the single command that bypasses the frozen cache for a full site build.

### Presentation (reveal.js slides)

The `agentic_coding_arc_agi` post has a companion slide deck at
`posts/agentic_coding_arc_agi/presentation.qmd`.  
It **executes Python** cells when rendered — the cells generate interactive Plotly
sidecar files and static preview PNGs on the fly. Always pass `--execute`:

```bash
quarto render posts/agentic_coding_arc_agi/presentation.qmd --execute --to revealjs
# or for live reload during editing:
quarto preview posts/agentic_coding_arc_agi/presentation.qmd --execute --to revealjs
```

All rendered artifacts land in **`posts/agentic_coding_arc_agi/presentation-html/`**
(configured via `posts/agentic_coding_arc_agi/_quarto.yml`, `project.output-dir`):

| Artifact | Description |
|---|---|
| `presentation.html` | The slide deck — open in any browser |
| `presentation_files/` | Reveal.js runtime (CSS, JS) copied by Quarto |
| `*-interactive.html` | Standalone Plotly HTML files (one per interactive figure) |
| `plotly.min.js` | Local Plotly bundle (served next to sidecar files) |
| `img/*-preview.png` | Static preview thumbnails (click-target on slides) |

Everything in `presentation-html/` is git-ignored. Press `?` in the browser to see
Reveal.js keyboard shortcuts.

#### Interactive figures — GLightbox + Plotly sidecar pattern

Interactive Plotly figures are surfaced via **GLightbox** (bundled by Quarto): a
static preview PNG sits on the slide and, when clicked, opens a GLightbox overlay
containing a full-viewport iframe with the interactive HTML figure.

**How it works end-to-end:**

1. **Python cell** calls `write_plotly_for_glightbox()` from `src/plotting.py`.  
   This writes two files into `presentation-html/`:
   - `<name>-interactive.html` — self-contained Plotly page (uses a local
     `plotly.min.js` instead of CDN to avoid integrity-check failures inside iframes).
     A `window.Reveal` stub is injected into `<head>` so that Quarto's hot-reload
     script (`quarto-preview.js`) does not crash inside the iframe context.
   - `img/<name>-preview.png` — static thumbnail exported via Kaleido.

2. **`{=html}` raw block** in the slide creates the clickable link:

   ```html
   <a href="<name>-interactive.html"
      class="lightbox"
      data-type="external"
      data-width="90vw"
      data-height="85vh"
      data-description="Optional caption shown below the iframe">
     <img src="img/<name>-preview.png" class="r-stretch" />
   </a>
   ```

   `class="lightbox"` activates GLightbox. `data-type="external"` tells GLightbox
   to render the target URL in an iframe rather than as an image.

3. **SCSS fix** in `presentation-theme.scss` corrects a GLightbox layout bug: when
   `data-description` is present, GLightbox's own CSS gives `.gslide-description`
   `flex: 1 0 100%` (basis 100%, no shrink), which collapses the iframe to zero
   height. The fix sets `flex: 0 0 auto !important` on the description and
   `flex: 1 1 0% !important` on `.gslide-media` so the iframe fills the remaining
   space.

**Adding a new interactive figure to the presentation:**

```python
from src.plotting import write_plotly_for_glightbox

_out = blog_root / "posts/agentic_coding_arc_agi/presentation-html"
write_plotly_for_glightbox(
    my_fig,                                     # any go.Figure
    _out / "my-figure-interactive.html",
    fig_key="my_figure",                        # key in style/style.yml (or any string)
    preview_png_path=_out / "img" / "my-figure-preview.png",
    caption="Optional caption",                 # shown in lightbox; omit if not needed
)
```

Then add a `{=html}` block on the slide (copy the anchor pattern above, substituting
`my-figure` for `<name>`).

**Dependencies:**
- `plotly` — figure creation and HTML export.
- `kaleido` — static PNG export (`pip install kaleido`). Required for preview thumbnails.
- GLightbox CSS/JS are bundled by Quarto automatically when any element has
  `class="lightbox"`.

## Preventing committed notebook output

To avoid committing cell outputs and execution metadata in `.ipynb` files, use a **pre-commit hook** that strips output from staged notebooks before each commit. The hook lives in the **repository root** (the repo that contains `blog/`), not inside `blog/`:

- **Path:** `.git/hooks/pre-commit` (at the repo root)
- **Make it executable:** `chmod +x .git/hooks/pre-commit`

The script below uses `jupyter nbconvert --clear-output` on every staged `.ipynb` file. If, after clearing output, there are no remaining changes to commit, the hook exits with failure so the commit is aborted.

```sh
# Source - https://stackoverflow.com/a/74753885
# Posted by Simon Hyll, modified by community. See post 'Timeline' for change history
# Retrieved 2026-01-30, License - CC BY-SA 4.0
# Use case/esac (POSIX) so the hook works when Git runs it with sh (e.g. in containers).

#!/bin/sh
for f in $(git diff --name-only --cached); do
    case "$f" in
        *.ipynb)
            jupyter nbconvert --clear-output --inplace "$f"
            git add "$f"
            ;;
    esac
done

if git diff --name-only --cached --exit-code
then
    echo "No changes detected after removing notebook output"
    exit 1
fi
```

Requires `jupyter`/`nbconvert` to be available (`pip install nbconvert`).

## Project layout

- **`src/`** – Python helpers used by posts (`plotting.py`, `data.py`).
- **`data/`** – Data files (e.g. puzzle JSON, solution scripts) under `blog/data/`.
- **`posts/*/index.{qmd,ipynb,md}`** – Only these index files are rendered as posts (see `_quarto.yml`).
- **`_output/`** – Rendered site (e.g. for GitHub Pages).
- **`_freeze/`** – Cached execution results for frozen posts; safe to delete to force re-execution.

Execution directory is the blog root (`execute-dir: project`), so paths like `data/` and `src/` resolve from the blog directory.

## Python dependencies

The blog uses Python for `src/` helpers (plotting, data loading, references conversion) and for executing notebook cells. Install dependencies into a virtual environment so Quarto uses them when rendering.

**Create and use a venv (from the blog directory):**

```bash
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Then render as usual (e.g. `quarto render posts/agentic_coding_arc_agi/index.ipynb --execute`). If Quarto was started from a terminal that has the venv activated, it will use that Python and the installed packages.

**Optional:** For the pre-commit hook that clears notebook output, install `nbconvert` in the same venv: `pip install nbconvert`.

**What’s in `requirements.txt`:** `jupyter` (running notebook cells when Quarto executes), `numpy` (for plotly express), `plotly` (figures), `IPython` (HTML display in notebooks), `pygments` (syntax highlighting of solution code), `PyYAML` (reading `style/style.yml`).

## References (citations)

Some posts use Quarto’s built-in bibliography (BibTeX + CSL) so in-text citations and the reference list are numbered and hyperlinked.

For the **agentic_coding_arc_agi** post:

- **Source of truth:** `posts/agentic_coding_arc_agi/text/80_references.md` — one line per reference in the form `[N] [Title](url)`.
- **Generated file:** `posts/agentic_coding_arc_agi/text/references.bib` — used by Quarto at render time. Do not edit by hand; regenerate it from the markdown file.
- **Conversion script:** From the **blog** directory, run:
  ```bash
  python src/md_to_bib.py
  ```
  This reads `posts/agentic_coding_arc_agi/text/80_references.md` and writes `posts/agentic_coding_arc_agi/text/references.bib`. Optional args: `python src/md_to_bib.py [input.md] [output.bib]`.

**When to regenerate:** After adding, removing, or changing entries in `80_references.md`, run `python src/md_to_bib.py` and commit the updated `references.bib`.

**In-text citations:** In the post’s `text/*.md` files, references use Pandoc syntax: `[@ref1]` for a single citation and `[@ref6; @ref7]` for multiple. The notebook YAML points to `text/references.bib` and `../../style/ieee.csl` and enables `link-citations` and `link-bibliography`.

## Link previews (Open Graph)

When you share a post URL (e.g. on Slack, Twitter/X, LinkedIn), the link preview (image, title, description) is driven by **Open Graph** and **Twitter Card** meta tags. The site is configured in `_quarto.yml` with `website.open-graph` and `website.twitter-card` so that Quarto emits these tags.

### Per-post setup

In each post’s front matter (e.g. the first cell of `index.ipynb`), add an **`open-graph`** block so that post gets a custom preview:

- **`open-graph.image`** — Preview image. Use a **relative path** (e.g. `image-preview.png`); Quarto resolves it to an absolute URL using `site-url`. Prefer an image sized for social (e.g. 1200×630 or a 50% resize) so validators don’t complain about size.
- **`open-graph.description`** — Description for the preview. Recommended **155–200 characters** so validators and platforms show a full snippet.
- **Title** — The page `title` is used for the preview. Recommended **60–95 characters** for better visibility in search and shares.

You do **not** need Twitter-specific fields in the post; the site-level `twitter-card` uses the same title, description, and image.

### `og:url` (canonical URL)

Quarto does **not** emit the `og:url` meta tag. Some validators (e.g. ogpreview.io) expect it. To satisfy them, add it manually per post via **`include-in-header`** in the post’s `format.html`:

```yaml
format:
  html:
    # ... other options (code-overflow, etc.) ...
    include-in-header:
      text: "<meta property=\"og:url\" content=\"https://pivotools.github.io/pivotools-quarto-blog/posts/your_post_slug/\">"
```

Use the post’s canonical URL (with trailing slash). Repeat for each post where you want `og:url` set.

**`og:type`** — Quarto does not emit `og:type`. For blog posts, add `article` in the same `include-in-header` block so validators and platforms know the content type:

```yaml
text: "<meta property=\"og:url\" content=\"https://...\">\n<meta property=\"og:type\" content=\"article\">"
```

### Checking previews without a Twitter account

- **[OGPreview.io](https://ogpreview.io/)** — Paste the post URL to see previews for Twitter/X, Facebook, LinkedIn, Slack, Discord.
- **[Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/)** — No login required; uses the same Open Graph tags and gives a good indication of how the link will look when shared.

## Analytics (Plausible)

[Plausible Analytics](https://plausible.io) is included for privacy-friendly, lightweight analytics. The snippet is in **`plausible.html`** and injected into every page via **`_quarto.yml`** → `format.html.include-in-header` (see [Plausible integration guides](https://plausible.io/docs/integration-guides)).

### How it fits this repo

- **Build:** Quarto renders static HTML into `_output/`. The Plausible script is part of each page’s `<head>`.
- **Deploy:** Whatever publishes `_output/` (e.g. GitHub Actions copying to `gh-pages` or into the branch that GitHub Pages serves) will serve the script; no extra step.
- **Domain in Plausible:** The site is a **GitHub project page** at `https://pivotools.github.io/pivotools-quarto-blog/`. In Plausible you add the **hostname** only: **`pivotools.github.io`**. Paths like `/pivotools-quarto-blog/` and `/pivotools-quarto-blog/posts/...` are tracked automatically as page paths.

### Redirect (`pivotools.github.io` → project page)

If you have a redirect from `pivotools.github.io` to `pivotools.github.io/pivotools-quarto-blog`, traffic can arrive via either URL. Plausible still sees the same hostname (`pivotools.github.io`) and full path, so you get one site in the dashboard. If the redirect is external (e.g. different host), add that host as an extra domain in Plausible if you want it tracked under the same or a separate site.

### Caveats

- **Adblockers:** The script is loaded from `plausible.io` (third-party). Some adblockers block it; counts can be lower than “true” traffic. For first-party hosting to reduce blocking, see [Plausible: Run as first-party connection](https://plausible.io/docs/proxy/introduction).
- **Verification:** After deploy, open the live site → View Page Source → search for `plausible.init`. If it’s there, the snippet is active. In the Plausible dashboard, use their “Check if Plausible is installed correctly” / test visit tool to confirm events are received.
- **SPA / hash routing:** This blog is multi-page (full reloads). If you ever use hash-based routing, you’d need `plausible.init({ hashBasedRouting: true })` in `plausible.html`; not needed for the current setup.

## Styling options

Styling is split into (1) Quarto project and document YAML and (2) programmatic figure styling in YAML.

**1. Quarto project and document (header YAML)**  
- **Project:** `_quarto.yml` — site title, navbar, output dir, which files are rendered, and default HTML format (e.g. `format.html.theme`, `format.html.css`).  
- **Document:** Each post’s `index.ipynb` or `index.qmd` has a YAML header — title, subtitle, format overrides, bibliography, and options like `fig-align` or `code-fold`.  
- **Theme CSS:** `styles.css` is included via `_quarto.yml` (`format.html.css`) and affects layout, fonts, and figure/caption styling site-wide.

**2. Programmatic figures (style YAML)**  
- **File:** `style/style.yml` — loaded by `src/plotting.py` and used for all figures generated in code (e.g. baseline-vs-interleaved scatter and bar charts, puzzle heatmaps).  
- **Contents:**  
  - `code_highlight` — Pygments style for solution code in puzzle figures.  
  - `colors` — ARC puzzle heatmap palette and palette name.  
  - `figures.baseline_vs_interleaved` — shared colors and shapes for figures that use `data/baseline_vs_interleaved.json` (scatter and bar).  
  - `figures.scatter_baseline_vs_interleaved` — axis ranges, marker size, arrow and layout for the cost–score scatter.  
  - `figures.bar_baseline_vs_interleaved` — axis, series names, and layout for the bar figure.  
- Changing colors (e.g. `figures.baseline_vs_interleaved.colors.baseline`) or shapes in `style/style.yml` updates the programmatic figures without editing Python.

## Building from scratch (files required)

To generate the site or a post from a fresh clone, the following files are required. Paths are relative to the **blog** directory.

### Project-level (blog root)

| File | Purpose |
|------|---------|
| `_quarto.yml` | Project config, render list, format |
| `styles.css` | HTML theme CSS |
| `src/plotting.py` | Used by notebook cells (e.g. `show_puzzle`) |
| `src/md_to_bib.py` | Script to generate `references.bib` from `80_references.md` (see References) |
| `data/puzzles/9aaea919.json`, `45a5af55.json`, `45a5af55.py` | Puzzle data for figures in agentic_coding_arc_agi post |
| `data/interleaved_thinking_gpt_oss_num_tool_calls.json` | Data for tool-calls histogram in agentic_coding_arc_agi post |
| `style/ieee.csl` | Citation style (numbered refs); notebook uses `../../style/ieee.csl` |

Optional: `style/style.yml` (see [Styling options](#styling-options)).

### Post-specific: agentic_coding_arc_agi

Run from blog root: `quarto render posts/agentic_coding_arc_agi/index.ipynb --execute`.

| File | Purpose |
|------|---------|
| `posts/agentic_coding_arc_agi/index.ipynb` | Notebook (YAML, includes, code cells) |
| `posts/agentic_coding_arc_agi/text/00_overview.md` … `08_acknowledgements.md` | Included content |
| `posts/agentic_coding_arc_agi/text/80_references.md` | Source of truth for references |
| `posts/agentic_coding_arc_agi/text/references.bib` | Generated from 80_references.md (run `python src/md_to_bib.py`) |
| `posts/agentic_coding_arc_agi/text/90_appendix.md` | Appendix content |
| `posts/agentic_coding_arc_agi/figs/interleaved_thinking_schematic.svg` | Figure (from 03_interleaved_thinking.md) |
| `posts/agentic_coding_arc_agi/figs/interleaved_thinking_examples.svg` | Figure (from 03_interleaved_thinking.md) |

### Git: add these for a full from-scratch build

Ensure these are tracked so a fresh clone can build without extra steps:

- `src/md_to_bib.py` — so `references.bib` can be regenerated from `80_references.md`.
- `posts/agentic_coding_arc_agi/text/08_acknowledgements.md` — acknowledgements section.
- `style/ieee.csl` — required for citation rendering.
- Optionally `posts/agentic_coding_arc_agi/text/references.bib` — so the post builds without running the conversion script.
