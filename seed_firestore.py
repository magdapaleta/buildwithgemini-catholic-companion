# Copyright 2026 Google LLC
# Seed script for Catholic Companion / Oiramen Firestore database

import datetime
from google.cloud import firestore

# Hardcode project ID as a string literal (crucial for Agent Platform deployment)
PROJECT_ID = "qwiklabs-gcp-04-cbd6b324d319"

SEEDED_ITEMS = [
    {
        "user_name": "Maria",
        "language": "es",
        "category": "health/family",
        "person": "mamá",
        "event": "cirugía de cadera el viernes",
        "target_date": "2026-10-02",
        "original_request": "Estoy muy preocupada porque mi mamá tendrá una cirugía el viernes, por favor oremos por ella.",
        "status": "active",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "user_name": "Carlos",
        "language": "es",
        "category": "work/provisions",
        "person": "Carlos",
        "event": "entrevista de trabajo importante",
        "target_date": "2026-09-30",
        "original_request": "Tengo una entrevista de trabajo mañana por la mañana y necesito paz en mi corazón.",
        "status": "active",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "user_name": "David",
        "language": "en",
        "category": "health/recovery",
        "person": "David",
        "event": "medical recovery and test results",
        "target_date": "2026-10-05",
        "original_request": "Please pray for healing as I await my medical test results next week.",
        "status": "active",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "user_name": "Sarah",
        "language": "en",
        "category": "thanksgiving/family",
        "person": "baby nephew Lucas",
        "event": "safe delivery and baptism",
        "target_date": "2026-10-04",
        "original_request": "Giving thanks to God for the safe birth of my nephew Lucas and praying for his upcoming baptism.",
        "status": "active",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
]


def seed_database():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection("prayer_intentions")

    print(f"Seeding {len(SEEDED_ITEMS)} sample prayer intentions...")
    for item in SEEDED_ITEMS:
        doc_ref = collection.document()
        item_copy = dict(item)
        item_copy["id"] = doc_ref.id
        doc_ref.set(item_copy)
        print(f"  [+] Seeded intention for {item['user_name']}: {item['event']} (Doc ID: {doc_ref.id})")

    print("\nFirestore seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
