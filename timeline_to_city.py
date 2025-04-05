import json
import yaml
import argparse
import time
import re
import sys
import os # Import os for checking file existence
from datetime import datetime, timedelta, time as dt_time
from dateutil import tz
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from tqdm import tqdm

# --- Constants ---
CACHE_FILENAME = 'geocoding_cache.json'
CACHE_PRECISION = 5 # Decimal places for lat/lon rounding in cache key

# --- Globals ---
geocoding_cache = {} # In-memory cache

# --- Argument Parsing, Config Loading, Validation (Keep as before) ---
parser = argparse.ArgumentParser(description='Process Google Timeline JSON history data (semanticSegments format).')
parser.add_argument('json_file', type=str, help='Path to the JSON file containing timeline data (e.g., Timeline.json).')
parser.add_argument('--config', type=str, default='config.yaml', help='Path to the configuration YAML file.')
parser.add_argument('--email', type=str, required=True, help='An email address to use as the user_agent for querying Nominatim (geolocation service policy requirement).')
args = parser.parse_args()

def load_config(file_path):
    # (Keep implementation as before)
    try:
        with open(file_path, 'r') as file:
            config = yaml.safe_load(file)
        validate_config(config)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{file_path}' not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file '{file_path}': {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error in configuration file '{file_path}': {e}")
        sys.exit(1)

def validate_config(config):
    # (Keep implementation as before)
    if 'date_range' not in config:
        raise ValueError("Config file must include 'date_range'.")
    if not isinstance(config['date_range'], list):
         raise ValueError("'date_range' must be a list of range objects.")
    for i, range_spec in enumerate(config['date_range']):
        if not isinstance(range_spec, dict):
             raise ValueError(f"Item {i} in 'date_range' is not a valid range object (must be a dictionary).")
        if 'start' not in range_spec or 'end' not in range_spec or 'closest_time' not in range_spec:
            raise ValueError(f"Date range {i} must include 'start', 'end', and 'closest_time'.")
        try:
            datetime.strptime(range_spec['start'], '%Y-%m-%d')
            datetime.strptime(range_spec['end'], '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Date range {i} has invalid date format in 'start' or 'end'. Use YYYY-MM-DD.")
        try:
            datetime.strptime(range_spec['closest_time'], '%H:%M:%S')
        except ValueError:
             raise ValueError(f"Date range {i} has invalid time format in 'closest_time'. Use HH:MM:SS.")

# --- Timestamp Parsing, Data Extraction (Keep as before) ---
def parse_timestamp(timestamp_str):
    # (Keep implementation as before)
    try:
        return datetime.fromisoformat(timestamp_str)
    except ValueError as e:
        # print(f"Warning: Could not parse timestamp '{timestamp_str}'. Error: {e}. Skipping record.")
        return None
    except TypeError:
        # print(f"Warning: Invalid type for timestamp: {timestamp_str}. Skipping record.")
        return None

def extract_data(data, date_range_config):
    # (Keep implementation as before)
    adjusted_data = []
    start_date = datetime.strptime(date_range_config['start'], '%Y-%m-%d').date()
    end_date = datetime.strptime(date_range_config['end'], '%Y-%m-%d').date()
    closest_time_target = datetime.strptime(date_range_config['closest_time'], '%H:%M:%S').time()
    print(f"\nProcessing range: {date_range_config['start']} to {date_range_config['end']}, closest to {date_range_config['closest_time']}")
    if 'semanticSegments' not in data:
        print("Warning: 'semanticSegments' key not found in JSON data. Cannot process.")
        return []
    for segment in tqdm(data['semanticSegments'], desc="Scanning Segments"):
        if 'visit' in segment and segment.get('visit'):
            visit_info = segment['visit']
            start_time_str = segment.get('startTime')
            if not start_time_str: continue
            timestamp_obj = parse_timestamp(start_time_str)
            if timestamp_obj is None: continue
            timestamp_utc = timestamp_obj.astimezone(tz.UTC)
            record_date = timestamp_utc.date()
            if start_date <= record_date <= end_date:
                lat, lon = None, None
                if visit_info.get('topCandidate') and visit_info['topCandidate'].get('placeLocation') and visit_info['topCandidate']['placeLocation'].get('latLng'):
                    latlng_str = visit_info['topCandidate']['placeLocation']['latLng']
                    try:
                        lat_str, lon_str = latlng_str.replace('°', '').split(',')
                        lat = float(lat_str.strip())
                        lon = float(lon_str.strip())
                    except (ValueError, TypeError): pass
                record_time = timestamp_obj.time()
                target_dt_on_record_date = datetime.combine(timestamp_obj.date(), closest_time_target)
                target_dt_on_record_date = target_dt_on_record_date.replace(tzinfo=timestamp_obj.tzinfo)
                time_difference = abs(timestamp_obj - target_dt_on_record_date)
                record = {'timestamp_obj': timestamp_obj, 'latitude': lat, 'longitude': lon, 'time_difference': time_difference, 'record_date_utc': record_date}
                adjusted_data.append(record)
    if not adjusted_data:
        print("No relevant visit segments found in this date range.")
        return []
    adjusted_data.sort(key=lambda x: (x['record_date_utc'], x['time_difference']))
    unique_days = {}
    for record in adjusted_data:
        day = record['record_date_utc']
        if day not in unique_days or record['time_difference'] < unique_days[day]['time_difference']:
            unique_days[day] = record
    final_data = list(unique_days.values())
    final_data.sort(key=lambda x: x['record_date_utc'])
    return final_data


# --- Geocoding Cache Functions ---
def load_cache():
    """Loads the geocoding cache from the JSON file."""
    global geocoding_cache
    if os.path.exists(CACHE_FILENAME):
        try:
            with open(CACHE_FILENAME, 'r', encoding='utf-8') as f:
                geocoding_cache = json.load(f)
            print(f"Loaded {len(geocoding_cache)} items from geocoding cache '{CACHE_FILENAME}'.")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load geocoding cache file '{CACHE_FILENAME}'. Starting with empty cache. Error: {e}")
            geocoding_cache = {}
    else:
        print("No existing geocoding cache file found. Starting with empty cache.")
        geocoding_cache = {}

def save_cache():
    """Saves the in-memory geocoding cache to the JSON file."""
    global geocoding_cache
    try:
        with open(CACHE_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(geocoding_cache, f, indent=2) # Use indent for readability
        # print(f"Saved {len(geocoding_cache)} items to geocoding cache '{CACHE_FILENAME}'.") # Optional: Can be verbose
    except IOError as e:
        print(f"Warning: Could not save geocoding cache to '{CACHE_FILENAME}'. Error: {e}")


# --- Modified Geocoding Logic with Cache ---
def get_location_with_cache(latitude, longitude, geolocator):
    """
    Gets location string: first checks cache, otherwise uses Nominatim lookup
    and updates the cache.
    """
    global geocoding_cache
    if latitude is None or longitude is None:
        return "Unknown Location (No Coords)"

    # Create cache key using rounded coordinates
    cache_key = f"{latitude:.{CACHE_PRECISION}f},{longitude:.{CACHE_PRECISION}f}"

    # 1. Check in-memory cache
    if cache_key in geocoding_cache:
        # print(f"Cache hit for {cache_key}") # Optional debug message
        return geocoding_cache[cache_key]

    # 2. Not in cache, perform Nominatim lookup (with retry)
    # print(f"Cache miss for {cache_key}, querying Nominatim...") # Optional debug message
    location_string = _nominatim_lookup_with_retry(latitude, longitude, geolocator)

    # 3. Store result in cache (memory and file)
    geocoding_cache[cache_key] = location_string
    save_cache() # Save cache after adding a new entry

    return location_string

# Renamed the original function to be "internal"
def _nominatim_lookup_with_retry(latitude, longitude, geolocator, attempt=1, max_attempts=3):
    """Internal function to perform the actual Nominatim lookup with retries."""
    time.sleep(1.1) # Comply with Nominatim usage policy (1 req/sec)
    try:
        # Call the core geopy reverse function
        location = geolocator.reverse((latitude, longitude), exactly_one=True, language='en', timeout=10)
        if location:
            address = location.raw.get('address', {})
            city = address.get('city') or address.get('town') or address.get('village')
            suburb = address.get('suburb')
            state = address.get('state', address.get('province', ''))
            country = address.get('country', '')
            location_parts = []
            if city: location_parts.append(city)
            elif suburb: location_parts.append(suburb)
            if state: location_parts.append(state)
            if country: location_parts.append(country)
            result = ', '.join(filter(None, location_parts))
            return result if result else "Location Name Unknown"
        else:
            return "Geocoding Failed (No Result)"
    except GeocoderTimedOut:
        print(f"Warning: Nominatim query timed out for {latitude}, {longitude}.")
        if attempt < max_attempts:
            print(f"Retrying ({attempt}/{max_attempts})...")
            time.sleep(2 ** attempt) # Exponential backoff
            return _nominatim_lookup_with_retry(latitude, longitude, geolocator, attempt + 1, max_attempts)
        else:
            print(f"Failed to geocode {latitude}, {longitude} after {max_attempts} attempts due to timeout.")
            return "Geocoding Failed (Timeout)"
    except KeyboardInterrupt:
        print("\nScript interrupted by user during geocoding.")
        sys.exit(0)
    except Exception as e:
        print(f"Warning: An error occurred during geocoding for {latitude}, {longitude}: {e}")
        # Optionally retry for other errors too
        return f"Geocoding Error"


# --- Country Extraction (Keep as before) ---
def get_country_from_location_string(location_string):
    # (Keep implementation as before)
    if not location_string or "Unknown Location" in location_string or "Geocoding Failed" in location_string or "Geocoding Error" in location_string:
        return None
    parts = [part.strip() for part in location_string.split(',')]
    if not parts: return None
    country = parts[-1]
    if country in ["United States", "USA", "US"]: return "USA"
    return country


# --- Updated Function for Detailed Travel Summary ---
def print_travel_summary(geocoded_records):
    """
    Analyzes daily geocoded records and prints a detailed summary
    of periods spent outside Canada, including daily locations.
    """
    print("\n--- Travel Summary (Periods Outside Canada - Detailed) ---")
    if not geocoded_records:
        print("No data to analyze.")
        return

    geocoded_records.sort(key=lambda x: x['date'])

    in_canada = True
    trip_start_date = None
    last_outside_day = None
    current_trip_details = [] # Stores {'date': date, 'location': loc} for the current trip
    trips_found = 0

    for record in geocoded_records:
        current_date = record['date']
        location_string = record['location_string']
        country = get_country_from_location_string(location_string)

        is_currently_outside = (country is not None and country != "Canada")

        if is_currently_outside:
            if in_canada:
                # Starting a new trip
                in_canada = False
                trip_start_date = current_date
                current_trip_details = [] # Reset details for the new trip

            # Update last day and add current day's details to the list
            last_outside_day = current_date
            current_trip_details.append({'date': current_date, 'location': location_string})

        else: # Inside Canada or Unknown
            if not in_canada:
                # Trip just ended, print its details
                print(f"\nTrip Found: {trip_start_date} to {last_outside_day}")
                trips_found += 1
                if not current_trip_details:
                     print("  (No daily location details available for this trip)")
                else:
                    for day_detail in current_trip_details:
                         print(f"  - {day_detail['date']}: {day_detail['location']}")

                # Reset state for being back in Canada
                in_canada = True
                trip_start_date = None
                last_outside_day = None
                current_trip_details = []

    # After loop, check if a trip was ongoing
    if not in_canada and trip_start_date and last_outside_day:
        print(f"\nTrip Found: {trip_start_date} to {last_outside_day} (End of data)")
        trips_found += 1
        if not current_trip_details:
             print("  (No daily location details available for this trip)")
        else:
            for day_detail in current_trip_details:
                 print(f"  - {day_detail['date']}: {day_detail['location']}")

    if trips_found == 0:
        print("No periods identified outside Canada based on the provided data and date ranges.")
    print("\n--------------------------------------------------------")


# --- Main Script Execution ---
if __name__ == "__main__":
    # --- Setup ---
    config = load_config(args.config)
    geolocator = Nominatim(user_agent=args.email)
    print(f"Using Nominatim with user_agent: {args.email}")
    load_cache() # Load cache at start

    # --- Load JSON Data ---
    try:
        with open(args.json_file, 'r', encoding='utf-8') as file:
            print(f"Loading JSON data from {args.json_file}...")
            data = json.load(file)
            print("JSON data loaded successfully.")
    except FileNotFoundError:
        print(f"Error: Input JSON file '{args.json_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from '{args.json_file}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred reading '{args.json_file}': {e}")
        sys.exit(1)

    output_filename = 'output.tsv'
    # Prepare TSV Header
    try:
        with open(output_filename, 'w', encoding='utf-8') as tsv_file:
             tsv_file.write("Timestamp (Local)\tLatitude\tLongitude\tClosest City\n")
        print(f"\nOutput TSV will be saved to '{output_filename}'.")
    except IOError as e:
        print(f"Error: Could not open output file '{output_filename}' for writing header: {e}")
        sys.exit(1) # Exit if we can't even write the header

    # --- Step 1: Extract and Geocode data (using cache) ---
    all_geocoded_records = []
    print("\n--- Processing Date Ranges and Geocoding (using cache) ---")
    for date_range in config['date_range']:
        extracted_data = extract_data(data, date_range)
        if not extracted_data: continue

        print(f"Geocoding/Retrieving {len(extracted_data)} daily locations for range {date_range['start']}-{date_range['end']}...")
        range_geocoded_records = []
        # Use TQDM for progress bar during geocoding/cache retrieval
        for record in tqdm(extracted_data, desc="Geocoding/Cache Lookup"):
            latitude = record.get('latitude', None)
            longitude = record.get('longitude', None)

            # Use the new function that handles cache internally
            city_name = get_location_with_cache(latitude, longitude, geolocator)

            range_geocoded_records.append({
                 'date': record['timestamp_obj'].date(),
                 'location_string': city_name,
                 'latitude': latitude,
                 'longitude': longitude,
                 'timestamp_obj': record['timestamp_obj']
             })
        all_geocoded_records.extend(range_geocoded_records)
    print("------------------------------------------------------")


    # --- Step 2: Write combined results to TSV ---
    print(f"\n--- Writing Data to TSV ---")
    if all_geocoded_records:
        all_geocoded_records.sort(key=lambda x: x['timestamp_obj'])
        print(f"Writing {len(all_geocoded_records)} records to '{output_filename}'...")
        total_records_written = 0
        try:
             with open(output_filename, 'a', encoding='utf-8') as tsv_file:
                 for record in tqdm(all_geocoded_records, desc="Writing to TSV"):
                     timestamp_local_str = record['timestamp_obj'].isoformat(sep=' ', timespec='seconds')
                     lat_str = f"{record['latitude']:.7f}" if record['latitude'] is not None else "N/A"
                     lon_str = f"{record['longitude']:.7f}" if record['longitude'] is not None else "N/A"
                     location_str = record['location_string']
                     tsv_line = '\t'.join([timestamp_local_str, lat_str, lon_str, location_str])
                     tsv_file.write(tsv_line + '\n')
                     total_records_written += 1
             print(f"TSV writing complete. {total_records_written} records appended.")
        except IOError as e:
             print(f"Error appending to output file '{output_filename}': {e}")
    else:
        print("No records to write to TSV.")
    print("-------------------------")


    # --- Step 3: Print Detailed Travel Summary ---
    print_travel_summary(all_geocoded_records)

    # --- Final message ---
    # Optional: Explicitly save cache at the very end, although it's saved after each miss now.
    # save_cache()
    print("\nProcessing finished.")