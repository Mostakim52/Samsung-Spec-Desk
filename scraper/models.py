from dataclasses import dataclass, field, asdict


@dataclass
class PhoneRecord:
    name: str
    brand: str
    release_date: str
    image_url: str
    display_size: str
    display_type: str
    resolution: str
    refresh_rate: str
    processor: str
    ram: str
    storage: str
    rear_camera: str
    front_camera: str
    battery_capacity: str
    battery_life: str
    os: str
    price: str
    raw_specs: dict = field(default_factory=dict)

    def to_doc(self) -> str:
        d = asdict(self)
        lines = [f"Samsung {d['name']}"]
        for key, value in d.items():
            if key in ("name", "raw_specs") or not value:
                continue
            lines.append(f"{key.replace('_', ' ').title()}: {value}")
        for key, value in (self.raw_specs or {}).items():
            lines.append(f"{key.title()}: {value}")
        return "\n".join(lines)
