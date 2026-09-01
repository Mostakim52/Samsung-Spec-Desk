import pytest

from agents.crew import PhoneSpecTool, generate_review
from database import db
from scraper import gsmarena


@pytest.fixture(scope="module", autouse=True)
def _ensure_db():
    try:
        conn = db.get_connection()
        conn.close()
    except Exception:
        pytest.skip("PostgreSQL not reachable")
    from database import db as _db

    _db.init_db()
    if _db.count_phones() == 0:
        for record in gsmarena.load_fallback_dataset():
            _db.upsert_phone(record)
    yield


def test_spec_tool_returns_specsheet():
    tool = PhoneSpecTool()
    result = tool._run("Galaxy S23")
    assert "Snapdragon" in result
    assert "Galaxy S23" in result


def test_spec_tool_unknown_phone():
    tool = PhoneSpecTool()
    result = tool._run("nonexistent phone xyz")
    assert "not found" in result.lower()


def test_generate_review_unknown_raises():
    with pytest.raises(LookupError):
        generate_review("nonexistent phone xyz")
