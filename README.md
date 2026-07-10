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
- Research metric cards are manually configured in the `metrics` array in `content/site.json`.

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

## Publication Format

Publications are maintained in `content/publications.json`. Each item is rendered as a structured publication entry with title, authors, venue, citation details, and an optional note.

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
