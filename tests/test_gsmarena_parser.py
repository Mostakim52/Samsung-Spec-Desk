import os

from scraper import gsmarena


def test_fallback_dataset_loads_and_valid():
    records = gsmarena.load_fallback_dataset()
    assert len(records) >= 10
    for r in records:
        assert r.name and r.display_size and r.processor and r.battery_capacity


def test_parse_phone_page_from_fixture():
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "gsmarena_s26.html")
    with open(fixture, encoding="utf-8") as f:
        html = f.read()
    record = gsmarena.parse_phone_page(html)
    assert record.name == "Galaxy S26"
    assert "Snapdragon 8 Elite Gen 5" in record.processor
    assert record.display_size.startswith("6.3")
    assert "4300 mAh" in record.battery_capacity
    assert "12 MP" in record.rear_camera
    assert record.price.startswith("$")
    assert "Android 16" in record.os


def test_fixture_extensive_details():
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "gsmarena_s26.html")
    with open(fixture, encoding="utf-8") as f:
        html = f.read()
    record = gsmarena.parse_phone_page(html)
    extras = record.raw_specs
    assert "Oryon" in extras["cpu"]
    assert "Adreno" in extras["gpu"]
    assert "149.6 x 71.7 x 7.2 mm" in extras["dimensions"]
    assert "167 g" in extras["weight"]
    assert "AnTuTu" in extras["tbench"]
    assert "25W wired" in extras["charging"]
    assert "Wi-Fi 802.11 a/b/g/n/ac/6e/7" in extras["wlan"]
    assert "5.4" in extras["bluetooth"]
    assert "under display" in extras["sensors"]
    assert "Active use score" in record.battery_life
    assert "SM-S942B" in extras["models"]
    assert "Cobalt Violet" in extras["colors"]
