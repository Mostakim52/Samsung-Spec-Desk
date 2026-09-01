import pytest
from database import db
from scraper.models import PhoneRecord


def _record(name="Galaxy S23"):
    return PhoneRecord(
        name=name, brand="Samsung", release_date="2023-02-24", image_url="",
        display_size="6.1\"", display_type="Dynamic AMOLED 2X",
        resolution="1080 x 2340", refresh_rate="120Hz", processor="Snapdragon 8 Gen 2",
        ram="8GB", storage="128/256GB", rear_camera="50MP", front_camera="10MP",
        battery_capacity="3900mAh", battery_life="Endurance 86h", os="Android 13",
        price="$799", raw_specs={"sensors": "accelerometer"},
    )


@pytest.fixture(scope="module")
def db_available():
    try:
        conn = db.get_connection()
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _skip_no_db(db_available):
    if not db_available:
        pytest.skip("PostgreSQL not reachable")


@pytest.fixture(scope="module", autouse=True)
def _cleanup_test_records():
    yield
    with db.get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM phones WHERE name = 'Galaxy S23 Test'")


def test_upsert_and_get(db_available):
    db.init_db()
    db.upsert_phone(_record("Galaxy S23 Test"))
    got = db.get_phone_by_name("galaxy s23 test")
    assert got is not None
    assert got.processor == "Snapdragon 8 Gen 2"
    assert got.raw_specs == {"sensors": "accelerometer"}


def test_upsert_idempotent(db_available):
    db.upsert_phone(_record("Galaxy S23 Test"))
    db.upsert_phone(_record("Galaxy S23 Test"))
    assert db.count_phones() >= 1
    got = db.get_phone_by_name("Galaxy S23 Test")
    assert got is not None


def test_fuzzy_lookup(db_available):
    got = db.get_phone_by_name("s23 test")
    assert got is not None and got.name == "Galaxy S23 Test"


def test_missing_returns_none(db_available):
    assert db.get_phone_by_name("nonexistent xyz") is None
