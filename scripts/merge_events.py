import csv
import json
import re
import unicodedata
from datetime import datetime, timezone

PARIS_POSTCODES = {f"750{i:02d}" for i in range(1, 21)}


def clean(value):
    return "" if value is None else str(value).strip()


def normalize(value):
    value = clean(value).lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(
        c for c in value
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", value)


def is_paris(city="", postalcode=""):
    city = normalize(city)
    postalcode = clean(postalcode)

    return (
        city == "paris"
        or postalcode in PARIS_POSTCODES
    )


def find_column(fieldnames, names):
    normalized = {
        normalize(name): name
        for name in (fieldnames or [])
        if name
    }

    for name in names:
        if normalize(name) in normalized:
            return normalized[normalize(name)]

    return None


def get(row, column):
    return clean(row.get(column)) if column else ""


def event_key(fields):
    return (
        normalize(
            fields.get("title")
            or fields.get("label")
            or ""
        ),
        normalize(
            fields.get("date_start")
            or ""
        ),
        normalize(
            fields.get("address_city")
            or "Paris"
        )
    )


def load_paris():
    with open(
        "paris.json",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    result = []

    for record in data.get("records", []):
        fields = record.get("fields", {})

        city = (
            fields.get("address_city")
            or fields.get("ville")
            or "Paris"
        )

        postalcode = (
            fields.get("postalcode")
            or fields.get("postcode")
            or ""
        )

        if not is_paris(city, postalcode):
            continue

        fields["source"] = "paris-open-data"
        fields["source_name"] = (
            "Paris Open Data / Ville de Paris"
        )
        fields["source_url"] = (
            "https://opendata.paris.fr/"
        )

        result.append({
            "recordid": record.get("recordid"),
            "fields": fields
        })

    return result


def load_datatourisme():
    result = []

    with open(
        "datatourisme-fma.csv",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)
        columns = reader.fieldnames or []

        title = find_column(
            columns,
            ["label", "title", "nom", "name"]
        )

        identifier = find_column(
            columns,
            ["id", "identifier"]
        )

        start = find_column(
            columns,
            [
                "startdate",
                "start_date",
                "date_start",
                "date_debut"
            ]
        )

        end = find_column(
            columns,
            [
                "enddate",
                "end_date",
                "date_end",
                "date_fin"
            ]
        )

        city = find_column(
            columns,
            ["city", "ville", "commune"]
        )

        postalcode = find_column(
            columns,
            [
                "postalcode",
                "postcode",
                "codepostal",
                "code_postal"
            ]
        )

        street = find_column(
            columns,
            ["street", "adresse", "address"]
        )

        latitude = find_column(
            columns,
            ["latitude", "lat"]
        )

        longitude = find_column(
            columns,
            ["longitude", "lon", "lng"]
        )

        website = find_column(
            columns,
            [
                "site web",
                "siteweb",
                "website",
                "web",
                "url"
            ]
        )

        description = find_column(
            columns,
            [
                "comment",
                "description",
                "lead_text"
            ]
        )

        theme = find_column(
            columns,
            ["theme"]
        )

        dtype = find_column(
            columns,
            ["type"]
        )

        last_update = find_column(
            columns,
            [
                "lastupdate",
                "last_update"
            ]
        )

        if not title:
            raise RuntimeError(
                "DATAtourisme: title/label column missing"
            )

        for row in reader:

            row_title = get(row, title)

            if not row_title:
                continue

            row_city = get(row, city)
            row_postalcode = get(row, postalcode)

            if not is_paris(
                row_city,
                row_postalcode
            ):
                continue

            row_id = get(row, identifier)

            fields = {
                "title": row_title,
                "date_start": get(row, start),
                "date_end": get(row, end),
                "address_city": (
                    row_city or "Paris"
                ),
                "postalcode": row_postalcode,
                "address_name": get(row, street),
                "latitude": get(row, latitude),
                "longitude": get(row, longitude),
                "url": get(row, website),
                "description": get(row, description),
                "datatourisme_id": row_id,
                "datatourisme_type": get(row, dtype),
                "datatourisme_theme": get(row, theme),
                "last_update": get(row, last_update),
                "source": "datatourisme",
                "source_name": "DATAtourisme",
                "source_url": (
                    "https://www.datatourisme.fr/"
                )
            }

            record_id = (
                "datatourisme-" + row_id
                if row_id
                else "datatourisme-"
                + normalize(row_title)
                + "-"
                + normalize(
                    get(row, start)
                )
            )

            result.append({
                "recordid": record_id,
                "fields": fields
            })

    return result


def merge(paris, datatourisme):

    result = []
    seen = set()

    for record in paris + datatourisme:

        fields = record.get("fields", {})
        key = event_key(fields)

        if key in seen:
            continue

        seen.add(key)
        result.append(record)

    return result


def sort_key(record):
    fields = record.get("fields", {})

    return (
        fields.get("date_start")
        or "9999-12-31"
    )


def main():

    paris = load_paris()
    datatourisme = load_datatourisme()

    events = merge(
        paris,
        datatourisme
    )

    events.sort(
        key=sort_key
    )

    output = {
        "records": events,
        "meta": {
            "generated": datetime.now(
                timezone.utc
            ).isoformat(),
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
                    "name": "DATAtourisme",
                    "url": (
                        "https://www.datatourisme.fr/"
                    )
                }
            ],
            "event_count": len(events)
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
        f"Paris Open Data: {len(paris)}"
    )

    print(
        f"DATAtourisme: {len(datatourisme)}"
    )

    print(
        f"Total: {len(events)}"
    )


if __name__ == "__main__":
    main()
