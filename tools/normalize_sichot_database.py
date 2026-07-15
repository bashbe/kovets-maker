#!/usr/bin/env python3
"""Normalise les titres des sichot et crée les relations parashiot/liens."""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path


HEBREW_VALUES = {
    "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7,
    "ח": 8, "ט": 9, "י": 10, "כ": 20, "ך": 20, "ל": 30,
    "מ": 40, "ם": 40, "נ": 50, "ן": 50, "ס": 60, "ע": 70,
    "פ": 80, "ף": 80, "צ": 90, "ץ": 90, "ק": 100, "ר": 200,
    "ש": 300, "ת": 400,
}


def hebrew_number(value: str) -> int | None:
    letters = [char for char in value if char in HEBREW_VALUES]
    return sum(HEBREW_VALUES[char] for char in letters) if letters else None


def parse_title(title: str, url: str = "") -> tuple[int | None, str | None, int | None, str | None]:
    clean_title = re.sub(r"[\u200e\u200f]", "", title)
    parts = [re.sub(r"\s+", " ", part).strip() for part in clean_title.split("•")]
    parts = [part for part in parts if part]

    # Le site inverse parfois les blocs, notamment pour חלק טו. On cherche donc
    # les libellés partout, sans supposer l'ordre « חלק • parasha • שיחה ».
    chelek_match = re.search(r"(?:^|\s)חלק\s+([א-תךםןףץ]+)(?=\s|$)", clean_title)
    sicha_match = re.search(r"(?:^|\s)שיחה\s+([א-תךםןףץ]+)(?=\s|$)", clean_title)
    chelek = hebrew_number(chelek_match.group(1)) if chelek_match else None
    sicha = hebrew_number(sicha_match.group(1)) if sicha_match else None

    url_chelek = re.search(r"(?:^|[-/])chelek-(\d+)(?:[-/]|$)", url, re.IGNORECASE)
    url_sicha = re.search(r"(?:^|-)sicha-(\d+)(?:[-/]|$)", url, re.IGNORECASE)
    if chelek is None and url_chelek:
        chelek = int(url_chelek.group(1))
    if sicha is None and url_sicha:
        sicha = int(url_sicha.group(1))

    chelek_part_index = next((i for i, part in enumerate(parts) if re.search(r"(?:^|\s)חלק\s", part)), None)
    parasha = None
    if chelek_part_index is not None and chelek_part_index + 1 < len(parts):
        candidate = parts[chelek_part_index + 1]
        if not re.search(r"(?:^|\s)(?:חלק|שיחה)\s", candidate):
            parasha = candidate
    if parasha is None:
        candidates = [part for part in parts if not re.search(r"(?:^|\s)(?:חלק|שיחה)\s", part)]
        if candidates:
            parasha = candidates[0]
    if parasha is None and chelek_match:
        # Format sans puces : « חלק יח פנחס - יב-יג תמוז ».
        remainder = clean_title[chelek_match.end():].strip(" -")
        parasha = remainder or None

    sicha_label = None
    if sicha_match:
        sicha_label = next((part for part in parts if "שיחה" in part), sicha_match.group(0).strip())

    return chelek, parasha, sicha, sicha_label


def migrate(database: Path) -> None:
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(sichot)")}
        for name, sql_type in (
            ("chelek_number", "INTEGER"),
            ("parasha_id", "INTEGER"),
            ("sicha_number", "INTEGER"),
            ("sicha_label", "TEXT"),
        ):
            if name not in columns:
                connection.execute(f'ALTER TABLE sichot ADD COLUMN "{name}" {sql_type}')

        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS parashiot (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS sicha_links (
                id INTEGER PRIMARY KEY,
                sicha_id INTEGER NOT NULL UNIQUE,
                "kehos - original" TEXT,
                "kehos - lahak" TEXT,
                scraped_at TEXT,
                scrape_error TEXT,
                FOREIGN KEY (sicha_id) REFERENCES sichot(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_sichot_chelek_number
                ON sichot(chelek_number);
            CREATE INDEX IF NOT EXISTS idx_sichot_parasha_id
                ON sichot(parasha_id);
            CREATE INDEX IF NOT EXISTS idx_sichot_sicha_number
                ON sichot(sicha_number);
            """
        )
        link_columns = {row[1] for row in connection.execute("PRAGMA table_info(sicha_links)")}
        if "scraped_at" not in link_columns:
            connection.execute("ALTER TABLE sicha_links ADD COLUMN scraped_at TEXT")
        if "scrape_error" not in link_columns:
            connection.execute("ALTER TABLE sicha_links ADD COLUMN scrape_error TEXT")

        rows = connection.execute("SELECT id, title, url FROM sichot ORDER BY id").fetchall()
        parsed_rows = []
        for sicha_id, title, url in rows:
            chelek, parasha, sicha, sicha_label = parse_title(title, url)
            parsed_rows.append((sicha_id, chelek, parasha, sicha, sicha_label))

        # Reconstruire évite de conserver les parashiot produites par une ancienne
        # version du parseur.
        connection.execute("UPDATE sichot SET parasha_id = NULL")
        connection.execute("DELETE FROM parashiot")
        for _sicha_id, _chelek, parasha, _sicha, _label in parsed_rows:
            if parasha:
                connection.execute("INSERT OR IGNORE INTO parashiot(name) VALUES (?)", (parasha,))

        for sicha_id, chelek, parasha, sicha, sicha_label in parsed_rows:
            parasha_id = None
            if parasha:
                parasha_id = connection.execute(
                    "SELECT id FROM parashiot WHERE name = ?", (parasha,)
                ).fetchone()[0]
            connection.execute(
                """UPDATE sichot
                   SET chelek_number = ?, parasha_id = ?, sicha_number = ?, sicha_label = ?
                   WHERE id = ?""",
                (chelek, parasha_id, sicha, sicha_label, sicha_id),
            )
            connection.execute(
                "INSERT OR IGNORE INTO sicha_links(sicha_id) VALUES (?)", (sicha_id,)
            )

        connection.commit()
        total = connection.execute("SELECT COUNT(*) FROM sichot").fetchone()[0]
        parashiot = connection.execute("SELECT COUNT(*) FROM parashiot").fetchone()[0]
        parsed = connection.execute(
            "SELECT COUNT(*) FROM sichot WHERE chelek_number IS NOT NULL AND parasha_id IS NOT NULL"
        ).fetchone()[0]
        print(f"Sichot: {total}; parashiot: {parashiot}; titres structurés: {parsed}")
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", nargs="?", type=Path, default=Path("sichot_links.db"))
    args = parser.parse_args()
    migrate(args.database.resolve())


if __name__ == "__main__":
    main()
