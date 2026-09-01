CREATE TABLE IF NOT EXISTS phones (
    phone_id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    brand TEXT,
    release_date TEXT,
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS specifications (
    spec_id SERIAL PRIMARY KEY,
    phone_id INTEGER NOT NULL REFERENCES phones(phone_id) ON DELETE CASCADE,
    display_size TEXT, display_type TEXT, resolution TEXT, refresh_rate TEXT,
    processor TEXT, ram TEXT, storage TEXT, rear_camera TEXT, front_camera TEXT,
    battery_capacity TEXT, battery_life TEXT, os TEXT, price TEXT,
    raw_specs JSONB DEFAULT '{}',
    UNIQUE (phone_id)
);
