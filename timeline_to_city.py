import json
import yaml
import argparse
import time
import re
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from tqdm import tqdm

# Set up argument parser for command line usage
parser = argparse.ArgumentParser(description='Process Google Timeline JSON history data.')
parser.add_argument('json_file', type=str, help='Path to the JSON file containing location data.')
parser.add_argument('--email', type=str, help='An email address to use for querying Nominatim (geolocation service).')
args = parser.parse_args()

# Load configuration from a YAML file
def load_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    validate_config(config)
    return config

# Validate the structure and contents of the configuration
def validate_config(config):
    if 'date_range' not in config:
        raise ValueError("Config file must include 'date_range'.")

    # Pattern for validating UTC offset format
    utc_offset_pattern = re.compile(r'^[+-]\d{2}:\d{2}$')
    for range in config['date_range']:
        # Validate each date range in the config
        if 'start' not in range or 'end' not in range or 'closest_time' not in range:
            raise ValueError("Each date range must include 'start', 'end', and 'closest_time'.")

        if 'UTC_offset' not in range or not utc_offset_pattern.match(range['UTC_offset']):
            raise ValueError("Each date range must include a valid 'UTC_offset' in the format ±HH:MM.")

# Parse timestamps from the JSON file
def parse_timestamp(timestamp_str):
    try:
        return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ')

# Extract data within the specified date range and adjust timestamps
def extract_data(data, date_range):
    adjusted_data = []
    start_date = datetime.strptime(date_range['start'], '%Y-%m-%d').date()
    end_date = datetime.strptime(date_range['end'], '%Y-%m-%d').date()
    closest_time = datetime.strptime(date_range['closest_time'], '%H:%M:%S').time()

    # Process UTC offset for time adjustment
    utc_offset = date_range.get('UTC_offset', '+00:00')
    offset_hours, offset_minutes = map(int, re.match(r'([+-]\d{2}):(\d{2})', utc_offset).groups())
    offset = timedelta(hours=offset_hours, minutes=offset_minutes)

    # Adjust timestamps for each location record
    for record in tqdm(data['locations'], desc="Adjusting Data"):
        timestamp = parse_timestamp(record['timestamp'])
        timestamp_adjusted = timestamp + offset

        if start_date <= timestamp_adjusted.date() <= end_date:
            record['timestamp_adjusted'] = timestamp_adjusted
            time_difference = abs(datetime.combine(timestamp_adjusted.date(), closest_time) - timestamp_adjusted)
            record['time_difference'] = time_difference
            adjusted_data.append(record)

    # Sort data and select the closest record for each day
    adjusted_data.sort(key=lambda x: (x['timestamp_adjusted'].date(), x['time_difference']))
    unique_days = {}
    for record in adjusted_data:
        day = record['timestamp_adjusted'].date()
        if day not in unique_days or unique_days[day]['time_difference'] > record['time_difference']:
            unique_days[day] = record

    final_data = list(unique_days.values())
    final_data.sort(key=lambda x: x['timestamp_adjusted'].date())

    return final_data

# Get closest city name from latitude and longitude using Nominatim
def get_closest_city_name(latitude, longitude, geolocator, email):
    location = geolocator.reverse((latitude, longitude), exactly_one=True)
    if location:
        address = location.raw.get('address', {})
        city = address.get('city') or address.get('town') or address.get('township') or address.get('village') or address.get('suburb')
        state = address.get('state', address.get('province', ''))
        country = address.get('country', '')
        return ', '.join(filter(None, [city, state, country]))
    else:
        return None

# Query Nominatim with retries in case of timeout
def query_nominatim(latitude, longitude, geolocator, email, attempt=1, max_attempts=5):
    # Sleep briefly between queries to comply with Nominatim's usage policy
    for _ in range(30):
        time.sleep(0.1)
    try:
        return get_closest_city_name(latitude, longitude, geolocator, email)
    except GeocoderTimedOut:
        if attempt <= max_attempts:
            print(f"Retrying {attempt}/{max_attempts} for coordinates: {latitude}, {longitude}")
            time.sleep(3)
            return query_nominatim(latitude, longitude, geolocator, email, attempt + 1)
        else:
            print(f"Failed to geocode coordinates: {latitude}, {longitude} after {max_attempts} attempts.")
            return None
    except KeyboardInterrupt:
        sys.exit("Script interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Main script execution
if __name__ == "__main__":
    # Load configuration and set up geolocator
    config = load_config('config.yaml')
    geolocator = Nominatim(user_agent=args.email)

    # Read the JSON file containing location data
    with open(args.json_file, 'r') as file:
        data = json.load(file)

    # Prepare the TSV file for writing processed data
    with open('output.tsv', 'w') as tsv_file:
        pass  # Clear existing contents

    # Process data and append to TSV file
    with open('output.tsv', 'a') as tsv_file:
        for date_range in config['date_range']:
            extracted_data = extract_data(data, date_range)

            for record in tqdm(extracted_data, desc="Writing to TSV"):
                # Convert latitude and longitude to decimal format
                latitude = record['latitudeE7'] / 1e7
                longitude = record['longitudeE7'] / 1e7
                # Query Nominatim for city name
                city_name = query_nominatim(latitude, longitude, geolocator, args.email)
                
                # Write each record to the TSV file using the adjusted timestamp
                adjusted_timestamp_str = record['timestamp_adjusted'].strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                tsv_line = '\t'.join(map(str, [adjusted_timestamp_str, latitude, longitude, city_name]))
                tsv_file.write(tsv_line + '\n')

    print("Data processing complete. Output saved to 'output.tsv'.")