import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

from scraper.models import PhoneRecord

BASE_URL = "https://www.gsmarena.com"
HEADERS = {"User-Agent": "samsung-phone-research-bot/1.0 (personal project)"}

PHONE_SLUGS = {
    "Galaxy S26 Ultra": "samsung_galaxy_s26_ultra_5g-14320",
    "Galaxy S26+": "samsung_galaxy_s26+_5g-14457",
    "Galaxy S26": "samsung_galaxy_s26_5g-14456",
    "Galaxy S26 FE": "samsung_galaxy_s26_fe_5g-14870",
    "Galaxy S25": "samsung_galaxy_s25-13610",
    "Galaxy S24 Ultra": "samsung_galaxy_s24_ultra-12752",
    "Galaxy S24+": "samsung_galaxy_s24_plus-12624",
    "Galaxy S24": "samsung_galaxy_s24-12583",
    "Galaxy S23 Ultra": "samsung_galaxy_s23_ultra-12032",
    "Galaxy S23": "samsung_galaxy_s23-11989",
    "Galaxy S22 Ultra": "samsung_galaxy_s22_ultra-11253",
    "Galaxy S22": "samsung_galaxy_s22-11251",
    "Galaxy S21 Ultra": "samsung_galaxy_s21_ultra-10596",
    "Galaxy S21": "samsung_galaxy_s21-10626",
    "Galaxy Z Fold6": "samsung_galaxy_z_fold6-13073",
    "Galaxy Z Flip6": "samsung_galaxy_z_flip6-13075",
    "Galaxy Z Fold5": "samsung_galaxy_z_fold5-12126",
    "Galaxy Z Flip5": "samsung_galaxy_z_flip5-12125",
    "Galaxy A57": "samsung_galaxy_a57_5g-14379",
    "Galaxy A55": "samsung_galaxy_a55-12439",
    "Galaxy A35": "samsung_galaxy_a35-12437",
    "Galaxy A17": "samsung_galaxy_a17_5g-14041",
    "Galaxy A07": "samsung_galaxy_a07-14066",
}

FALLBACK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "fallback_dataset.json"
)

MAKER_URL = f"{BASE_URL}/samsung-phones-9.php"


def _slug_key(name: str) -> str:
    key = name.lower().replace("+", "plus")
    key = re.sub(r"[^a-z0-9]", "", key)
    return re.sub(r"5g$", "", key)


def resolve_slugs(targets: dict[str, str]) -> dict[str, str]:
    discovered = {}
    for page_url in _maker_page_urls(MAKER_URL):
        try:
            response = requests.get(page_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
        except Exception as exc:
            print(f"WARN could not load maker page {page_url}: {exc}")
            continue
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.select(".module-phones-link[href], li a[href*='samsung_']"):
            href = link.get("href", "")
            title = link.get_text(" ", strip=True)
            if not href or "samsung_" not in href or "phones-9" in href:
                continue
            match = re.search(r"([a-z0-9_+]+-\d+)\.php", href)
            if not match:
                continue
            key = _slug_key(title.replace("Samsung", "", 1))
            discovered.setdefault(key, match.group(1))
    resolved = {}
    for name, fallback_slug in targets.items():
        key = _slug_key(name)
        resolved[name] = discovered.get(key, fallback_slug)
    return resolved


def _maker_page_urls(first_page: str, max_pages: int = 12) -> list[str]:
    urls = [first_page]
    try:
        response = requests.get(first_page, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        last = 1
        for link in soup.select("a[href]"):
            match = re.search(r"-p(\d+)\.php", link.get("href", ""))
            if match:
                last = max(last, min(int(match.group(1)), max_pages))
        for page in range(2, last + 1):
            urls.append(f"{BASE_URL}/samsung-phones-f-9-0-p{page}.php")
    except Exception:
        pass
    return urls


def _clean(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace(" ,", ",")


def _spec(soup: BeautifulSoup, name: str) -> str:
    node = soup.find(attrs={"data-spec": name})
    if node is None:
        return ""
    return _clean(node.get_text(" ", strip=True))


def _title(soup: BeautifulSoup) -> str:
    node = soup.find("h1", class_="specs-phone-name-title")
    if not node:
        node = soup.find("h1")
    title = node.get_text(strip=True) if node else ""
    return re.sub(r"^Samsung\s+", "", title, flags=re.I)


def _image_url(soup: BeautifulSoup) -> str:
    node = soup.find("div", class_="specs-photo-main")
    if node:
        img = node.find("img")
        if img and img.get("src"):
            return img["src"]
    return ""


def _price(soup: BeautifulSoup) -> str:
    price = _spec(soup, "price")
    if price:
        return price
    match = re.search(r"([$€£₹][\d,\.]+)", soup.get_text(" ", strip=True))
    return match.group(1) if match else ""


def _brief_field(soup: BeautifulSoup, name: str) -> str:
    node = soup.find(attrs={"data-spec": name})
    return _clean(node.get_text(" ", strip=True)) if node else ""


def _extra_specs(soup: BeautifulSoup) -> dict:
    extras = {}
    for name in (
        "dimensions", "weight", "build", "sim", "bodyother", "displayprotection",
        "cpu", "gpu", "memoryslot", "memoryother", "cam1features", "cam1video",
        "cam2features", "cam2video", "wlan", "bluetooth", "gps", "nfc", "radio",
        "usb", "sensors", "featuresother", "batdescription1", "sar-us", "sar-eu",
        "models", "colors", "tbench",
    ):
        value = _spec(soup, name)
        if value:
            extras[name] = value
    charging = soup.find(string=re.compile("wired", re.I))
    if charging:
        node = charging.find_parent("td")
        if node:
            extras["charging"] = _clean(node.get_text(" ", strip=True))
    return extras


def parse_phone_page(html: str) -> PhoneRecord:
    soup = BeautifulSoup(html, "html.parser")
    name = _title(soup)
    display_size = _spec(soup, "displaysize")
    battery_type = _spec(soup, "batdescription1")
    return PhoneRecord(
        name=name,
        brand="Samsung",
        release_date=_spec(soup, "status") or _spec(soup, "year"),
        image_url=_image_url(soup),
        display_size=display_size,
        display_type=_spec(soup, "displaytype"),
        resolution=_spec(soup, "displayresolution"),
        refresh_rate="120Hz" if "120hz" in _spec(soup, "displaytype").lower() else "",
        processor=_spec(soup, "chipset"),
        ram=_spec(soup, "internalmemory"),
        storage=_spec(soup, "internalmemory"),
        rear_camera=_spec(soup, "cam1modules"),
        front_camera=_spec(soup, "cam2modules"),
        battery_capacity=battery_type,
        battery_life=_brief_field(soup, "batlife2") or _spec(soup, "batlife1"),
        os=_spec(soup, "os"),
        price=_price(soup),
        raw_specs=_extra_specs(soup),
    )


def scrape_phone(name: str, slug: str) -> PhoneRecord:
    url = f"{BASE_URL}/{slug}.php"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return parse_phone_page(response.text)


def scrape_all(delay: float = 2.0) -> list[PhoneRecord]:
    try:
        slugs = resolve_slugs(PHONE_SLUGS)
    except Exception as exc:
        print(f"WARN slug discovery failed ({exc}); using stored slugs")
        slugs = dict(PHONE_SLUGS)
    records, failures = [], []
    for name, slug in slugs.items():
        try:
            record = scrape_phone(name, slug)
            if _slug_key(record.name) != _slug_key(name):
                raise ValueError(
                    f"page for slug {slug} returned '{record.name}', expected '{name}'"
                )
            records.append(record)
            print(f"OK {name}")
        except Exception as exc:
            failures.append((name, str(exc)))
            print(f"FAILED {name}: {exc}")
        time.sleep(delay)
    print(f"Scraped {len(records)}/{len(slugs)} phones")
    return records


def save_fallback_dataset(records: list[PhoneRecord]):
    os.makedirs(os.path.dirname(os.path.abspath(FALLBACK_PATH)), exist_ok=True)
    payload = [r.__dict__ for r in records]
    with open(FALLBACK_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_fallback_dataset() -> list[PhoneRecord]:
    path = os.path.abspath(FALLBACK_PATH)
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    return [PhoneRecord(**p) for p in payload]


if __name__ == "__main__":
    scraped = scrape_all()
    if scraped:
        save_fallback_dataset(scraped)
        from database import db

        db.init_db()
        for record in scraped:
            db.upsert_phone(record)
        print(f"Saved {len(scraped)} records to DB and fallback dataset")
