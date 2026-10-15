
#!/usr/bin/env python3

import argparse
import json
import random
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path


FHIR_VERSION = "4.0.1"

RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
LOINC = "http://loinc.org"
UCUM = "http://unitsofmeasure.org"
SNOMED = "http://snomed.info/sct"

SYNTHETIC_MEDICATIONS = [
    {
        "code": "29046",
        "name": "Lisinopril 10 MG Oral Tablet",
        "form_code": "385055001",
        "form": "Tablet",
        "strength": "10 mg",
        "quantity": 30,
        "dosage": "Take one tablet by mouth once daily",
        "frequency": 1,
        "duration": 30,
    },
    {
        "code": "860975",
        "name": "Metformin hydrochloride 500 MG Oral Tablet",
        "form_code": "385055001",
        "form": "Tablet",
        "strength": "500 mg",
        "quantity": 60,
        "dosage": "Take one tablet by mouth twice daily",
        "frequency": 2,
        "duration": 30,
    },
]

FIRST_NAMES = [
    "Alex",
    "Jordan",
    "Morgan",
    "Taylor",
    "Casey",
    "Robin",
]

LAST_NAMES = [
    "Example",
    "Sample",
    "Demo",
    "Test",
    "Synthetic",
]

GENDERS = ["male", "female", "other"]


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resource_id():
    return str(uuid.uuid4())


def resource(resource_type, **fields):
    return {
        "resourceType": resource_type,
        "id": resource_id(),
        **fields,
    }


def reference(item):
    return {
        "reference": f"urn:uuid:{item['id']}",
    }


def coding(system, code, display=None):
    value = {
        "system": system,
        "code": code,
    }

    if display is not None:
        value["display"] = display

    return {"coding": [value]}


def generate_patient(index, rng):
    first = rng.choice(FIRST_NAMES)
    last = rng.choice(LAST_NAMES)
    birth_year = rng.randint(1950, 2000)
    birth_month = rng.randint(1, 12)
    birth_day = rng.randint(1, 28)

    return resource(
        "Patient",
        identifier=[
            {
                "system": "https://example.org/synthetic/patients",
                "value": f"PAT-{index:06d}",
            }
        ],
        name=[
            {
                "use": "official",
                "family": last,
                "given": [first],
            }
        ],
        gender=rng.choice(GENDERS),
        birthDate=date(
            birth_year,
            birth_month,
            birth_day,
        ).isoformat(),
    )


def generate_practitioner(index):
    return resource(
        "Practitioner",
        identifier=[
            {
                "system": "https://example.org/synthetic/practitioners",
                "value": f"DOC-{index:06d}",
            }
        ],
        name=[
            {
                "use": "official",
                "family": "Example",
                "given": ["Jane"],
                "prefix": ["Dr"],
            }
        ],
    )


def generate_medication(template):
    return resource(
        "Medication",
        code=coding(
            RXNORM,
            template["code"],
            template["name"],
        ),
        form=coding(
            SNOMED,
            template["form_code"],
            template["form"],
        ),
    )


def generate_observation(patient, rng):
    weight = round(rng.uniform(55, 105), 1)

    return resource(
        "Observation",
        status="final",
        category=[
            coding(
                "http://terminology.hl7.org/CodeSystem/observation-category",
                "vital-signs",
                "Vital Signs",
            )
        ],
        code=coding(
            LOINC,
            "29463-7",
            "Body weight",
        ),
        subject=reference(patient),
        effectiveDateTime=utc_now(),
        valueQuantity={
            "value": weight,
            "unit": "kg",
            "system": UCUM,
            "code": "kg",
        },
    )


def generate_medication_request(
    patient,
    practitioner,
    medication,
    template,
):
    return resource(
        "MedicationRequest",
        status="active",
        intent="order",
        medicationReference=reference(medication),
        subject=reference(patient),
        requester=reference(practitioner),
        authoredOn=utc_now(),
        dosageInstruction=[
            {
                "text": template["dosage"],
                "timing": {
                    "repeat": {
                        "frequency": template["frequency"],
                        "period": 1,
                        "periodUnit": "d",
                    }
                },
                "route": {
                    "text": "Oral",
                },
            }
        ],
        dispenseRequest={
            "quantity": {
                "value": template["quantity"],
                "unit": "tablet",
                "system": UCUM,
                "code": "{tbl}",
            },
            "expectedSupplyDuration": {
                "value": template["duration"],
                "unit": "days",
                "system": UCUM,
                "code": "d",
            },
            "numberOfRepeatsAllowed": 0,
        },
        substitution={
            "allowedBoolean": True,
        },
    )


def generate_prescription(index, rng):
    patient = generate_patient(index, rng)
    practitioner = generate_practitioner(index)

    selected = rng.choice(SYNTHETIC_MEDICATIONS)

    medication = generate_medication(selected)

    observation = generate_observation(patient, rng)

    request = generate_medication_request(
        patient,
        practitioner,
        medication,
        selected,
    )

    return [
        patient,
        practitioner,
        medication,
        observation,
        request,
    ]


def build_bundle(resources):
    return {
        "resourceType": "Bundle",
        "id": resource_id(),
        "type": "collection",
        "timestamp": utc_now(),
        "entry": [
            {
                "fullUrl": f"urn:uuid:{item['id']}",
                "resource": item,
            }
            for item in resources
        ],
    }


def validate_bundle(bundle):
    if bundle.get("resourceType") != "Bundle":
        raise ValueError("Invalid Bundle resource type")

    if bundle.get("type") != "collection":
        raise ValueError("Invalid Bundle type")

    entries = bundle.get("entry")

    if not isinstance(entries, list) or not entries:
        raise ValueError("Bundle has no entries")

    urls = set()

    for entry in entries:
        item = entry.get("resource")

        if not isinstance(item, dict):
            raise ValueError("Invalid Bundle entry")

        if not item.get("resourceType") or not item.get("id"):
            raise ValueError("Resource type or ID missing")

        expected = f"urn:uuid:{item['id']}"
        actual = entry.get("fullUrl")

        if actual != expected:
            raise ValueError("Resource fullUrl mismatch")

        if actual in urls:
            raise ValueError("Duplicate resource fullUrl")

        urls.add(actual)

    required_references = {
        "Observation": ["subject"],
        "MedicationRequest": [
            "subject",
            "requester",
            "medicationReference",
        ],
    }

    for entry in entries:
        item = entry["resource"]
        kind = item["resourceType"]

        for field in required_references.get(kind, []):
            target = item.get(field, {}).get("reference")

            if target not in urls:
                raise ValueError(
                    f"Unresolved reference in {kind}.{field}"
                )

    return True


def count_resources(bundle):
    counts = {}

    for entry in bundle["entry"]:
        kind = entry["resource"]["resourceType"]
        counts[kind] = counts.get(kind, 0) + 1

    return counts


def generate_bundle(count, seed):
    rng = random.Random(seed)

    resources = []

    for index in range(1, count + 1):
        resources.extend(
            generate_prescription(index, rng)
        )

    bundle = build_bundle(resources)
    validate_bundle(bundle)

    return bundle


def save_bundle(bundle, path, overwrite):
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mode = "w" if overwrite else "x"

    with path.open(mode, encoding="utf-8") as handle:
        json.dump(
            bundle,
            handle,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        handle.write("\n")


def print_summary(bundle, count, destination):
    counts = count_resources(bundle)

    print()
    print("FHIR Creator 3.0")
    print("=" * 52)
    print(f"FHIR version       : R4 ({FHIR_VERSION})")
    print(f"Bundle type        : {bundle['type']}")
    print(f"Prescriptions      : {count}")
    print(f"Total resources    : {len(bundle['entry'])}")
    print(f"Generated UTC      : {bundle['timestamp']}")
    print(f"Output             : {destination}")
    print()

    print("Resource Summary")
    print("-" * 52)

    width = max(len(name) for name in counts)

    for name, total in sorted(counts.items()):
        print(f"{name:<{width}} : {total}")

    print()
    print("Internal reference validation: passed")
    print("Full FHIR conformance validation: not performed")
    print()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate synthetic FHIR R4 prescription bundles"
    )

    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of synthetic prescriptions",
    )

    parser.add_argument(
        "--output",
        default="prescription_fhir.json",
        help="Output JSON filename",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for synthetic data",
    )

    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the FHIR Bundle to standard output",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing output file",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the terminal summary",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.count < 1:
        print(
            "Error: --count must be positive",
            file=sys.stderr,
        )
        return 2

    if args.count > 10000:
        print(
            "Error: --count exceeds the limit of 10000",
            file=sys.stderr,
        )
        return 2

    try:
        bundle = generate_bundle(
            args.count,
            args.seed,
        )

        if args.stdout:
            json.dump(
                bundle,
                sys.stdout,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
            sys.stdout.write("\n")
            return 0

        save_bundle(
            bundle,
            args.output,
            args.overwrite,
        )

        if not args.quiet:
            print_summary(
                bundle,
                args.count,
                args.output,
            )

        return 0

    except (
        ValueError,
        OSError,
        TypeError,
    ) as exc:
        print(
            f"Error: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
