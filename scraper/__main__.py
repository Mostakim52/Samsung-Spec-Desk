from scraper.gsmarena import scrape_all
from scraper.gsmarena import save_fallback_dataset
from database import db

records = scrape_all()
if records:
    save_fallback_dataset(records)
    db.init_db()
    for record in records:
        db.upsert_phone(record)
    print(f"Saved {len(records)} records to DB and fallback dataset")
else:
    print("No records scraped — keeping existing fallback dataset")
