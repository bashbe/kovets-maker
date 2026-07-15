#!/usr/bin/env python3
"""Rattrape les liens Kehos manquants depuis le catalogue /library/."""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from scrape_sicha_links import KehosLinkParser, USER_AGENT


LIBRARY_URL = "https://projectlikkuteisichos.org/library/"
HEBREW_VALUES = {
    "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7,
    "ח": 8, "ט": 9, "י": 10, "כ": 20, "ך": 20, "ל": 30,
    "מ": 40, "ם": 40, "נ": 50, "ן": 50, "ס": 60, "ע": 70,
    "פ": 80, "ף": 80, "צ": 90, "ץ": 90, "ק": 100, "ר": 200,
    "ש": 300, "ת": 400,
}


def fetch(url: str, attempts: int = 3) -> str:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=25) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, "replace")
        except Exception as exc:
            last_error = exc
            time.sleep(1 + attempt)
    assert last_error is not None
    raise last_error


def clean_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", value)
    value = value.replace("־", " ").replace("–", " ").replace("—", " ")
    value = re.sub(r"[\"'׳״’‘`´]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def comparison_text(value: str) -> str:
    return re.sub(r"[^א-ת0-9]", "", clean_text(value))


def hebrew_number(value: str) -> int | None:
    token = clean_text(value).replace(" ", "")
    if not token or any(char not in HEBREW_VALUES for char in token):
        return None
    return sum(HEBREW_VALUES[char] for char in token)


def volume_number(heading: str) -> int | None:
    match = re.search(r"חלק\s+([א-תךםןףץ]+)", clean_text(heading))
    return hebrew_number(match.group(1)) if match else None


@dataclass(frozen=True)
class CatalogEntry:
    chelek: int
    title: str
    url: str


class LibraryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_main = 0
        self.heading_depth = 0
        self.anchor_depth = 0
        self.heading_parts: list[str] = []
        self.anchor_parts: list[str] = []
        self.anchor_href: str | None = None
        self.current_chelek: int | None = None
        self.entries: list[CatalogEntry] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = dict(attrs)
        if tag == "main":
            self.in_main += 1
        elif self.in_main and tag == "h2":
            self.heading_depth = 1
            self.heading_parts = []
        elif self.heading_depth:
            self.heading_depth += 1
        if self.in_main and tag == "a":
            self.anchor_depth = 1
            self.anchor_parts = []
            self.anchor_href = attributes.get("href")
        elif self.anchor_depth:
            self.anchor_depth += 1

    def handle_data(self, data: str) -> None:
        if self.heading_depth:
            self.heading_parts.append(data)
        if self.anchor_depth:
            self.anchor_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.heading_depth:
            self.heading_depth -= 1
            if self.heading_depth == 0:
                number = volume_number("".join(self.heading_parts))
                if number is not None:
                    self.current_chelek = number
        if self.anchor_depth:
            self.anchor_depth -= 1
            if self.anchor_depth == 0 and self.current_chelek and self.anchor_href:
                title = clean_text("".join(self.anchor_parts))
                if title:
                    self.entries.append(
                        CatalogEntry(self.current_chelek, title, urljoin(LIBRARY_URL, self.anchor_href))
                    )
        if tag == "main" and self.in_main:
            self.in_main -= 1


def parse_catalog(html: str) -> list[CatalogEntry]:
    parser = LibraryParser()
    parser.feed(html)
    unique: dict[str, CatalogEntry] = {}
    for entry in parser.entries:
        # WordPress publie parfois deux fois la même page, avec et sans slash final.
        unique.setdefault(entry.url.rstrip("/"), entry)
    return list(unique.values())


def parse_catalog_title(entry: CatalogEntry) -> tuple[str, int | None]:
    parts = [clean_text(part) for part in re.split(r"\s*•\s*", entry.title) if clean_text(part)]
    if len(parts) >= 2:
        number = hebrew_number(parts[0])
        if number is not None and number <= 10:
            return " ".join(parts[1:]), number
    if len(parts) >= 2:
        last_part = re.sub(r"^שיחה\s+", "", parts[-1])
        number = hebrew_number(last_part)
        if number is not None and number <= 10:
            return " ".join(parts[:-1]), number
    if len(parts) == 1:
        trailing = re.match(r"^(.*?)\s+([א-ט])$", parts[0])
        if trailing:
            return trailing.group(1), hebrew_number(trailing.group(2))
        slug = urlparse(entry.url).path.strip("/").lower()
        url_number = re.search(r"([a-z]+)(\d+)$", slug)
        if url_number and "-" not in slug:
            return entry.title, int(url_number.group(2))
    return entry.title, None


def aliases(value: str) -> set[str]:
    base = comparison_text(value)
    values = {base}
    if base.startswith("כי"):
        values.add(base[2:])
    equivalent_groups = (
        {"קדשים", "קדושים"},
        {"פנחס", "פינחס"},
        {"קרח", "קורח"},
        {"חקת", "חוקת"},
        {"בהעלותך", "בהעלתך"},
        {"תבא", "תבוא"},
        {"אמר", "אמור"},
        {"פורים", "חגהפורים"},
        {"פסח", "חגהפסח"},
        {"סוכות", "חגסוכות", "חגהסוכות"},
        {"ברכה", "וזאתהברכה"},
        {"יביגתמוז", "פנחסיביגתמוז"},
    )
    for group in equivalent_groups:
        if base in group:
            values.update(group)
    return values


def database_display_key(title: str) -> str:
    value = clean_text(title)
    value = re.sub(r"^חלק\s+[א-תךםןףץ]+\s*•?\s*", "", value)
    value = re.sub(r"(?:^|\s)שיחה\s+", " ", value)
    return display_comparison(value)


def display_comparison(value: str) -> str:
    result = comparison_text(value)
    for old, new in (
        ("תבוא", "תבא"), ("פינחס", "פנחס"), ("קורח", "קרח"),
        ("חוקת", "חקת"), ("בהעלתך", "בהעלותך"),
    ):
        result = result.replace(old, new)
    return result


def scrape_catalog_page(entry: CatalogEntry) -> tuple[CatalogEntry, str | None, str | None, str | None]:
    try:
        parser = KehosLinkParser()
        parser.feed(fetch(entry.url))
        original = urljoin(entry.url, parser.original) if parser.original else None
        lahak = urljoin(entry.url, parser.lahak) if parser.lahak else None
        return entry, original, lahak, None
    except Exception as exc:
        return entry, None, None, f"{type(exc).__name__}: {exc}"


def run(database: Path, report: Path, workers: int, update: bool) -> None:
    catalog = parse_catalog(fetch(LIBRARY_URL))
    connection = sqlite3.connect(database, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    rows = connection.execute(
        """SELECT s.id, s.chelek_number, p.name AS parasha, s.sicha_number,
                  s.title, s.url, l."kehos - original" AS original,
                  l."kehos - lahak" AS lahak
           FROM sichot s
           LEFT JOIN parashiot p ON p.id = s.parasha_id
           JOIN sicha_links l ON l.sicha_id = s.id
           WHERE NULLIF(TRIM(l."kehos - original"), '') IS NULL
           ORDER BY s.id"""
    ).fetchall()

    index: dict[tuple[int, str, int | None], list[sqlite3.Row]] = {}
    display_index: dict[tuple[int, str], list[sqlite3.Row]] = {}
    for row in rows:
        if row["chelek_number"] is None or not row["parasha"]:
            continue
        for parasha_alias in aliases(row["parasha"]):
            index.setdefault(
                (row["chelek_number"], parasha_alias, row["sicha_number"]), []
            ).append(row)
        display_index.setdefault(
            (row["chelek_number"], database_display_key(row["title"])), []
        ).append(row)

    matches: dict[str, list[sqlite3.Row]] = {}
    for entry in catalog:
        parasha, sicha = parse_catalog_title(entry)
        candidates: list[sqlite3.Row] = []
        for parasha_alias in aliases(parasha):
            candidates.extend(index.get((entry.chelek, parasha_alias, sicha), []))
        candidates.extend(display_index.get((entry.chelek, display_comparison(entry.title)), []))
        if candidates:
            matches[entry.url] = list({row["id"]: row for row in candidates}.values())

    selected = [entry for entry in catalog if entry.url in matches]
    scraped: dict[str, tuple[str | None, str | None, str | None]] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(scrape_catalog_page, entry) for entry in selected]
        for position, future in enumerate(as_completed(futures), 1):
            entry, original, lahak, error = future.result()
            scraped[entry.url] = (original, lahak, error)
            if position % 25 == 0 or position == len(futures):
                print(f"Pages du catalogue vérifiées: {position}/{len(futures)}", flush=True)

    report.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sicha_id", "chelek_number", "parasha", "sicha_number", "title",
        "search_page_url", "library_page_url", "kehos_original_found",
        "kehos_lahak_found", "result", "error",
    ]
    recovered_original_ids: set[int] = set()
    recovered_lahak_ids: set[int] = set()
    report_rows: list[dict[str, object]] = []
    now = datetime.now(timezone.utc).isoformat()
    for entry in selected:
        original, lahak, error = scraped[entry.url]
        for row in matches[entry.url]:
            result = "original_found" if original else "no_original_on_library_page"
            if error:
                result = "request_error"
            report_rows.append({
                "sicha_id": row["id"], "chelek_number": row["chelek_number"],
                "parasha": row["parasha"], "sicha_number": row["sicha_number"],
                "title": row["title"], "search_page_url": row["url"],
                "library_page_url": entry.url, "kehos_original_found": original or "",
                "kehos_lahak_found": lahak or "", "result": result, "error": error or "",
            })
            if update and (original or (lahak and not row["lahak"])):
                connection.execute(
                    """UPDATE sicha_links
                       SET "kehos - original" = COALESCE(NULLIF("kehos - original", ''), ?),
                           "kehos - lahak" = COALESCE(NULLIF("kehos - lahak", ''), ?),
                           scraped_at = ?, scrape_error = NULL
                       WHERE sicha_id = ?""",
                    (original, lahak, now, row["id"]),
                )
            if original:
                recovered_original_ids.add(row["id"])
            if lahak and not row["lahak"]:
                recovered_lahak_ids.add(row["id"])

    matched_ids = {row["id"] for candidates in matches.values() for row in candidates}
    for row in rows:
        if row["id"] not in matched_ids:
            report_rows.append({
                "sicha_id": row["id"], "chelek_number": row["chelek_number"],
                "parasha": row["parasha"] or "", "sicha_number": row["sicha_number"] or "",
                "title": row["title"], "search_page_url": row["url"],
                "library_page_url": "", "kehos_original_found": "",
                "kehos_lahak_found": "", "result": "not_listed_or_unmatched", "error": "",
            })

    with report.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(report_rows, key=lambda item: int(item["sicha_id"])))
    if update:
        connection.commit()
    connection.close()
    print(
        f"Catalogue: {len(catalog)} pages; manquants: {len(rows)}; "
        f"correspondances: {len(matched_ids)}; originaux trouvés: {len(recovered_original_ids)}; "
        f"lahak ajoutables: {len(recovered_lahak_ids)}; mise à jour: {'oui' if update else 'non'}"
    )
    print(f"Rapport: {report}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", nargs="?", type=Path, default=Path("sichot_links.db"))
    parser.add_argument("--report", type=Path, default=Path("library_recovery_report.csv"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()
    run(args.database.resolve(), args.report.resolve(), args.workers, args.update)


if __name__ == "__main__":
    main()
