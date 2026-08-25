#!/usr/bin/env python3

import csv
import json
import re
from datetime import datetime
from pathlib import Path


PARIS_FILE = Path("paris.json")
DATATOURISME_FILE = Path("datatourisme-fma.csv")
OUTPUT_FILE = Path("events.json")


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_key(value):
    value = clean(value).lower()
    value = value.replace("\ufeff", "")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def normalize_row(row):
    result = {}

    for key, value in row.items():
        if key is None:
            continue

        normalized = normalize_key(key)
        result[normalized] = clean(value)

    return result


def first_value(row, names):
    for name in names:
        key = normalize_key(name)
        value = clean(row.get(key, ""))

        if value:
            return value

    return ""


def parse_periods(value):
    value = clean(value)

    if not value:
        return []

    periods = []

    for item in value.split("|"):
        item = item.strip()

        if not item:
            continue

        match = re.search(
            r"(\d{4}-\d{2}-\d{2})\s*<->\s*(\d{4}-\d{2}-\d{2})",
            item
        )

        if match:
            periods.append(
                (
                    match.group(1),
                    match.group(2)
                )
            )
            continue

        match = re.search(
            r"(\d{4}-\d{2}-\d{2})",
            item
        )

        if match:
            date_value = match.group(1)

            periods.append(
                (
                    date_value,
                    date_value
                )
            )

    return periods


def extract_url(value):
    value = clean(value)

    if not value:
        return ""

    urls = re.findall(
        r"https?://[^\s|<>\"']+",
        value
    )

    if urls:
        return urls[0].rstrip(".,;)")

    return ""


def extract_city(row):
    value = first_value(
        row,
        [
            "code_postal_et_commune",
            "code_postal_et_commune_",
            "postalcode_city",
            "city",
            "ville"
        ]
    )

    if not value:
        return "Paris"

    if "#" in value:
        parts = value.split("#", 1)

        if len(parts) == 2:
            return clean(parts[1])

    return value


def extract_postal_code(row):
    value = first_value(
        row,
        [
            "code_postal_et_commune",
            "postalcode_city",
            "postalcode",
            "code_postal"
        ]
    )

    if not value:
        return ""

    match = re.search(r"\b(\d{5})\b", value)

    if match:
        return match.group(1)

    if "#" in value:
        return clean(value.split("#", 1)[0])

    return ""


def is_paris_event(row):
    postal_code = extract_postal_code(row)

    if postal_code.startswith("75"):
        return True

    city = extract_city(row).lower()

    paris_names = {
        "paris",
        "paris 1er",
        "paris 2e",
        "paris 3e",
        "paris 4e",
        "paris 5e",
        "paris 6e",
        "paris 7e",
        "paris 8e",
        "paris 9e",
        "paris 10e",
        "paris 11e",
        "paris 12e",
        "paris 13e",
        "paris 14e",
        "paris 15e",
        "paris 16e",
        "paris 17e",
        "paris 18e",
        "paris 19e",
        "paris 20e",
    }

    return city in paris_names or city.startswith("paris ")


def load_paris():
    print("Loading Paris Open Data...")

    with PARIS_FILE.open(
        "r",
        encoding="utf-8"
    ) as handle:
        data = json.load(handle)

    records = data.get("records", [])

    if not isinstance(records, list):
        raise RuntimeError("Paris Open Data: records is not a list")

    print("Paris Open Data:", len(records))

    return records


def load_datatourisme():
    print("Loading DATAtourisme FMA...")

    if not DATATOURISME_FILE.exists():
        raise RuntimeError(
            "DATAtourisme file not found: datatourisme-fma.csv"
        )

    with DATATOURISME_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as handle:

        reader = csv.DictReader(handle)

        if not reader.fieldnames:
            raise RuntimeError(
                "DATAtourisme: CSV header missing"
            )

        print(
            "DATAtourisme columns:",
            reader.fieldnames
        )

        rows = []

        for raw_row in reader:
            row = normalize_row(raw_row)

            title = first_value(
                row,
                [
                    "nom_du_poi",
                    "label",
                    "titre",
                    "nom"
                ]
            )

            periods = first_value(
                row,
                [
                    "periodes_regroupees",
                    "periodes_regroupee",
                    "periods"
                ]
            )

            if not title:
                continue

            if not periods:
                continue

            if not is_paris_event(row):
                continue

            rows.append(row)

    print("DATAtourisme Paris rows:", len(rows))

    return rows


def make_datatourisme_events(rows):
    events = []

    for row in rows:

        title = first_value(
            row,
            [
                "nom_du_poi",
                "label",
                "titre",
                "nom"
            ]
        )

        description = first_value(
            row,
            [
                "description",
                "comment",
                "description_du_poi"
            ]
        )

        address = first_value(
            row,
            [
                "adresse_postale",
                "street",
                "adresse"
            ]
        )

        city = extract_city(row)

        postal_code = extract_postal_code(row)

        latitude = first_value(
            row,
            [
                "latitude",
                "lat"
            ]
        )

        longitude = first_value(
            row,
            [
                "longitude",
                "lon",
                "lng"
            ]
        )

        poi_id = first_value(
            row,
            [
                "uri_id_du_poi",
                "id",
                "uri"
            ]
        )

        contacts = first_value(
            row,
            [
                "contacts_du_poi",
                "website",
                "site_web",
                "url"
            ]
        )

        url = extract_url(contacts)

        if not url and poi_id.startswith("http"):
            url = poi_id

        periods_value = first_value(
            row,
            [
                "periodes_regroupees"
            ]
        )

        periods = parse_periods(periods_value)

        for start_date, end_date in periods:

            event_id = (
                "datatourisme:"
                + (poi_id if poi_id else title)
                + ":"
                + start_date
                + ":"
                + end_date
            )

            event = {
                "recordid": event_id,
                "fields": {
                    "title": title,
                    "date_start": start_date,
                    "date_end": end_date,
                    "address_city": city,
                    "address_postal_code": postal_code,
                    "address_name": address,
                    "description": description,
                    "lead_text": description,
                    "latitude": latitude,
                    "longitude": longitude,
                    "url": url,
                    "source": "DATAtourisme",
                    "source_id": poi_id
                }
            }

            events.append(event)

    return events


def normalize_paris_events(records):
    result = []

    for record in records:

        if not isinstance(record, dict):
            continue

        fields = record.get("fields", {})

        if not isinstance(fields, dict):
            continue

        result.append(record)

    return result


def event_key(event):
    fields = event.get("fields", {})

    title = clean(
        fields.get("title")
        or fields.get("nom")
        or fields.get("name")
    ).lower()

    start = clean(
        fields.get("date_start")
        or fields.get("date_debut")
        or fields.get("date")
    )

    city = clean(
        fields.get("address_city")
        or fields.get("ville")
        or fields.get("city")
    ).lower()

    source = clean(
        fields.get("source")
    ).lower()

    source_id = clean(
        fields.get("source_id")
    )

    if source_id:
        return (
            "source:"
            + source
            + ":"
            + source_id
            + ":"
            + start
        )

    return (
        "event:"
        + title
        + ":"
        + start
        + ":"
        + city
    )


def parse_sort_date(event):
    fields = event.get("fields", {})

    value = clean(
        fields.get("date_start")
        or fields.get("date_debut")
        or fields.get("date")
    )

    try:
        return datetime.strptime(
            value[:10],
            "%Y-%m-%d"
        )
    except Exception:
        return datetime.max


def merge_events(paris_events, datatourisme_events):
    merged = []

    seen = set()

    for event in paris_events + datatourisme_events:

        key = event_key(event)

        if key in seen:
            continue

        seen.add(key)
        merged.append(event)

    merged.sort(
        key=parse_sort_date
    )

    return merged


def main():

    paris_events = load_paris()

    datatourisme_rows = load_datatourisme()

    datatourisme_events = make_datatourisme_events(
        datatourisme_rows
    )

    paris_events = normalize_paris_events(
        paris_events
    )

    print(
        "DATAtourisme generated events:",
        len(datatourisme_events)
    )

    merged = merge_events(
        paris_events,
        datatourisme_events
    )

    output = {
        "records": merged
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as handle:

        json.dump(
            output,
            handle,
            ensure_ascii=False,
            indent=2
        )

        handle.write("\n")

    print(
        "Final events:",
        len(merged)
    )

    print(
        "Written:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
