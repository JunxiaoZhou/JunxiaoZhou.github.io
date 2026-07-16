#!/usr/bin/env python3
"""Add queued publication titles to publications.json using Crossref metadata."""

from __future__ import annotations

import argparse
import html
import json
import re
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TITLES = ROOT / "content" / "new-publications.txt"
DEFAULT_PUBLICATIONS = ROOT / "content" / "publications.json"
CROSSREF_ENDPOINT = "https://api.crossref.org/works"
CONTACT_EMAIL = "junxiaozhou@nju.edu.cn"
PRIMARY_AUTHOR_NAME = "Junxiao Zhou"
MINIMUM_MATCH_SCORE = 0.92


class PublicationMetadataError(ValueError):
    """Raised when a queued title cannot be resolved safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--titles",
        type=Path,
        default=DEFAULT_TITLES,
        help="Text file containing one complete publication title per line",
    )
    parser.add_argument(
        "--publications",
        type=Path,
        default=DEFAULT_PUBLICATIONS,
        help="Publication JSON file to update",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and print metadata without updating publications.json",
    )
    return parser.parse_args()


def clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"<[^>]+>", "", html.unescape(value))
    return re.sub(r"\s+", " ", value).strip()


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", clean_text(value)).casefold()
    return re.sub(r"[^a-z0-9]+", "", value)


def queued_titles(path: Path) -> list[str]:
    if not path.exists():
        return []
    titles = []
    seen = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        title = raw_line.strip()
        if not title or title.startswith("#"):
            continue
        key = normalize_title(title)
        if key and key not in seen:
            titles.append(title)
            seen.add(key)
    return titles


def fetch_crossref_candidates(title: str) -> list[dict]:
    query = urllib.parse.urlencode(
        {
            "query.title": title,
            "rows": 10,
            "mailto": CONTACT_EMAIL,
        }
    )
    request = urllib.request.Request(
        f"{CROSSREF_ENDPOINT}?{query}",
        headers={
            "Accept": "application/json",
            "User-Agent": (
                "JunxiaoZhou.github.io publication updater "
                f"(mailto:{CONTACT_EMAIL})"
            ),
        },
    )
    ssl_context = ssl.create_default_context()
    try:
        import certifi

        ssl_context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(
                request, timeout=30, context=ssl_context
            ) as response:
                payload = json.load(response)
            items = payload.get("message", {}).get("items", [])
            if not isinstance(items, list):
                raise PublicationMetadataError("Crossref returned invalid work data")
            return [item for item in items if isinstance(item, dict)]
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
        ) as error:
            last_error = error
            if attempt < 2:
                time.sleep(attempt + 1)
    raise PublicationMetadataError(f"Crossref request failed: {last_error}")


def crossref_title(item: dict) -> str:
    titles = item.get("title", [])
    if isinstance(titles, list) and titles:
        return clean_text(titles[0])
    return ""


def candidate_score(requested_title: str, item: dict) -> float:
    requested = normalize_title(requested_title)
    candidate = normalize_title(crossref_title(item))
    if not requested or not candidate:
        return 0.0
    if requested == candidate:
        score = 1.0
    else:
        score = SequenceMatcher(None, requested, candidate).ratio()

    authors = item.get("author", [])
    author_names = " ".join(
        f"{author.get('given', '')} {author.get('family', '')}"
        for author in authors
        if isinstance(author, dict)
    )
    if normalize_title(PRIMARY_AUTHOR_NAME) in normalize_title(author_names):
        score += 0.02
    if item.get("type") == "journal-article":
        score += 0.01
    return min(score, 1.0)


def best_candidate(title: str, candidates: list[dict]) -> dict:
    if not candidates:
        raise PublicationMetadataError(f"No Crossref results for: {title}")
    scored = sorted(
        ((candidate_score(title, item), item) for item in candidates),
        key=lambda pair: pair[0],
        reverse=True,
    )
    score, candidate = scored[0]
    if score < MINIMUM_MATCH_SCORE:
        found = crossref_title(candidate) or "unknown title"
        raise PublicationMetadataError(
            f"Low-confidence Crossref match for {title!r}: {found!r} ({score:.1%})"
        )
    return candidate


def author_name(author: dict) -> str:
    name = clean_text(
        " ".join(
            part
            for part in (author.get("given", ""), author.get("family", ""))
            if isinstance(part, str) and part.strip()
        )
    )
    if normalize_title(name) == normalize_title(PRIMARY_AUTHOR_NAME):
        return f"**{PRIMARY_AUTHOR_NAME}**"
    return name


def publication_year(item: dict) -> int | None:
    for field in ("published-print", "published-online", "published", "issued"):
        date_parts = item.get(field, {}).get("date-parts", [])
        if (
            isinstance(date_parts, list)
            and date_parts
            and isinstance(date_parts[0], list)
            and date_parts[0]
            and isinstance(date_parts[0][0], int)
        ):
            return date_parts[0][0]
    return None


def citation_text(item: dict, year: int) -> str:
    volume = clean_text(item.get("volume"))
    locator = clean_text(item.get("page")) or clean_text(item.get("article-number"))
    if volume and locator:
        return f"**{volume}**, {locator} ({year})"
    if volume:
        return f"**{volume}** ({year})"
    if locator:
        return f"{locator} ({year})"
    return f"({year})"


def normalize_crossref_item(requested_title: str, item: dict) -> dict:
    title = crossref_title(item)
    authors = item.get("author", [])
    author_names = [
        author_name(author) for author in authors if isinstance(author, dict)
    ]
    author_names = [name for name in author_names if name]
    containers = item.get("container-title", [])
    venue = clean_text(containers[0]) if isinstance(containers, list) and containers else ""
    doi = clean_text(item.get("DOI"))
    year = publication_year(item)

    missing = []
    if not title:
        missing.append("title")
    if not author_names:
        missing.append("authors")
    if not venue:
        missing.append("journal")
    if not doi:
        missing.append("DOI")
    if year is None:
        missing.append("year")
    if missing:
        raise PublicationMetadataError(
            f"Incomplete Crossref metadata for {requested_title!r}: {', '.join(missing)}"
        )

    return {
        "authors": ", ".join(author_names),
        "title": title,
        "venue": venue,
        "url": f"https://doi.org/{doi}",
        "citation": citation_text(item, year),
    }


def load_publications(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PublicationMetadataError("publications.json must contain an object")
    if not isinstance(data.get("other"), list):
        raise PublicationMetadataError("publications.json must contain an other list")
    return data


def main() -> int:
    args = parse_args()
    try:
        titles = queued_titles(args.titles)
        publications = load_publications(args.publications)
        existing_titles = {
            normalize_title(item.get("title", ""))
            for group in ("selected", "other")
            for item in publications.get(group, [])
            if isinstance(item, dict)
        }
        pending = [
            title for title in titles if normalize_title(title) not in existing_titles
        ]
        additions = []
        for title in pending:
            candidate = best_candidate(title, fetch_crossref_candidates(title))
            additions.append(normalize_crossref_item(title, candidate))

        if not additions:
            print("Publication metadata is unchanged.")
            return 0

        for item in additions:
            print(f"Resolved: {item['title']} -> {item['url']}")
        if args.dry_run:
            print(json.dumps(additions, ensure_ascii=False, indent=2))
            return 0

        publications["other"] = additions + publications["other"]
        args.publications.write_text(
            json.dumps(publications, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Added {len(additions)} publication(s) to {args.publications}.")
        return 0
    except (OSError, json.JSONDecodeError, PublicationMetadataError) as error:
        print(f"Publication metadata update failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
