#!/usr/bin/env python3

import json
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen


PARIS_FILE = Path("paris.json")
OUTPUT_FILE = Path("events.json")

IDF_API = (
    "https://opendata.iledefrance.fr/api/explore/v2.1/"
    "catalog/datasets/mon-ete-ma-region/records"
)

IDF_LIMIT = 100


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def first_value(record, names):
    for name in names:
        value = record.get(name)

        if value not in (None, ""):
            return value

    return ""


def load_json(path):
    with path.open(
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def load_paris_events():
    print("Loading Paris Open Data...")

    data = load_json(PARIS_FILE)

    records = data.get("records", [])

    if not isinstance(records, list):
        raise RuntimeError(
            "Paris Open Data: invalid records structure"
        )

    print(
        "Paris Open Data:",
        len(records)
    )

    return records


def load_idf_events():
    print(
        "Loading Région Île-de-France..."
    )

    params = (
        "?limit="
        + str(IDF_LIMIT)
        + "&where=past%3Dfalse"
    )

    url = IDF_API + params

    request = Request(
        url,
        headers={
            "User-Agent": "NVO987.eu/1.0"
        }
    )

    with urlopen(
        request,
        timeout=60
    ) as response:

        data = json.load(response)

    records = data.get("results", [])

    if not isinstance(records, list):
        raise RuntimeError(
            "Île-de-France API: invalid results structure"
        )

    print(
        "Île-de-France events:",
        len(records)
    )

    return records


def convert_idf_event(record):
    title = clean(
        first_value(
            record,
            [
                "title",
                "titre",
                "name",
                "nom"
            ]
        )
    )

    if not title:
        return None

    description = clean(
        first_value(
            record,
            [
                "description",
                "descriptif",
                "description_evenement"
            ]
        )
    )

    start = clean(
        first_value(
            record,
            [
                "date_start",
                "date_debut",
                "start_date",
                "date"
            ]
        )
    )

    end = clean(
        first_value(
            record,
            [
                "date_end",
                "date_fin",
                "end_date"
            ]
        )
    )

    city = clean(
        first_value(
            record,
            [
                "city",
                "ville",
                "commune",
                "nom_commune"
            ]
        )
    )

    address = clean(
        first_value(
            record,
            [
                "address",
                "adresse",
                "adresse_postale"
            ]
        )
    )

    url = clean(
        first_value(
            record,
            [
                "url",
                "website",
                "site_web",
                "lien"
            ]
        )
    )

    event_id = clean(
        first_value(
            record,
            [
                "id",
                "recordid",
                "identifiant"
            ]
        )
    )

    if not event_id:
        event_id = (
            title
            + "|"
            + start
            + "|"
            + city
        )

    return {
        "recordid": (
            "idf:"
            + event_id
        ),
        "fields": {
            "title": title,
            "date_start": start,
            "date_end": end,
            "address_city": city,
            "address_name": address,
            "description": description,
            "lead_text": description,
            "url": url,

            "source": (
                "region-ile-de-france"
            ),

            "source_name": (
                "Région Île-de-France"
            ),

            "source_url": (
                "https://opendata.iledefrance.fr/"
            ),

            "license": (
                "Licence Ouverte / "
                "Open Licence 2.0"
            )
        }
    }


def event_key(event):
    fields = event.get(
        "fields",
        {}
    )

    title = clean(
        fields.get("title")
    ).lower()

    start = clean(
        fields.get("date_start")
    )

    city = clean(
        fields.get("address_city")
    ).lower()

    return (
        title,
        start,
        city
    )


def merge_events(
    paris_events,
    idf_events
):
    result = []
    seen = set()

    for event in (
        paris_events
        + idf_events
    ):
        key = event_key(event)

        if key in seen:
            continue

        seen.add(key)
        result.append(event)

    return result


def sort_events(events):

    def sort_key(event):
        fields = event.get(
            "fields",
            {}
        )

        date = clean(
            fields.get("date_start")
        )

        if not date:
            return "9999-12-31"

        return date[:10]

    return sorted(
        events,
        key=sort_key
    )


def main():

    paris_events = (
        load_paris_events()
    )

    idf_records = (
        load_idf_events()
    )

    idf_events = []

    for record in idf_records:

        event = convert_idf_event(
            record
        )

        if event is not None:
            idf_events.append(
                event
            )

    print(
        "Converted Île-de-France:",
        len(idf_events)
    )

    merged = merge_events(
        paris_events,
        idf_events
    )

    merged = sort_events(
        merged
    )

    output = {
        "records": merged,

        "meta": {
            "generated": (
                datetime.utcnow()
                .isoformat()
                + "Z"
            ),

            "sources": [
                {
                    "name": (
                        "Paris Open Data / "
                        "Ville de Paris"
                    ),
                    "url": (
                        "https://opendata.paris.fr/"
                    )
                },
                {
                    "name": (
                        "Région Île-de-France"
                    ),
                    "url": (
                        "https://opendata.iledefrance.fr/"
                    ),
                    "dataset": (
                        "Mon été, ma région"
                    )
                }
            ],

            "event_count": len(merged)
        }
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

        f.write("\n")

    print(
        "=============================="
    )

    print(
        "Paris:",
        len(paris_events)
    )

    print(
        "Île-de-France:",
        len(idf_events)
    )

    print(
        "TOTAL:",
        len(merged)
    )

    print(
        "events.json created."
    )


if __name__ == "__main__":
    main()
