import json
import os
from typing import Optional

import psycopg2

from scraper.models import PhoneRecord

_DATABASE_URL = None


def _database_url():
    global _DATABASE_URL
    if _DATABASE_URL is None:
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        name = os.getenv("POSTGRES_DB", "samsung_phones")
        _DATABASE_URL = f"host={host} port={port} user={user} password={password} dbname={name}"
    return _DATABASE_URL


def get_connection():
    return psycopg2.connect(_database_url())


def init_db():
    path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(path) as f, get_connection() as conn, conn.cursor() as cur:
        cur.execute(f.read())


def upsert_phone(record: PhoneRecord) -> int:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO phones (name, brand, release_date, image_url) VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (name) DO UPDATE SET brand=EXCLUDED.brand, "
            "release_date=EXCLUDED.release_date, image_url=EXCLUDED.image_url "
            "RETURNING phone_id",
            (record.name, record.brand, record.release_date, record.image_url),
        )
        phone_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO specifications (phone_id, display_size, display_type, resolution, "
            "refresh_rate, processor, ram, storage, rear_camera, front_camera, "
            "battery_capacity, battery_life, os, price, raw_specs) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (phone_id) DO UPDATE SET display_size=EXCLUDED.display_size, "
            "display_type=EXCLUDED.display_type, resolution=EXCLUDED.resolution, "
            "refresh_rate=EXCLUDED.refresh_rate, processor=EXCLUDED.processor, "
            "ram=EXCLUDED.ram, storage=EXCLUDED.storage, rear_camera=EXCLUDED.rear_camera, "
            "front_camera=EXCLUDED.front_camera, battery_capacity=EXCLUDED.battery_capacity, "
            "battery_life=EXCLUDED.battery_life, os=EXCLUDED.os, price=EXCLUDED.price, "
            "raw_specs=EXCLUDED.raw_specs",
            (phone_id, record.display_size, record.display_type, record.resolution,
             record.refresh_rate, record.processor, record.ram, record.storage,
             record.rear_camera, record.front_camera, record.battery_capacity,
             record.battery_life, record.os, record.price,
             json.dumps(record.raw_specs)),
        )
    return phone_id


def _row_to_record(cur, row) -> PhoneRecord:
    keys = [d[0] for d in cur.description]
    data = dict(zip(keys, row))
    data.pop("phone_id", None)
    data.pop("spec_id", None)
    raw = data.pop("raw_specs", None)
    rec = PhoneRecord(**data)
    rec.raw_specs = raw if isinstance(raw, dict) else json.loads(raw or "{}")
    return rec


def get_phone_by_name(name: str) -> Optional[PhoneRecord]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT p.phone_id, p.name, p.brand, p.release_date, p.image_url, s.* "
            "FROM phones p JOIN specifications s ON s.phone_id = p.phone_id "
            "WHERE p.name ILIKE %s ORDER BY p.name LIMIT 1",
            (f"%{name}%",),
        )
        row = cur.fetchone()
        return _row_to_record(cur, row) if row else None


def get_all_phones() -> list[PhoneRecord]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT p.phone_id, p.name, p.brand, p.release_date, p.image_url, s.* "
            "FROM phones p JOIN specifications s ON s.phone_id = p.phone_id "
            "ORDER BY p.name"
        )
        return [_row_to_record(cur, row) for row in cur.fetchall()]


def count_phones() -> int:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM phones")
        return cur.fetchone()[0]
