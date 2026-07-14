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
from datetime import datetime, timezone
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


def metric_pair(table: list[dict], name: str) -> tuple[int, int | None, int | None]:
    payload = next((row[name] for row in table if name in row), None)
    if not isinstance(payload, dict) or not isinstance(payload.get("all"), int):
        raise ScholarDataError(f"Missing cited_by.table metric: {name}")

    recent_key = next((key for key in payload if key.startswith("since_")), None)
    recent_value = payload.get(recent_key) if recent_key else None
    if recent_value is not None and not isinstance(recent_value, int):
        raise ScholarDataError(f"Invalid recent value for metric: {name}")

    recent_since = int(recent_key.removeprefix("since_")) if recent_key else None
    return payload["all"], recent_value, recent_since


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
    graph = cited_by.get("graph")
    if not isinstance(table, list) or not isinstance(graph, list):
        raise ScholarDataError("Missing cited_by table or graph")

    citations_all, citations_recent, recent_since = metric_pair(
        table, "citations"
    )
    h_all, h_recent, h_since = metric_pair(table, "h_index")
    i10_all, i10_recent, i10_since = metric_pair(table, "i10_index")
    recent_years = {year for year in (recent_since, h_since, i10_since) if year}
    if len(recent_years) > 1:
        raise ScholarDataError("Recent metric periods do not match")

    by_year = []
    for point in graph:
        year = point.get("year")
        citations = point.get("citations")
        if not isinstance(year, int) or not isinstance(citations, int):
            raise ScholarDataError("Invalid point in cited_by graph")
        by_year.append({"year": year, "citations": citations})
    by_year.sort(key=lambda point: point["year"])

    articles = raw.get("articles", [])
    if not isinstance(articles, list):
        raise ScholarDataError("Invalid articles data")

    return {
        "authorId": expected_author_id,
        "authorName": raw.get("author", {}).get("name", "Junxiao Zhou"),
        "updatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        ),
        "recentSince": next(iter(recent_years), None),
        "citations": {"all": citations_all, "recent": citations_recent},
        "hIndex": {"all": h_all, "recent": h_recent},
        "i10Index": {"all": i10_all, "recent": i10_recent},
        "byYear": by_year,
        "articleCount": len(articles),
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
