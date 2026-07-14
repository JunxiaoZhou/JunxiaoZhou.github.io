# Junxiao Zhou Academic Homepage

This repository builds a static GitHub Pages homepage from Markdown content.

## Edit Content

- Site-level metadata lives in `content/site.json`.
- Page modules live in `content/sections/*.md`.
- Files are rendered in filename order, so `01-overview.md` appears before `02-publications.md`.
- To hide a module, add `draft: true` in its front matter.
- The hero background is controlled by `heroBackground` in `content/site.json`.
- Hero background paths should start with `/assets/`, for example `/assets/header-metasurface-bg.jpg`.
- To add a portrait, place the image at `assets/avatar.jpg` and run `make build`.
- Research metric cards are configured in the `metrics` array in `content/site.json`. Static cards use `value`; Scholar-backed cards use `scholarField`.

Example module:

```markdown
---
title: Awards
eyebrow: Recognition
---

### Selected Awards

- Award name, year
```

## Build

Run:

```bash
make build
```

This regenerates `index.html`, which is the file served by GitHub Pages. You can also run `python3 scripts/build.py` directly.

## Google Scholar Metrics

Google Scholar metrics are normalized in `content/scholar.json`. The generated homepage uses this file for the citation and h-index cards. Publication content remains managed separately in `content/publications.json`.

The same Scholar response stores normalized article citation data. During the build, selected publications are matched by normalized title and display `Cited by N` when the count is greater than zero. Other publications remain unchanged apart from year grouping.

The Personal Statement can reuse the same values with `{{ scholar_citations }}` and `{{ scholar_h_index }}` placeholders, keeping its prose synchronized with the metric cards during each build.

To refresh Scholar data locally, set the SerpApi key in the environment and run:

```bash
export SERPAPI_API_KEY="your-key"
make scholar
make build
```

The API key must not be committed to the repository. For the daily GitHub Actions refresh, add it as a repository Actions secret named `SERPAPI_API_KEY`. The workflow can also be started manually from the Actions tab.

If the request fails or SerpApi returns incomplete data, the fetch script exits without replacing the last valid `content/scholar.json` file.

## Publication Format

Publications are maintained in `content/publications.json`. Each item is rendered as a structured publication entry with title, authors, venue, citation details, and an optional note.

Other publications are automatically grouped by the year in the trailing `(YYYY)` portion of each `citation` field. Numeric page ranges are rendered with an en dash.

Markdown syntax can still be used inside text fields for bold author names and italic notes. Wrap contribution symbols in carets so they render as superscripts: `^†^` for equal contribution and `^*^` for corresponding author.

```json
{
  "authors": "First Author^†^, **Junxiao Zhou^†^,^*^**, Corresponding Author^*^",
  "title": "Paper title",
  "venue": "Journal",
  "url": "https://example.com",
  "citation": "**12**, 34-56 (2026)",
  "note": "Optional note"
}
```
