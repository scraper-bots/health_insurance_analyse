import requests
import csv
import re
import os
import urllib3
from datetime import datetime
from html import unescape

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://ateshgah.com/incidents"
PAGES = {
    "klinikalar": "CLINIC",
    "tibbi-xidmet": "MEDICAL_SERVICE"
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


def clean_text(text):
    """Clean and normalize text."""
    if not text:
        return ""
    # Unescape HTML entities
    text = unescape(text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_items(html_content):
    """Extract items from HTML."""
    if not html_content:
        return []

    records = []

    # Pattern to match service items with flexible whitespace
    # <a href="javascript:void(0);" class="services__item" data-lng="..." data-lat="...">
    #     <h4>Name</h4>
    #     <span>address, phone, email</span>
    # </a>

    pattern = r'<a\s+href="javascript:void\(0\);"\s+class="services__item"\s+data-lng="([^"]*)"\s+data-lat="([^"]*)"[^>]*>\s*<h4>([^<]*)</h4>\s*<span>(.*?)</span>\s*</a>'

    for match in re.finditer(pattern, html_content, re.DOTALL):
        lng = match.group(1).strip()
        lat = match.group(2).strip()
        name = clean_text(match.group(3))
        details = match.group(4)

        # Clean details - remove any HTML tags
        details = re.sub(r'<[^>]+>', '', details)
        details = clean_text(details)

        # Parse details (address, phone, email separated by commas)
        parts = [p.strip() for p in details.split(',') if p.strip()]

        address = ""
        phone = ""
        email = ""

        for part in parts:
            part = part.strip()
            if '@' in part:
                email = part
            elif re.search(r'[\d\-\+\(\)\s]{7,}', part):
                # Looks like a phone number
                if phone:
                    phone += "; " + part
                else:
                    phone = part
            else:
                # Assume it's part of the address
                if address:
                    address += ", " + part
                else:
                    address = part

        records.append({
            'name': name,
            'address': address,
            'phone': phone,
            'email': email,
            'latitude': lat,
            'longitude': lng,
        })

    return records


def process_records(records, record_type):
    """Add type to records."""
    for record in records:
        record['type'] = record_type
    return records


def save_to_csv(records, filename):
    """Save records to a CSV file."""
    if not records:
        print(f"No records to save for {filename}")
        return

    filepath = os.path.join(DATA_DIR, filename)

    fieldnames = [
        'name', 'type', 'address', 'phone', 'email',
        'latitude', 'longitude'
    ]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Saved {len(records)} records to {filepath}")


def main():
    print("Ateshgah Insurance Data Fetcher")
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
            # Extract items from HTML
            records = extract_items(html_content)
            print(f"  Found {len(records)} records")

            # Add type to records
            processed = process_records(records, record_type)
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
    save_to_csv(unique_records, "ateshgah.csv")

    print("-" * 50)
    print(f"Total records fetched: {len(all_records)}")
    print(f"Unique records saved: {len(unique_records)}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
