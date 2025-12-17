import requests
import csv
import re
import os
import urllib3
from datetime import datetime
from html import unescape

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://aiic.az/az/hekim"
PAGES = {
    "klinikalar": "CLINIC",
    "aptek": "PHARMACY"
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
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_coords_from_maps_url(url):
    """Extract latitude and longitude from Google Maps embed URL."""
    if not url:
        return None, None

    # Pattern to find !2d{lng}!3d{lat} in Google Maps URLs
    # Sometimes it's !3d{lat}!2d{lng}, need to handle both

    lat_match = re.search(r'!3d([\d.]+)', url)
    lng_match = re.search(r'!2d([\d.]+)', url)

    lat = lat_match.group(1) if lat_match else None
    lng = lng_match.group(1) if lng_match else None

    return lat, lng


def extract_items(html_content):
    """Extract items from HTML."""
    if not html_content:
        return []

    records = []

    # Pattern to match accordion items
    # Each item has:
    # - <a href="google maps url"...> with <span class="aptek-name">Name</span>
    # - <div class="accordion-body"> with address and phone in <p> tags

    item_pattern = r'<div class="accordion-item">\s*<a href="([^"]*)"[^>]*>.*?<span class="aptek-name">([^<]*)</span>.*?</a>\s*<div[^>]*>\s*<div class="accordion-body">(.*?)</div>\s*</div>\s*</div>'

    for match in re.finditer(item_pattern, html_content, re.DOTALL):
        maps_url = match.group(1)
        name = clean_text(match.group(2))
        body_html = match.group(3)

        # Extract coordinates from Google Maps URL
        lat, lng = extract_coords_from_maps_url(maps_url)

        # Parse body for address and phone
        # First <p> is usually address, then "Telefon" label, then phone number
        p_tags = re.findall(r'<p>([^<]*)</p>', body_html)

        address = ""
        phone = ""

        for i, p in enumerate(p_tags):
            p_clean = clean_text(p)
            if p_clean.lower() == 'telefon':
                # Next p tag is the phone number
                if i + 1 < len(p_tags):
                    phone = clean_text(p_tags[i + 1])
            elif not address and p_clean and p_clean.lower() != 'telefon':
                # First non-telefon p tag is address
                address = p_clean

        records.append({
            'name': name,
            'address': address,
            'phone': phone,
            'latitude': lat if lat else '',
            'longitude': lng if lng else '',
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
        'name', 'type', 'address', 'phone', 'latitude', 'longitude'
    ]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Saved {len(records)} records to {filepath}")


def main():
    print("AIIC Insurance Data Fetcher")
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
            records = extract_items(html_content)
            print(f"  Found {len(records)} records")

            processed = process_records(records, record_type)
            all_records.extend(processed)
        else:
            print(f"  Failed to fetch page")

    print("-" * 50)

    # Remove duplicates based on name + address
    seen = set()
    unique_records = []
    duplicates = 0
    for record in all_records:
        key = (record['name'], record['address'])
        if key not in seen:
            seen.add(key)
            unique_records.append(record)
        else:
            duplicates += 1

    if duplicates > 0:
        print(f"Removed {duplicates} duplicate records")

    # Save combined CSV with unique records
    save_to_csv(unique_records, "aiic.csv")

    print("-" * 50)
    print(f"Total records fetched: {len(all_records)}")
    print(f"Unique records saved: {len(unique_records)}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
