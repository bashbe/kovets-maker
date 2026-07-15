#!/usr/bin/env python3
"""Récupère les liens Kehos de chaque page et les stocke dans SQLite."""

from __future__ import annotations

import argparse
import re
import sqlite3
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin
from urllib.request import Request, urlopen


ORIGINAL_IMAGE = "https://projectlikkuteisichos.org/wp-content/uploads/2022/02/The_Sicha_Pages.png"
ORIGINAL_HEBREW_BANNER = "https://projectlikkuteisichos.org/wp-content/uploads/2020/05/השיחה-עמודים-Banner.png"
ORIGINAL_LAYOUT_SUFFIX = "TheSicha-Layout.png"
LAHAK_IMAGE = "https://projectlikkuteisichos.org/wp-content/uploads/2021/02/The_Sicha_Pages-1.png"
USER_AGENT = "Mozilla/5.0 (compatible; KovetsMaker/1.0)"


class KehosLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchor_stack: list[str | None] = []
        self.original: str | None = None
        self.lahak: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag.lower() == "a":
            self.anchor_stack.append(attributes.get("href"))
        elif tag.lower() == "img" and self.anchor_stack:
            # WordPress peut déplacer l'URL dans data-src/srcset lors du lazy-load.
            image_attributes = " ".join(value or "" for value in attributes.values())
            decoded_attributes = unquote(image_attributes)
            href = self.anchor_stack[-1]
            is_original = (
                ORIGINAL_IMAGE in image_attributes
                or ORIGINAL_HEBREW_BANNER in decoded_attributes
                or re.search(
                    rf"{re.escape(ORIGINAL_LAYOUT_SUFFIX)}(?:[?#][^\s\"']*)?(?=[\s\"']|$)",
                    decoded_attributes,
                    re.IGNORECASE,
                ) is not None
            )
            if href and is_original:
                self.original = href
            if href and LAHAK_IMAGE in image_attributes:
                self.lahak = href

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self.anchor_stack:
            self.anchor_stack.pop()


def scrape_page(row: tuple[int, str], attempts: int = 1) -> tuple[int, str | None, str | None, str | None]:
    sicha_id, page_url = row
    last_error = None
    for attempt in range(attempts):
        try:
            request = Request(page_url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=15) as response:
                html = response.read().decode(response.headers.get_content_charset() or "utf-8", "replace")
            parser = KehosLinkParser()
            parser.feed(html)
            original = urljoin(page_url, parser.original) if parser.original else None
            lahak = urljoin(page_url, parser.lahak) if parser.lahak else None
            return sicha_id, original, lahak, None
        except Exception as exc:  # une erreur n'interrompt pas les autres pages
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(1 + attempt)
    return sicha_id, None, None, last_error


def run(database: Path, workers: int, missing_original: bool = False) -> None:
    connection = sqlite3.connect(database, timeout=30)
    connection.execute("PRAGMA busy_timeout = 30000")
    try:
        condition = (
            "NULLIF(TRIM(l.\"kehos - original\"), '') IS NULL"
            if missing_original else "l.scraped_at IS NULL"
        )
        rows = connection.execute(
            f"""SELECT s.id, s.url
                FROM sichot s JOIN sicha_links l ON l.sicha_id = s.id
                WHERE {condition}
                ORDER BY s.id"""
        ).fetchall()
    except sqlite3.OperationalError as exc:
        connection.close()
        raise SystemExit("Exécutez d'abord tools/normalize_sichot_database.py") from exc

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(scrape_page, row) for row in rows]
            for position, future in enumerate(as_completed(futures), 1):
                sicha_id, original, lahak, error = future.result()
                connection.execute(
                    """UPDATE sicha_links SET
                           "kehos - original" = COALESCE(NULLIF("kehos - original", ''), ?),
                           "kehos - lahak" = COALESCE(NULLIF("kehos - lahak", ''), ?),
                           scraped_at = ?, scrape_error = ?
                       WHERE sicha_id = ?""",
                    (original, lahak, datetime.now(timezone.utc).isoformat(), error, sicha_id),
                )
                if position % 10 == 0 or position == len(rows):
                    connection.commit()
                    print(f"Pages traitées: {position}/{len(rows)}", flush=True)
        connection.commit()
        original_count = connection.execute(
            'SELECT COUNT(*) FROM sicha_links WHERE "kehos - original" IS NOT NULL'
        ).fetchone()[0]
        lahak_count = connection.execute(
            'SELECT COUNT(*) FROM sicha_links WHERE "kehos - lahak" IS NOT NULL'
        ).fetchone()[0]
        error_count = connection.execute(
            "SELECT COUNT(*) FROM sicha_links WHERE scrape_error IS NOT NULL"
        ).fetchone()[0]
        print(f"kehos - original: {original_count}; kehos - lahak: {lahak_count}; erreurs: {error_count}")
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", nargs="?", type=Path, default=Path("sichot_links.db"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--missing-original", action="store_true",
        help="revérifie uniquement les rangées sans kehos - original",
    )
    args = parser.parse_args()
    run(args.database.resolve(), max(1, args.workers), args.missing_original)


if __name__ == "__main__":
    main()
