import csv
import os
import re
from datetime import datetime

# Directory paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")

# Source files configuration
SOURCE_FILES = {
    "pasha_insurance.csv": {
        "source": "Pasha Insurance",
        "field_mapping": {
            "name": "name",
            "type": "type",
            "address": "address",
            "phone": "phone",
            "latitude": "latitude",
            "longitude": "longitude"
        }
    },
    "aiic.csv": {
        "source": "AIIC",
        "field_mapping": {
            "name": "name",
            "type": "type",
            "address": "address",
            "phone": "phone",
            "latitude": "latitude",
            "longitude": "longitude"
        }
    },
    "ateshgah.csv": {
        "source": "Ateshgah",
        "field_mapping": {
            "name": "name",
            "type": "type",
            "address": "address",
            "phone": "phone",
            "latitude": "latitude",
            "longitude": "longitude"
        }
    },
    "meqa_sigorta.csv": {
        "source": "Meqa Sigorta",
        "field_mapping": {
            "name": "name",
            "type": "type",
            "address": "address",
            "phone": "phone",
            "latitude": "latitude",
            "longitude": "longitude",
            "city": "city"
        }
    },
    "a_group.csv": {
        "source": "A-Group",
        "field_mapping": {
            "name": "name",
            "type": "type",
            "address": "address",
            "phone": "phone",
            "latitude": "latitude",
            "longitude": "longitude"
        }
    }
}

# Type normalization mapping
TYPE_MAPPING = {
    # Standard types
    "PHARMACY": "PHARMACY",
    "CLINIC": "CLINIC",
    "DENTAL": "DENTAL",
    "OPTICS": "OPTICS",

    # Variations
    "ONLINE_PHARMACY": "PHARMACY",
    "MEDICAL_SERVICE": "CLINIC",
    "DENTAL_CLINIC": "DENTAL",
    "OPTIC": "OPTICS",

    # Lowercase variations
    "pharmacy": "PHARMACY",
    "clinic": "CLINIC",
    "dental": "DENTAL",
    "optics": "OPTICS",
}

# Baku districts for city detection
BAKU_DISTRICTS = [
    "Binəqədi", "Xətai", "Xəzər", "Nərimanov", "Nəsimi", "Nizami",
    "Qaradağ", "Sabunçu", "Səbail", "Suraxanı", "Yasamal", "Pirallahı",
    "Bakı", "Baku", "Baki"
]

# Azerbaijan regions/cities
REGIONS = {
    "Sumqayıt": "Sumqayıt",
    "Gəncə": "Gəncə",
    "Mingəçevir": "Mingəçevir",
    "Naxçıvan": "Naxçıvan",
    "Lənkəran": "Lənkəran",
    "Şəki": "Şəki",
    "Şirvan": "Şirvan",
    "Yevlax": "Yevlax",
    "Xaçmaz": "Xaçmaz",
    "Quba": "Quba",
    "Qusar": "Qusar",
    "Zaqatala": "Zaqatala",
    "Masallı": "Masallı",
    "Biləsuvar": "Biləsuvar",
    "İmişli": "İmişli",
    "Salyan": "Salyan",
    "Qəbələ": "Qəbələ",
    "Şamaxı": "Şamaxı",
    "Göyçay": "Göyçay",
    "Ağdaş": "Ağdaş",
    "Bərdə": "Bərdə",
    "Tovuz": "Tovuz",
    "Qazax": "Qazax",
    "Xırdalan": "Absheron",
    "Abşeron": "Absheron",
}


def normalize_type(raw_type):
    """Normalize provider type to standard categories."""
    if not raw_type:
        return "UNKNOWN"

    raw_type = raw_type.strip().upper()
    return TYPE_MAPPING.get(raw_type, TYPE_MAPPING.get(raw_type.lower(), "OTHER"))


def detect_city(address, city_hint=None):
    """Detect city/region from address or city hint."""
    if city_hint and city_hint.strip():
        return city_hint.strip()

    if not address:
        return "Unknown"

    address_upper = address.upper()

    # Check for Baku districts
    for district in BAKU_DISTRICTS:
        if district.upper() in address_upper:
            return "Bakı"

    # Check for regions
    for region_key, region_name in REGIONS.items():
        if region_key.upper() in address_upper:
            return region_name

    # Check for common patterns
    if "ŞƏH" in address_upper or "ŞƏHƏR" in address_upper:
        # Try to extract city name before "şəh" or "şəhəri"
        match = re.search(r'([A-Za-zƏəÜüÖöŞşÇçIıĞğ]+)\s+şəh', address, re.IGNORECASE)
        if match:
            city = match.group(1).strip()
            if city.upper() not in ["BAKI", "BAKI"]:
                return city

    return "Bakı"  # Default to Baku


def detect_region_category(city):
    """Categorize city into Baku or Region."""
    baku_area = ["Bakı", "Baku", "Baki", "Absheron", "Xırdalan"]
    return "Bakı" if city in baku_area else "Region"


def clean_phone(phone):
    """Clean and normalize phone number."""
    if not phone:
        return ""
    # Keep only the first phone number if multiple
    phone = str(phone).split(";")[0].split("/")[0].strip()
    return phone


def clean_name(name):
    """Clean provider name."""
    if not name:
        return ""
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', str(name)).strip()
    return name


def parse_coordinates(lat, lon):
    """Parse and validate coordinates."""
    try:
        lat_f = float(lat) if lat else None
        lon_f = float(lon) if lon else None

        if lat_f is None or lon_f is None:
            return None, None

        # Validate Azerbaijan bounds (approximately)
        if not (38.0 <= lat_f <= 42.0 and 44.0 <= 52.0):
            # Might be swapped
            if 38.0 <= lon_f <= 42.0 and 44.0 <= lat_f <= 52.0:
                lat_f, lon_f = lon_f, lat_f

        return lat_f, lon_f
    except (ValueError, TypeError):
        return None, None


def load_csv(filepath, config):
    """Load and normalize CSV data."""
    records = []
    source = config["source"]
    mapping = config["field_mapping"]

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Extract fields using mapping
                name = clean_name(row.get(mapping.get("name", "name"), ""))
                raw_type = row.get(mapping.get("type", "type"), "")
                address = row.get(mapping.get("address", "address"), "")
                phone = clean_phone(row.get(mapping.get("phone", "phone"), ""))
                lat = row.get(mapping.get("latitude", "latitude"), "")
                lon = row.get(mapping.get("longitude", "longitude"), "")
                city_hint = row.get(mapping.get("city", ""), "")

                # Normalize and validate
                provider_type = normalize_type(raw_type)
                latitude, longitude = parse_coordinates(lat, lon)
                city = detect_city(address, city_hint)
                region_category = detect_region_category(city)

                if name:  # Only add if name exists
                    records.append({
                        "name": name,
                        "type": provider_type,
                        "address": address.strip() if address else "",
                        "phone": phone,
                        "latitude": latitude,
                        "longitude": longitude,
                        "city": city,
                        "region_category": region_category,
                        "source": source
                    })

    except FileNotFoundError:
        print(f"  Warning: File not found - {filepath}")
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")

    return records


def deduplicate_records(records):
    """Remove duplicate records based on name + coordinates."""
    seen = set()
    unique_records = []
    duplicates = 0

    for record in records:
        # Create key based on normalized name and coordinates
        name_key = record["name"].lower().strip()
        lat = record["latitude"]
        lon = record["longitude"]

        # Round coordinates to 4 decimal places for comparison
        lat_key = round(lat, 4) if lat else None
        lon_key = round(lon, 4) if lon else None

        key = (name_key, lat_key, lon_key)

        if key not in seen:
            seen.add(key)
            unique_records.append(record)
        else:
            duplicates += 1

    return unique_records, duplicates


def save_combined_csv(records, filename):
    """Save combined records to CSV."""
    filepath = os.path.join(DATA_DIR, filename)

    fieldnames = [
        "name", "type", "address", "phone",
        "latitude", "longitude", "city", "region_category", "source"
    ]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Saved {len(records)} records to {filepath}")


def main():
    # Set console encoding for Windows
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("Health Insurance Data Combiner")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)

    all_records = []

    # Load all source files
    for filename, config in SOURCE_FILES.items():
        filepath = os.path.join(DATA_DIR, filename)
        print(f"Loading {filename}...")

        records = load_csv(filepath, config)
        print(f"  Loaded {len(records)} records from {config['source']}")
        all_records.extend(records)

    print("-" * 50)
    print(f"Total records loaded: {len(all_records)}")

    # Deduplicate
    unique_records, duplicates = deduplicate_records(all_records)
    print(f"Duplicates removed: {duplicates}")
    print(f"Unique records: {len(unique_records)}")

    # Print summary by source
    print("-" * 50)
    print("Records by source:")
    source_counts = {}
    for record in unique_records:
        source = record["source"]
        source_counts[source] = source_counts.get(source, 0) + 1
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count}")

    # Print summary by type
    print("-" * 50)
    print("Records by type:")
    type_counts = {}
    for record in unique_records:
        ptype = record["type"]
        type_counts[ptype] = type_counts.get(ptype, 0) + 1
    for ptype, count in sorted(type_counts.items()):
        print(f"  {ptype}: {count}")

    # Print summary by region
    print("-" * 50)
    print("Records by region category:")
    region_counts = {}
    for record in unique_records:
        region = record["region_category"]
        region_counts[region] = region_counts.get(region, 0) + 1
    for region, count in sorted(region_counts.items()):
        print(f"  {region}: {count}")

    # Save combined CSV
    print("-" * 50)
    save_combined_csv(unique_records, "combined.csv")

    print("-" * 50)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
