import requests
import csv
import re
import os
import json
import urllib3
from datetime import datetime
from html import unescape

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://a-group.az/list"

# API endpoints configuration
# pharmacy, optiks, stomatology use JSON API
# clinics uses XML API with separate detail endpoint
API_ENDPOINTS = {
    "pharmacy": {
        "url": f"{BASE_URL}/pharmacy/api.php",
        "type": "PHARMACY",
        "detail_key": "PHARMACY",
        "format": "json"
    },
    "optiks": {
        "url": f"{BASE_URL}/optiks/api.php",
        "type": "OPTICS",
        "detail_key": "OPTIC",
        "format": "json"
    },
    "stomatology": {
        "url": f"{BASE_URL}/stomatology/api.php",
        "type": "DENTAL",
        "detail_key": "DENTAL_CLINIC",
        "format": "json"
    },
    "clinics": {
        "url": f"{BASE_URL}/clinics/hospitals",
        "detail_url": f"{BASE_URL}/clinics/hospital",
        "type": "CLINIC",
        "format": "xml"
    }
}

# Output directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, application/xml;q=0.9,*/*;q=0.8",
}


def normalize_coordinates(location_x, location_y):
    """
    Normalize coordinates - swap if X starts with digits > 42.
    In Azerbaijan, latitude should be ~38-42, longitude ~44-51.
    """
    try:
        x = float(location_x) if location_x else None
        y = float(location_y) if location_y else None

        if x is None or y is None:
            return "", ""

        # Check if X value looks more like longitude (> 42 means it's probably longitude)
        x_head = int(str(abs(x))[:2])
        if x_head > 42:
            # Swap coordinates
            x, y = y, x

        return str(x), str(y)
    except (ValueError, TypeError):
        return "", ""


def clean_text(text):
    """Clean and normalize text."""
    if not text:
        return ""
    # Unescape HTML entities
    text = unescape(str(text))
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch_json_api(endpoint_config):
    """Fetch data from JSON API endpoint."""
    url = endpoint_config["url"]
    record_type = endpoint_config["type"]
    detail_key = endpoint_config["detail_key"]

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
            verify=False
        )
        response.raise_for_status()
        data = response.json()

        records = []
        for item in data:
            name = clean_text(item.get("NAME", ""))
            customer_id = item.get("CUSTOMER_ID", "")
            location_x = item.get("LOCATION_X", "")
            location_y = item.get("LOCATION_Y", "")

            # Get details
            details = item.get("details", {}).get(detail_key, {})
            address = clean_text(details.get("WORK_ADR_FULL", ""))
            phone = clean_text(details.get("WORK_PHONE", ""))

            # Normalize coordinates
            latitude, longitude = normalize_coordinates(location_x, location_y)

            records.append({
                "name": name,
                "type": record_type,
                "customer_id": customer_id,
                "address": address,
                "phone": phone,
                "latitude": latitude,
                "longitude": longitude
            })

        return records

    except requests.RequestException as e:
        print(f"  Error fetching {url}: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"  Error parsing JSON from {url}: {e}")
        return []


def parse_xml_value(xml_content, tag):
    """Extract value from XML tag."""
    pattern = rf'<{tag}[^>]*>(.*?)</{tag}>'
    match = re.search(pattern, xml_content, re.DOTALL | re.IGNORECASE)
    if match:
        value = match.group(1).strip()
        # Remove any nested HTML/XML tags
        value = re.sub(r'<[^>]+>', '', value)
        return clean_text(value)
    return ""


def fetch_xml_hospitals(endpoint_config):
    """Fetch clinic data from XML endpoint with separate detail calls."""
    list_url = endpoint_config["url"]
    detail_url = endpoint_config["detail_url"]
    record_type = endpoint_config["type"]

    try:
        # Fetch list of hospitals
        response = requests.get(
            list_url,
            headers=HEADERS,
            timeout=30,
            verify=False
        )
        response.raise_for_status()
        xml_content = response.text

        # Decode HTML entities in XML
        xml_content = unescape(xml_content)

        # Parse hospital blocks
        hospital_pattern = r'<HOSPITALS>(.*?)</HOSPITALS>'
        hospital_blocks = re.findall(hospital_pattern, xml_content, re.DOTALL | re.IGNORECASE)

        records = []
        total = len(hospital_blocks)

        for idx, block in enumerate(hospital_blocks, 1):
            customer_id = parse_xml_value(block, "CUSTOMER_ID")
            name = parse_xml_value(block, "NAME")
            if not name:
                name = parse_xml_value(block, "NAME_AZ")
            if not name:
                name = parse_xml_value(block, "NAME_EN")

            location_x = parse_xml_value(block, "LOCATION_X")
            location_y = parse_xml_value(block, "LOCATION_Y")

            # Normalize coordinates
            latitude, longitude = normalize_coordinates(location_x, location_y)

            # Fetch details for this hospital
            address = ""
            phone = ""

            if customer_id:
                try:
                    detail_response = requests.get(
                        f"{detail_url}/{customer_id}",
                        headers=HEADERS,
                        timeout=30,
                        verify=False
                    )
                    if detail_response.ok:
                        detail_xml = unescape(detail_response.text)
                        address = parse_xml_value(detail_xml, "WORK_ADR_FULL")
                        phone = parse_xml_value(detail_xml, "WORK_PHONE")
                except requests.RequestException:
                    pass  # Continue without details if request fails

            if idx % 20 == 0 or idx == total:
                print(f"    Processed {idx}/{total} clinics...")

            records.append({
                "name": name,
                "type": record_type,
                "customer_id": customer_id,
                "address": address,
                "phone": phone,
                "latitude": latitude,
                "longitude": longitude
            })

        return records

    except requests.RequestException as e:
        print(f"  Error fetching {list_url}: {e}")
        return []


def save_to_csv(records, filename):
    """Save records to a CSV file."""
    if not records:
        print(f"No records to save for {filename}")
        return

    filepath = os.path.join(DATA_DIR, filename)

    fieldnames = [
        'name', 'type', 'customer_id', 'address', 'phone',
        'latitude', 'longitude'
    ]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Saved {len(records)} records to {filepath}")


def main():
    print("A-Group Insurance Data Fetcher")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output directory: {DATA_DIR}")
    print("-" * 50)

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    all_records = []

    for endpoint_name, config in API_ENDPOINTS.items():
        print(f"Fetching {endpoint_name}...")

        if config["format"] == "json":
            records = fetch_json_api(config)
        else:  # xml
            records = fetch_xml_hospitals(config)

        print(f"  Found {len(records)} records")
        all_records.extend(records)

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
    save_to_csv(unique_records, "a_group.csv")

    print("-" * 50)
    print(f"Total records fetched: {len(all_records)}")
    print(f"Unique records saved: {len(unique_records)}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
