import requests
import csv
import re
import json
import os
import urllib3
from datetime import datetime

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.meqasigorta.az/medical"
PAGES = {
    "pharmacy-and-optics": "PHARMACY",
    "dental-clinics": "DENTAL",
    "clinics": "CLINIC"
}

# City ID to name mapping (extracted from the page)
CITIES = {
    "28": "Bakı",
    "29": "Sumqayıt",
    "30": "Gəncə",
    "31": "Mingəçevir",
    "32": "Naxçıvan",
    "33": "Zaqatala",
    "34": "Xaçmaz",
    "35": "Biləsuvar",
    "36": "Qəbələ",
    "37": "Lənkəran",
    "38": "Səmkir",
    "39": "Qusar",
    "40": "Quba",
    "41": "Xırdalan",
    "42": "Göyçay",
    "43": "Ağdaş",
    "44": "Şirvan",
    "45": "Şəki",
    "46": "Qazax",
    "47": "Bərdə",
}

# Output directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_page(page_name):
    """Fetch HTML page content."""
    url = f"{BASE_URL}/{page_name}"
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
            verify=False
        )
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {page_name}: {e}")
        return None


def extract_med_points(html_content):
    """Extract medPoints array from JavaScript in HTML."""
    if not html_content:
        return []

    # Find the medPoints array in the script
    pattern = r'const\s+medPoints\s*=\s*\[(.*?)\];'
    match = re.search(pattern, html_content, re.DOTALL)

    if not match:
        print("Could not find medPoints in HTML")
        return []

    # Extract the array content
    array_content = match.group(1)

    # Parse each object in the array
    records = []
    # Pattern to match individual objects
    obj_pattern = r'\{([^}]+)\}'

    for obj_match in re.finditer(obj_pattern, array_content):
        obj_str = obj_match.group(1)
        record = {}

        # Extract fields
        fields = {
            'title': r'title:\s*"([^"]*)"',
            'city': r'city:\s*(\d+)',
            'lat': r'lat:\s*"([^"]*)"',
            'lng': r'lng:\s*"([^"]*)"',
            'address': r'address:\s*"([^"]*)"',
            'phone': r'phone:\s*"([^"]*)"',
            'description': r'description:\s*"([^"]*)"',
            'whatsapp': r'whatsapp:\s*"([^"]*)"',
            'single_phone_number': r'single_phone_number:\s*"([^"]*)"',
        }

        for field_name, field_pattern in fields.items():
            field_match = re.search(field_pattern, obj_str)
            if field_match:
                record[field_name] = field_match.group(1)
            else:
                record[field_name] = ""

        if record.get('title'):  # Only add if we have a title
            records.append(record)

    return records


def extract_working_hours(html_content):
    """Extract working hours from HTML cards."""
    if not html_content:
        return {}

    hours_map = {}
    # Pattern to match working hours in cards
    card_pattern = r'data-marker-index="(\d+)".*?med-point-title">([^<]+)</h5>.*?(?:İş saatları:</strong>\s*<span>([^<]+)</span>)?'

    for match in re.finditer(card_pattern, html_content, re.DOTALL):
        index = int(match.group(1))
        hours = match.group(3) if match.group(3) else ""
        hours_map[index] = hours

    return hours_map


def process_records(records, record_type, working_hours):
    """Process and enrich records with type and city name."""
    processed = []
    for i, record in enumerate(records):
        city_id = record.get('city', '')
        city_name = CITIES.get(str(city_id), '')
        hours = working_hours.get(i, '')

        processed.append({
            'name': record.get('title', ''),
            'type': record_type,
            'city_id': city_id,
            'city': city_name,
            'address': record.get('address', ''),
            'phone': record.get('phone', ''),
            'single_phone': record.get('single_phone_number', ''),
            'whatsapp': record.get('whatsapp', ''),
            'working_hours': hours,
            'latitude': record.get('lat', ''),
            'longitude': record.get('lng', ''),
            'description': record.get('description', ''),
        })

    return processed


def save_to_csv(records, filename):
    """Save records to a CSV file."""
    if not records:
        print(f"No records to save for {filename}")
        return

    filepath = os.path.join(DATA_DIR, filename)

    fieldnames = [
        'name', 'type', 'city_id', 'city', 'address', 'phone',
        'single_phone', 'whatsapp', 'working_hours', 'latitude',
        'longitude', 'description'
    ]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Saved {len(records)} records to {filepath}")


def main():
    print("Meqa Sigorta Data Fetcher")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output directory: {DATA_DIR}")
    print("-" * 50)

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    all_records = []

    for page_name, record_type in PAGES.items():
        print(f"Fetching {page_name}...")
        html_content = fetch_page(page_name)

        if html_content:
            # Extract medPoints from JavaScript
            records = extract_med_points(html_content)
            print(f"  Found {len(records)} records")

            # Extract working hours from HTML
            working_hours = extract_working_hours(html_content)

            # Process and enrich records
            processed = process_records(records, record_type, working_hours)
            all_records.extend(processed)
        else:
            print(f"  Failed to fetch page")

    print("-" * 50)

    # Remove duplicates based on name + latitude + longitude
    seen = set()
    unique_records = []
    duplicates = 0
    for record in all_records:
        key = (record['name'], record['latitude'], record['longitude'])
        if key not in seen:
            seen.add(key)
            unique_records.append(record)
        else:
            duplicates += 1

    if duplicates > 0:
        print(f"Removed {duplicates} duplicate records")

    # Save combined CSV with unique records
    save_to_csv(unique_records, "meqa_sigorta.csv")

    print("-" * 50)
    print(f"Total records fetched: {len(all_records)}")
    print(f"Unique records saved: {len(unique_records)}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
