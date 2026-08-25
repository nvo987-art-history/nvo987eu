import csv
import json
import re
from datetime import datetime, timezone


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def split_address(value):
    value = clean(value)

    if "#" in value:
        postal, city = value.split("#", 1)
        return postal.strip(), city.strip()

    match = re.search(r"\b(750\d{2})\b", value)

    if match:
        postal = match.group(1)
        city = value.replace(postal, "").strip(" ,")
        return postal, city

    return "", value


def parse_period(value):
    value = clean(value)

    if not value:
        return "", ""

    dates = re.findall(
        r"\d{4}-\d{2}-\d{2}(?:[T ][0-9:.+\-Z]*)?",
        value
    )

    if not dates:
        return "", ""

    start = dates[0]
    end = dates[1] if len(dates) > 1 else start

    return start, end


def is_paris(postal, city):
    postal = clean(postal)
    city = clean(city).lower()

    return (
        postal.startswith("750")
        or city == "paris"
        or "paris" in city
    )


def load_paris():
    with open(
        "paris.json",
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    events = []

    for record in data.get("records", []):
        fields = record.get("fields", {})

        fields["source"] = "paris-open-data"
        fields["source_name"] = (
            "Paris Open Data / Ville de Paris"
        )
        fields["source_url"] = (
            "https://opendata.paris.fr/"
        )

        events.append({
            "recordid": record.get("recordid"),
            "fields": fields
        })

    return events


def load_datatourisme():

    events = []

    with open(
        "datatourisme-fma.csv",
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        print(
            "DATAtourisme columns:",
            reader.fieldnames
        )

        for row in reader:

            title = clean(
                row.get("Nom_du_POI")
            )

            if not title:
                continue

            postal, city = split_address(
                row.get(
                    "Code_postal_et_commune"
                )
            )

            if not is_paris(
                postal,
                city
            ):
                continue

            start, end = parse_period(
                row.get(
                    "Periodes_regroupees"
                )
            )

            record_id = clean(
                row.get("URI_ID_du_POI")
            )

            if not record_id:
                record_id = (
                    "datatourisme-"
                    + title
                    + "-"
                    + start
                )

            fields = {
                "title": title,

                "date_start": start,

                "date_end": end,

                "address_city": city or "Paris",

                "postalcode": postal,

                "address_name": clean(
                    row.get("Adresse_postale")
                ),

                "latitude": clean(
                    row.get("Latitude")
                ),

                "longitude": clean(
                    row.get("Longitude")
                ),

                "description": clean(
                    row.get("Description")
                ),

                "url": "",

                "datatourisme_id": record_id,

                "categories": clean(
                    row.get("Categories_de_POI")
                ),

                "periods": clean(
                    row.get("Periodes_regroupees")
                ),

                "contacts": clean(
                    row.get("Contacts_du_POI")
                ),

                "last_update": clean(
                    row.get("Date_de_mise_a_jour")
                ),

                "creator": clean(
                    row.get("Createur_de_la_donnee")
                ),

                "diffuser": clean(
                    row.get("SIT_diffuseur")
                ),

                "source": "datatourisme",

                "source_name": "DATAtourisme",

                "source_url": (
                    "https://www.datatourisme.fr/"
                )
            }

            events.append({
                "recordid": record_id,
                "fields": fields
            })

    return events


def event_key(record):

    fields = record.get(
        "fields",
        {}
    )

    title = clean(
        fields.get("title")
        or fields.get("nom")
    ).lower()

    date = clean(
        fields.get("date_start")
    )

    city = clean(
        fields.get("address_city")
    ).lower()

    return (
        title,
        date,
        city
    )


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

        key = event_key(record)

        if key in seen:
            continue

        seen.add(key)
        result.append(record)

    return result


def sort_events(events):

    return sorted(
        events,
        key=lambda record: (
            record.get(
                "fields",
                {}
            ).get(
                "date_start"
            )
            or "9999-12-31"
        )
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

    events = sort_events(events)

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
        "================================"
    )

    print(
        f"Paris Open Data: "
        f"{len(paris_events)}"
    )

    print(
        f"DATAtourisme: "
        f"{len(datatourisme_events)}"
    )

    print(
        f"TOTAL: {len(events)}"
    )

    print(
        "events.json generated."
    )


if __name__ == "__main__":
    main()
```0
