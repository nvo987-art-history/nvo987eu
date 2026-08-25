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
    if not fieldnames:
        return None

    normalized = {
        normalize(name): name
        for name in fieldnames
        if name
    }

    for name in names:
        key = normalize(name)

        if key in normalized:
            return normalized[key]

    return None


def get_value(row, column):
    if not column:
        return ""

    return clean(row.get(column))


def event_key(fields):
    return (
        normalize(fields.get("title")),
        normalize(fields.get("date_start")),
        normalize(fields.get("address_city"))
    )


def load_paris():

    with open(
        "paris.json",
        "r",
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
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)
        columns = reader.fieldnames or []

        print(
            "DATAtourisme columns:",
            columns
        )

        id_col = find_column(
            columns,
            ["id", "identifier"]
        )

        label_col = find_column(
            columns,
            ["label", "title", "nom", "name"]
        )

        type_col = find_column(
            columns,
            ["type"]
        )

        theme_col = find_column(
            columns,
            ["theme"]
        )

        start_col = find_column(
            columns,
            [
                "startdate",
                "start_date",
                "date_start",
                "date_debut"
            ]
        )

        end_col = find_column(
            columns,
            [
                "enddate",
                "end_date",
                "date_end",
                "date_fin"
            ]
        )

        street_col = find_column(
            columns,
            [
                "street",
                "adresse",
                "address"
            ]
        )

        postal_col = find_column(
            columns,
            [
                "postalcode",
                "postcode",
                "codepostal",
                "code_postal"
            ]
        )

        city_col = find_column(
            columns,
            [
                "city",
                "ville",
                "commune"
            ]
        )

        insee_col = find_column(
            columns,
            ["insee"]
        )

        latitude_col = find_column(
            columns,
            ["latitude", "lat"]
        )

        longitude_col = find_column(
            columns,
            ["longitude", "lon", "lng"]
        )

        website_col = find_column(
            columns,
            [
                "site web",
                "siteweb",
                "website",
                "web",
                "url"
            ]
        )

        lastupdate_col = find_column(
            columns,
            [
                "lastupdate",
                "last_update"
            ]
        )

        comment_col = find_column(
            columns,
            [
                "comment",
                "description",
                "lead_text"
            ]
        )

        if not label_col:
            raise RuntimeError(
                "DATAtourisme: label column not found. "
                f"Columns found: {columns}"
            )

        for row in reader:

            title = get_value(
                row,
                label_col
            )

            if not title:
                continue

            city = get_value(
                row,
                city_col
            )

            postalcode = get_value(
                row,
                postal_col
            )

            if not is_paris(
                city,
                postalcode
            ):
                continue

            fields = {
                "title": title,

                "date_start": get_value(
                    row,
                    start_col
                ),

                "date_end": get_value(
                    row,
                    end_col
                ),

                "address_city": city or "Paris",

                "postalcode": postalcode,

                "address_name": get_value(
                    row,
                    street_col
                ),

                "latitude": get_value(
                    row,
                    latitude_col
                ),

                "longitude": get_value(
                    row,
                    longitude_col
                ),

                "url": get_value(
                    row,
                    website_col
                ),

                "description": get_value(
                    row,
                    comment_col
                ),

                "datatourisme_id": get_value(
                    row,
                    id_col
                ),

                "datatourisme_type": get_value(
                    row,
                    type_col
                ),

                "datatourisme_theme": get_value(
                    row,
                    theme_col
                ),

                "insee": get_value(
                    row,
                    insee_col
                ),

                "last_update": get_value(
                    row,
                    lastupdate_col
                ),

                "source": "datatourisme",

                "source_name": "DATAtourisme",

                "source_url": (
                    "https://www.datatourisme.fr/"
                )
            }

            record_id = get_value(
                row,
                id_col
            )

            if record_id:
                record_id = (
                    "datatourisme-"
                    + record_id
                )
            else:
                record_id = (
                    "datatourisme-"
                    + normalize(title)
                    + "-"
                    + normalize(
                        fields["date_start"]
                    )
                )

            result.append({
                "recordid": record_id,
                "fields": fields
            })

    return result


def merge_events(
    paris_events,
    datatourisme_events
):

    result = []
    seen = set()

    for record in (
        paris_events
        + datatourisme_events
    ):

        fields = record.get(
            "fields",
            {}
        )

        key = event_key(fields)

        if key in seen:
            continue

        seen.add(key)
        result.append(record)

    return result


def sort_key(record):

    fields = record.get(
        "fields",
        {}
    )

    return (
        fields.get("date_start")
        or "9999-12-31"
    )


def main():

    print(
        "Loading Paris Open Data..."
    )

    paris_events = load_paris()

    print(
        f"Paris Open Data: "
        f"{len(paris_events)}"
    )

    print(
        "Loading DATAtourisme FMA..."
    )

    datatourisme_events = (
        load_datatourisme()
    )

    print(
        f"DATAtourisme Paris: "
        f"{len(datatourisme_events)}"
    )

    events = merge_events(
        paris_events,
        datatourisme_events
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
        f"TOTAL EVENTS: {len(events)}"
    )


if __name__ == "__main__":
    main()
