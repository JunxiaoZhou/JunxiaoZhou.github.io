#!/usr/bin/env python3
"""Fetch and normalize Google Scholar author metrics through SerpApi."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "content" / "scholar.json"
ENDPOINT = "https://serpapi.com/search.json"


class ScholarDataError(ValueError):
    """Raised when SerpApi returns incomplete or unexpected Scholar data."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--author-id",
        default="XsS_vrgAAAAJ",
        help="Google Scholar author ID",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Normalized JSON output path",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Read a saved SerpApi response instead of making a network request",
    )
    return parser.parse_args()


def fetch_response(author_id: str, api_key: str) -> dict:
    query = urllib.parse.urlencode(
        {
            "engine": "google_scholar_author",
            "author_id": author_id,
            "hl": "en",
            "num": 100,
            "api_key": api_key,
        }
    )
    request = urllib.request.Request(
        f"{ENDPOINT}?{query}",
        headers={"User-Agent": "JunxiaoZhou.github.io Scholar metrics updater"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ScholarDataError(f"SerpApi request failed: {error}") from error


def metric_value(table: list[dict], name: str) -> int:
    payload = next((row[name] for row in table if name in row), None)
    if not isinstance(payload, dict) or not isinstance(payload.get("all"), int):
        raise ScholarDataError(f"Missing cited_by.table metric: {name}")
    return payload["all"]


def normalize(raw: dict, expected_author_id: str) -> dict:
    if raw.get("error"):
        raise ScholarDataError(f"SerpApi returned an error: {raw['error']}")

    parameters = raw.get("search_parameters", {})
    actual_author_id = parameters.get("author_id")
    if actual_author_id and actual_author_id != expected_author_id:
        raise ScholarDataError(
            f"Unexpected author ID: {actual_author_id!r} (expected {expected_author_id!r})"
        )

    cited_by = raw.get("cited_by")
    if not isinstance(cited_by, dict):
        raise ScholarDataError("Missing cited_by data")

    table = cited_by.get("table")
    if not isinstance(table, list):
        raise ScholarDataError("Missing cited_by table")

    citations_all = metric_value(table, "citations")
    h_all = metric_value(table, "h_index")

    articles = raw.get("articles", [])
    if not isinstance(articles, list):
        raise ScholarDataError("Invalid articles data")

    normalized_articles = []
    for article in articles:
        title = article.get("title")
        cited_by = article.get("cited_by") or {}
        cited_by_value = cited_by.get("value")
        if cited_by_value is None:
            cited_by_value = 0
        if not isinstance(title, str):
            continue
        if not isinstance(cited_by_value, int):
            raise ScholarDataError(f"Invalid citation count for article: {title}")
        normalized_articles.append(
            {
                "title": title,
                "citedBy": cited_by_value,
            }
        )

    return {
        "authorId": expected_author_id,
        "citations": {"all": citations_all},
        "hIndex": {"all": h_all},
        "articles": normalized_articles,
    }


def write_if_changed(path: Path, data: dict) -> bool:
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == rendered:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    return True


def main() -> int:
    args = parse_args()
    try:
        if args.input:
            raw = json.loads(args.input.read_text(encoding="utf-8"))
        else:
            api_key = os.environ.get("SERPAPI_API_KEY")
            if not api_key:
                raise ScholarDataError("SERPAPI_API_KEY is not set")
            raw = fetch_response(args.author_id, api_key)
        normalized = normalize(raw, args.author_id)
        changed = write_if_changed(args.output, normalized)
    except (OSError, json.JSONDecodeError, ScholarDataError) as error:
        print(f"Scholar metrics update failed: {error}", file=sys.stderr)
        return 1

    action = "Updated" if changed else "Unchanged"
    print(
        f"{action} {args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output} "
        f"({normalized['citations']['all']:,} citations, h-index {normalized['hIndex']['all']})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
