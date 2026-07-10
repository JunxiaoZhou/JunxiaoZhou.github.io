#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content" / "sections"
SITE_FILE = ROOT / "content" / "site.json"
PUBLICATIONS_FILE = ROOT / "content" / "publications.json"
OUTPUT_FILE = ROOT / "index.html"


@dataclass
class Section:
    slug: str
    title: str
    eyebrow: str
    html: str


ICONS = {
    "bar-chart": '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>',
    "book-open": '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3z"/><path d="M21 18a1 1 0 0 0 1-1V5a1 1 0 0 0-1-1h-5a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3z"/></svg>',
    "building-2": '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18"/><path d="M6 12H4a2 2 0 0 0-2 2v8"/><path d="M18 9h2a2 2 0 0 1 2 2v11"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/></svg>',
    "external-link": '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>',
    "file-text": '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>',
    "graduation-cap": '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/></svg>',
    "info": '<svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
    "mail": '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="m22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7"/><rect x="2" y="4" width="20" height="16" rx="2"/></svg>',
    "user-round": '<svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/></svg>',
    "quote": '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M16 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2 1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0 0 2 4 4 0 0 0 4-4V5a2 2 0 0 0-2-2z"/><path d="M7 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2 1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0 0 2 4 4 0 0 0 4-4V5a2 2 0 0 0-2-2z"/></svg>',
    "user-check": '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="m16 11 2 2 4-4"/></svg>',
}


def icon(name: str) -> str:
    return f'<span class="icon">{ICONS[name]}</span>'


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text

    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text

    raw = text[4:end].strip()
    body = text[end + 5 :].lstrip()
    meta: dict[str, str] = {}

    for line in raw.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip("\"'")

    return meta, body


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def render_inline(value: str) -> str:
    placeholders: list[str] = []

    def stash_html(markup: str) -> str:
        placeholders.append(markup)
        return f"\0{len(placeholders) - 1}\0"

    def stash_code(match: re.Match[str]) -> str:
        placeholders.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"\0{len(placeholders) - 1}\0"

    def stash_link(match: re.Match[str]) -> str:
        label = render_inline(match.group(1))
        url = html.escape(match.group(2), quote=True)
        return stash_html(
            f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'
        )

    value = re.sub(r"`([^`]+)`", stash_code, value)
    value = re.sub(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]+\")?\)", stash_link, value)
    value = html.escape(value)
    value = re.sub(
        r"\^([*†‡]+)\^",
        lambda match: stash_html(
            f'<sup class="author-marker">{match.group(1)}</sup>'
        ),
        value,
    )
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", value)

    for index, replacement in enumerate(placeholders):
        value = value.replace(f"\0{index}\0", replacement)

    return value


def flush_paragraph(lines: list[str], output: list[str]) -> None:
    if lines:
        output.append(f"<p>{render_inline(' '.join(lines))}</p>")
        lines.clear()


def render_markdown(markdown: str) -> str:
    output: list[str] = []
    paragraph: list[str] = []
    list_type: str | None = None

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            output.append(f"</{list_type}>")
            list_type = None

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        if not line.strip():
            flush_paragraph(paragraph, output)
            close_list()
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph(paragraph, output)
            close_list()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            output.append(f'<h{level} id="{slugify(text)}">{render_inline(text)}</h{level}>')
            continue

        ordered = re.match(r"^(\d+)\.\s+(.+)$", line)
        unordered = re.match(r"^[-*]\s+(.+)$", line)
        if ordered or unordered:
            flush_paragraph(paragraph, output)
            tag = "ol" if ordered else "ul"
            item = ordered.group(2) if ordered else unordered.group(1)
            if list_type != tag:
                close_list()
                if ordered and ordered.group(1) != "1":
                    output.append(f'<{tag} start="{html.escape(ordered.group(1), quote=True)}">')
                else:
                    output.append(f"<{tag}>")
                list_type = tag
            output.append(f"<li>{render_inline(item)}</li>")
            continue

        close_list()
        paragraph.append(line.strip())

    flush_paragraph(paragraph, output)
    close_list()
    return "\n".join(output)


def load_sections() -> list[Section]:
    sections: list[Section] = []

    for path in sorted(CONTENT_DIR.glob("*.md")):
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        if meta.get("draft", "").lower() == "true":
            continue

        title = meta.get("title") or path.stem
        sections.append(
            Section(
                slug=slugify(title),
                title=title,
                eyebrow=meta.get("eyebrow", ""),
                html=render_markdown(body),
            )
        )

    return sections


def render_metrics(site: dict) -> str:
    metrics = site.get("metrics", [])
    metric_icons = {
        "Peer-reviewed SCI papers": "file-text",
        "First/corresponding author": "user-check",
        "Citations": "quote",
        "h-index": "bar-chart",
    }
    items = []
    for metric in metrics:
        metric_icon = metric_icons.get(metric["label"], "bar-chart")
        items.append(
            '<div class="metric">'
            f'{icon(metric_icon)}'
            f'<span><span class="metric-value">{html.escape(metric["value"])}</span>'
            f'<span class="metric-label">{html.escape(metric["label"])}</span></span>'
            "</div>"
        )
    return "\n".join(items)


def render_links(site: dict) -> str:
    link_icons = {
        "Email": "mail",
        "Google Scholar": "graduation-cap",
        "NJU Profile": "building-2",
        "ORCID": "user-check",
    }
    links = []
    for item in site.get("links", []):
        item_icon = link_icons.get(item["label"], "external-link")
        links.append(
            f'<a class="button" href="{html.escape(item["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{icon(item_icon)}{html.escape(item["label"])}</a>'
        )
    return "\n".join(links)


def render_avatar(site: dict) -> str:
    avatar = site.get("avatarImage", "")
    avatar_path = avatar.lstrip("/")
    if avatar and (ROOT / avatar_path).exists():
        return (
            '<div class="avatar-frame">'
            f'<img src="{html.escape(avatar, quote=True)}" alt="{html.escape(site["name"])} portrait">'
            "</div>"
        )

    initials = "".join(part[0] for part in site["name"].split()[:2]).upper()
    return f'<div class="avatar-frame avatar-placeholder" aria-label="Portrait placeholder">{html.escape(initials)}</div>'


def render_sections(sections: list[Section]) -> str:
    rendered = []
    section_icons = {
        "General Information": "user-round",
        "Publications": "book-open",
    }
    for section in sections:
        eyebrow = f'<p class="eyebrow">{html.escape(section.eyebrow)}</p>' if section.eyebrow else ""
        section_icon = section_icons.get(section.title, "book-open")
        section_html = (
            render_publications()
            if section.title == "Publications" and PUBLICATIONS_FILE.exists()
            else section.html
        )
        rendered.append(
            f"""
<section id="{section.slug}" class="section">
  <div class="section-heading">
    {icon(section_icon)}{eyebrow}
    <h2>{html.escape(section.title)}</h2>
  </div>
  <div class="section-body">
    {section_html}
  </div>
</section>""".strip()
        )
    return "\n\n".join(rendered)


def render_publication_item(item: dict, index: int) -> str:
    note = item.get("note", "")
    note_html = (
        f'<span class="publication-note">{render_inline(note)}</span>'
        if note
        else ""
    )
    return (
        '<li class="publication-item">'
        f'<span class="publication-number">{index}</span>'
        '<div class="publication-content">'
        f'<a class="publication-title" href="{html.escape(item["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{render_inline(item["title"])}</a>'
        f'<div class="publication-authors">{render_inline(item["authors"])}</div>'
        '<div class="publication-meta">'
        f'<a class="publication-venue" href="{html.escape(item["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{render_inline(item["venue"])}</a>'
        f'<span>{render_inline(item["citation"])}</span>'
        f'{note_html}'
        '</div>'
        '</div>'
        '</li>'
    )


def render_publication_group(title: str, items: list[dict], start: int) -> tuple[str, int]:
    rendered_items = []
    number = start
    group_slug = slugify(title)
    for item in items:
        rendered_items.append(render_publication_item(item, number))
        number += 1

    return (
        f'<h3 id="{group_slug}" class="publication-group-heading publication-group-heading--{group_slug}">{html.escape(title)}</h3>\n'
        f'<ol class="publication-list publication-list--{group_slug}" start="{start}">\n'
        + "\n".join(rendered_items)
        + "\n</ol>",
        number,
    )


def render_publications() -> str:
    publications = json.loads(PUBLICATIONS_FILE.read_text(encoding="utf-8"))
    selected_html, next_number = render_publication_group(
        "Selected Publications", publications.get("selected", []), 1
    )
    other_html, _ = render_publication_group(
        "Other Publications", publications.get("other", []), next_number
    )
    return f"{selected_html}\n{other_html}"


def render_page(site: dict, sections: list[Section]) -> str:
    analytics_id = site.get("googleAnalyticsId", "")
    analytics = ""
    if analytics_id:
        safe_id = html.escape(analytics_id, quote=True)
        analytics = f"""
<script async src="https://www.googletagmanager.com/gtag/js?id={safe_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{safe_id}');
</script>""".strip()

    verification = site.get("googleSiteVerification", "")
    verification_tag = (
        f'<meta name="google-site-verification" content="{html.escape(verification, quote=True)}">'
        if verification
        else ""
    )
    research_visual = html.escape(site.get("heroBackground", ""), quote=True)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {verification_tag}
  <title>{html.escape(site["name"])}</title>
  <meta name="description" content="{html.escape(site.get("description", ""), quote=True)}">
  <link rel="icon" href="favicon.ico">
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <main id="top" class="page">
    <header class="profile-header" style="--profile-accent-image: url('{research_visual}')">
      <div class="profile-main">
        <div class="identity">
          {render_avatar(site)}
          <div>
            <p class="eyebrow">Researcher Profile</p>
            <h1>{html.escape(site["name"])}</h1>
            <div class="hero-actions">
              {render_links(site)}
            </div>
          </div>
        </div>
      </div>
    </header>

    <section class="metrics" aria-label="Research metrics">
      {render_metrics(site)}
    </section>

    {render_sections(sections)}
  </main>

  <footer class="site-footer">
    <span id="busuanzi_container_site_pv">Views: <span id="busuanzi_value_site_pv">0</span></span>
    <span id="busuanzi_container_site_uv">Visitors: <span id="busuanzi_value_site_uv">0</span></span>
  </footer>
  <script async src="//busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"></script>
  {analytics}
</body>
</html>
"""


def main() -> None:
    site = json.loads(SITE_FILE.read_text(encoding="utf-8"))
    sections = load_sections()
    OUTPUT_FILE.write_text(render_page(site, sections), encoding="utf-8")
    print(f"Built {OUTPUT_FILE.relative_to(ROOT)} from {len(sections)} section(s).")


if __name__ == "__main__":
    main()
