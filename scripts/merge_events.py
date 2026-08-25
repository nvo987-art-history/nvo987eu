#!/usr/bin/env python3

import csv
import json
import re
import unicodedata
from datetime import datetime


PARIS_POSTCODE_RE = re.compile(r"^750\d{2}$")


def normalize(value):
    if value is None:
        return ""

    value = str(value).strip().lower()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        c for c in value
        if not unicodedata.combining(c)
    )

    value = re.sub(r"\s+", " ", value)

    return value


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def parse_date(value):
    value = clean(value)

    if not value:
        return ""

    # DATAtourisme dátumformátumok kezelése
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).isoformat()
        except ValueError:
            pass

    return value


def paris_event(record):
    fields = record.get("fields", {})

    city = normalize(
        fields.get("address_city")
        or fields.get("ville")
        or ""
    )

    postcode = clean(
        fields.get("postalcode")
        or fields.get("postcode")
        or ""
    )

    if city == "paris":
        return True

    if PARIS_POSTCODE_RE.match(postcode):
        return True

    return False


def paris_key(record):
    fields = record.get("fields", {})

    title = normalize(
        fields.get("title")
        or fields.get("label")
        or ""
    )

    start = normalize(
        fields.get("date_start")
        or fields.get("startdate")
        or ""
    )

    city = normalize(
        fields.get("address_city")
        or fields.get("city")
        or ""
    )

    return (title, start, city)


def convert_paris_record(record):
    fields = record.get("fields", {})

    fields["source"] = "paris-open-data"
    fields["source_name"] = "Paris Open Data / Ville de Paris"
    fields["source_url"] = "https://opendata.paris.fr/"

    return {
        "recordid": record.get("recordid"),
        "fields": fields
    }


def convert_datatourisme_row(row):
    title = clean(row.get("label"))
    start = parse_date(row.get("startdate"))
    end = parse_date(row.get("enddate"))

    city = clean(row.get("city"))
    postalcode = clean(row.get("postalcode"))

    website = clean(
        row.get("web")
        or row.get("site web")
        or row.get("website")
    )

    description = clean(row.get("comment"))

    fields = {
        "title": title,
        "date_start": start,
        "date_end": end,
        "address_city": city,
        "postalcode": postalcode,
        "address_name": clean(row.get("street")),
        "latitude": clean(row.get("latitude")),
        "longitude": clean(row.get("longitude")),
        "url": website,
        "description": description,

        "datatourisme_id": clean(row.get("id")),
        "datatourisme_type": clean(row.get("type")),
        "datatourisme_theme": clean(row.get("theme")),
        "last_update": clean(row.get("lastupdate")),

        "source": "datatourisme",
        "source_name": "DATAtourisme",
        "source_url": "https://www.datatourisme.fr/",
    }

    return {
        "recordid": "datatourisme-" + clean(row.get("id")),
        "fields": fields
    }


def load_paris():
    with open(
        "paris.json",
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    records = data.get("records", [])

    result = []

    for record in records:
        converted = convert_paris_record(record)

        if paris_event(converted):
            result.append(converted)

    return result


def load_datatourisme():
    result = []

    with open(
        "datatourisme-fma.csv",
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:
            city = normalize(row.get("city"))
            postcode = clean(row.get("postalcode"))

            if city != "paris" and not PARIS_POSTCODE_RE.match(postcode):
                continue

            if not clean(row.get("label")):
                continue

            record = convert_datatourisme_row(row)

            result.append(record)

    return result


def main():
    paris_records = load_paris()
    datatourisme_records = load_datatourisme()

    print(
        f"Paris Open Data events: {len(paris_records)}"
    )

    print(
        f"DATAtourisme Paris events: {len(datatourisme_records)}"
    )

    merged = []

    seen = set()

    # Paris Open Data elsőbbséget kap
    for record in paris_records:
        key = paris_key(record)

        if key in seen:
            continue

        seen.add(key)
        merged.append(record)

    # DATAtourisme hozzáadása
    added = 0
    duplicates = 0

    for record in datatourisme_records:
        key = paris_key(record)

        if key in seen:
            duplicates += 1
            continue

        seen.add(key)
        merged.append(record)
        added += 1

    # Dátum szerinti rendezés
    def sort_key(record):
        fields = record.get("fields", {})
        return (
            fields.get("date_start")
            or "9999-12-31"
        )

    merged.sort(key=sort_key)

    output = {
        "records": merged,
        "meta": {
            "generated": datetime.utcnow().isoformat() + "Z",
            "sources": [
                {
                    "id": "paris-open-data",
                    "name": "Paris Open Data / Ville de Paris",
                    "url": "https://opendata.paris.fr/"
                },
                {
                    "id": "datatourisme",
                    "name": "DATAtourisme",
                    "url": "https://www.datatourisme.fr/"
                }
            ]
        }
    }

    with open(
        "events.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"DATAtourisme new events added: {added}"
    )

    print(
        f"Duplicates skipped: {duplicates}"
    )

    print(
        f"Total events: {len(merged)}"
    )


if __name__ == "__main__":
    main()
