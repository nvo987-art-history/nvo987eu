#!/usr/bin/env python3

import json
from pathlib import Path


PARIS_FILE = Path("paris.json")
IDF_FILE = Path("iledefrance.json")
OUTPUT_FILE = Path("events.json")


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def get_paris_events():
    with PARIS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    records = data.get("records", [])

    if not isinstance(records, list):
        raise RuntimeError(
            "Paris Open Data: invalid records"
        )

    return records


def get_idf_events():
    with IDF_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    records = data.get("results", [])

    if not isinstance(records, list):
        raise RuntimeError(
            "Île-de-France: invalid results"
        )

    return records


def get_first_timing(record):
    timings = record.get("timings")

    if not isinstance(timings, list):
        return None

    if not timings:
        return None

    timing = timings[0]

    if not isinstance(timing, dict):
        return None

    return timing


def convert_idf_event(record):
    title = clean(
        record.get("title")
    )

    if not title:
        return None

    timing = get_first_timing(record)

    date_start = ""
    date_end = ""

    if timing:
        date_start = clean(
            timing.get("begin")
        )

        date_end = clean(
            timing.get("end")
        )

    geo = record.get("geo")

    if not isinstance(geo, dict):
        geo = {}

    links = record.get("links")

    url = ""

    if isinstance(links, list):
        for link in links:
            if isinstance(link, dict):
                candidate = clean(
                    link.get("url")
                    or link.get("href")
                )

                if candidate:
                    url = candidate
                    break

    elif isinstance(links, dict):
        url = clean(
            links.get("url")
            or links.get("href")
        )

    return {
        "recordid": (
            "idf:"
            + clean(record.get("uid"))
        ),

        "fields": {
            "title": title,

            "date_start": date_start,

            "date_end": date_end,

            "address_city": clean(
                record.get("location_city")
            ),

            "address_postal_code": clean(
                record.get("location_postalcode")
            ),

            "address_name": clean(
                record.get("location_name")
            ),

            "address": clean(
                record.get("location_address")
            ),

            "description": clean(
                record.get("description")
            ),

            "lead_text": clean(
                record.get("description")
            ),

            "url": url,

            "latitude": geo.get("lat"),

            "longitude": geo.get("lon"),

            "source": "iledefrance",

            "source_name": (
                "Région Île-de-France"
            ),

            "source_dataset": (
                "Mon été, ma région"
            ),

            "source_url": (
                "https://opendata.iledefrance.fr/"
            ),

            "source_id": clean(
                record.get("uid")
            ),

            "slug": clean(
                record.get("slug")
            ),

            "category": record.get(
                "thematique_de_votre_evenement_label"
            ),

            "event_type": record.get(
                "nature_de_votre_evenements_label"
            ),

            "conditions": clean(
                record.get("conditions")
            ),

            "registration": record.get(
                "registration"
            ),

            "image": clean(
                record.get("image_full_url")
            )
        }
    }


def event_key(event):
    fields = event.get(
        "fields",
        {}
    )

    source = clean(
        fields.get("source")
    )

    source_id = clean(
        fields.get("source_id")
    )

    if source_id:
        return (
            source,
            source_id
        )

    title = clean(
        fields.get("title")
    ).lower()

    date_start = clean(
        fields.get("date_start")
    )

    city = clean(
        fields.get("address_city")
    ).lower()

    return (
        title,
        date_start,
        city
    )


def merge_events(
    paris_events,
    idf_events
):
    merged = []

    seen = set()

    for event in (
        paris_events
        + idf_events
    ):
        key = event_key(event)

        if key in seen:
            continue

        seen.add(key)

        merged.append(event)

    return merged


def sort_events(events):
    def sort_key(event):
        fields = event.get(
            "fields",
            {}
        )

        return clean(
            fields.get("date_start")
        ) or "9999-12-31"

    return sorted(
        events,
        key=sort_key
    )


def main():

    paris_events = (
        get_paris_events()
    )

    idf_records = (
        get_idf_events()
    )

    idf_events = []

    for record in idf_records:

        event = convert_idf_event(
            record
        )

        if event is not None:
            idf_events.append(event)

    merged = merge_events(
        paris_events,
        idf_events
    )

    merged = sort_events(
        merged
    )

    output = {
        "records": merged
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

        file.write("\n")

    print(
        "Paris Open Data:",
        len(paris_events)
    )

    print(
        "Région Île-de-France:",
        len(idf_events)
    )

    print(
        "Total:",
        len(merged)
    )

    print(
        "events.json created."
    )


if __name__ == "__main__":
    main()
