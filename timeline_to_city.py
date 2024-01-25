import json
import yaml
import argparse
import time
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from tqdm import tqdm

# Parse command line arguments
parser = argparse.ArgumentParser(description='Process Google Timeline JSON history data.')
parser.add_argument('json_file', type=str, help='Path to the JSON file.')
parser.add_argument('--email', type=str, help='An email address to use for querying Nominatim.')
args = parser.parse_args()

def load_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    validate_config(config)
    return config

def validate_config(config):
    if 'date_ranges' not in config:
        raise ValueError("Config file must include 'date_ranges'.")

    for range in config['date_ranges']:
        if 'start' not in range or 'end' not in range or 'closest_time' not in range:
            raise ValueError("Each date range must include 'start', 'end', and 'closest_time'.")

def parse_timestamp(timestamp_str):
    try:
        # First, try parsing with fractional seconds
        return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        # If that fails, try parsing without fractional seconds
        return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ')

def extract_data(data, date_range):
    extracted_data = []
    start_date = datetime.strptime(date_range['start'], '%Y-%m-%d').date()
    end_date = datetime.strptime(date_range['end'], '%Y-%m-%d').date()
    closest_time = datetime.strptime(date_range['closest_time'], '%H:%M:%S').time()

    for record in tqdm(data['locations'], desc="Extracting Data"):
        timestamp = parse_timestamp(record['timestamp'])
        if start_date <= timestamp.date() <= end_date:
            time_difference = abs(datetime.combine(timestamp.date(), closest_time) - timestamp)
            record['time_difference'] = time_difference
            extracted_data.append(record)

    # Sort by time difference and take the closest for each day
    extracted_data.sort(key=lambda x: (x['timestamp'], x['time_difference']))
    unique_days = set()
    final_data = []
    for record in extracted_data:
        day = record['timestamp'][:10]  # Extract the date part
        if day not in unique_days:
            unique_days.add(day)
            final_data.append(record)

    print(f"Extracted {len(final_data)} entries from the data.")
    return final_data

def get_closest_city_name(latitude, longitude, geolocator, email):
    location = geolocator.reverse((latitude, longitude), exactly_one=True)
    if location:
        address = location.raw.get('address', {})
        
        # print(address)

        # Check for various fields in order of preference
        city = address.get('city') or address.get('town') or address.get('township') or address.get('village') or address.get('suburb')
        state = address.get('state', address.get('province', ''))
        country = address.get('country', '')
        
        return ', '.join(filter(None, [city, state, country]))
    else:
        return None

def query_nominatim(latitude, longitude, geolocator, email, attempt=1, max_attempts=5):
    # Sleep for 3 seconds between queries to avoid rate limiting.
    for _ in range(30):
        time.sleep(0.1)
    try:
        return get_closest_city_name(latitude, longitude, geolocator, email)
    except GeocoderTimedOut:
        if attempt <= max_attempts:
            print(f"Retrying {attempt}/{max_attempts} for coordinates: {latitude}, {longitude}")
            time.sleep(3)  # Wait for 3 seconds before retrying
            return query_nominatim(latitude, longitude, geolocator, email, attempt + 1)
        else:
            print(f"Failed to geocode coordinates: {latitude}, {longitude} after {max_attempts} attempts.")
            return None
    except KeyboardInterrupt:
        sys.exit("Script interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Main Script
if __name__ == "__main__":
    config = load_config('config.yaml')
    geolocator = Nominatim(user_agent=args.email)

    with open(args.json_file, 'r') as file:
        data = json.load(file)

    output_data = []
    for date_range in config['date_ranges']:
        extracted_data = extract_data(data, date_range)

        for record in tqdm(extracted_data, desc="Querying Nominatim"):
            latitude = record['latitudeE7'] / 1e7
            longitude = record['longitudeE7'] / 1e7
            city_name = query_nominatim(latitude, longitude, geolocator, args.email)
            output_data.append([record['timestamp'], latitude, longitude, city_name])

    # Write to TSV
    with open('output.tsv', 'w') as file:
        for line in output_data:
            file.write('\t'.join(map(str, line)) + '\n')
