# google-timeline-to-city
This script processes Google Timeline JSON history data to extract location information and converts latitude and longitude coordinates into readable city, province/state, and country names. The results are saved in a TSV format.

## Features
- Parses Google Timeline JSON data.
- Filters data based on configurable date ranges.
- Finds data points closest to a specified time within these date ranges.
- Uses Nominatim to geocode coordinates into human-readable location names.
- Outputs the processed data in a TSV file.

## Requirements
- Python 3
- Libraries: json, yaml, argparse, datetime, geopy, tqdm
- A YAML configuration file specifying the date ranges, times, and UTC offsets for data extraction.
- A copy of your Google Timeline data obtained by Google's takeout service.

## Downloading Google Timeline Data from Google Takeout

To use this script, you first need to download your Google Timeline data in JSON format from Google's Takeout service. Follow these steps to download your data:

1. **Visit Google Takeout**: 
   - Go to [Google Takeout](https://takeout.google.com/).
   - Log in with your Google account.

2. **Select Your Data**:
   - Initially, all data types are pre-selected. Click on "Deselect all" at the top of the list.
   - Scroll down and find "Location History". Check the box next to it.
   - Ensure "Location History JSON format" is selected by clicking on "Multiple formats" next to "Location History".

3. **Customize Archive Format**:
   - Scroll down and click “Next step”.
   - Choose your archive frequency, file type, and maximum archive size.

4. **Create and Download the Archive**:
   - Click on “Create export”.
   - Google will prepare your download and send an email when it's ready.
   - Follow the link in the email to download the archive.

5. **Extract and Locate the Data**:
   - The downloaded file will be in ZIP format. Extract it using your file extraction tool.
   - Inside the extracted folder, navigate to the "Takeout/Location History (Timeline)" directory.
   - The file you need is typically named "Records.json". This is your Google Timeline data in JSON format.

6. **Use the Data with the Script**:
   - You can now use this "Records.json" file with the `timeline_to_city.py` script to process and analyze your location history.

## Installation
Before running the script, ensure you have the required libraries installed. You can install them using pip:

```
pip install pyyaml geopy tqdm
```

## Usage
To run the script, use the following command:

```
python timeline_to_city.py --email your-email@example.com path/to/your/Records.json
```

your-email@example.com should be replaced with your actual email address. This is used for querying Nominatim.
`path/to/your/Records.json` should be the path to your Google Timeline JSON file.

## YAML Configuration File
The script requires a YAML file named config.yaml with the following structure:

```
date_ranges:
  - start: "YYYY-MM-DD"
    end: "YYYY-MM-DD"
    closest_time: "HH:MM:SS"
    UTC_offset: "±HH:MM"
```  
- start and end define the date range for extracting data.
- closest_time specifies the time of day for which you want to find the closest data point.
- UTC_offset specifies the UTC offset to adjust the times to your local timezone (e.g., -04:00 for Atlantic Time).

# Output
The script generates a TSV file named `output.tsv`, containing the adjusted timestamp, latitude, longitude, and location name (city, province/state, country) for each data point within the specified date ranges.

## Adjusted Timestamps
The script adjusts timestamps to a specified timezone. In the `output.tsv` file, the timestamps reflect these adjustments, based on the UTC offset provided in the `config.yaml` file.

- This adjustment aligns the timestamps with the user's local time zone for better context.
- The format of the adjusted timestamps in the TSV file remains consistent with the original Google Timeline format (`YYYY-MM-DDTHH:MM:SS.sssZ`).

## Example Output Format
The TSV file includes tab-separated columns in the following order:

1. **Timestamp (Adjusted)**: The date and time of the location data point, modified to the specified local time zone.
2. **Latitude**: The latitude coordinate of the location.
3. **Longitude**: The longitude coordinate of the location.
4. **Location Name**: A readable name of the location, typically in "City, Province/State, Country" format.

### Location Name Logic
The script uses Nominatim's reverse geocoding to convert latitude and longitude coordinates into human-readable location names. The logic for determining the location name is as follows:

- **City**: The script first tries to identify the 'city' from the geocoded data. If 'city' is not available, it looks for 'town', 'hamlet', 'township', 'village', or 'suburb', in that order of preference. 
- **State/Province**: The script first searches for the 'state' field in the geocoded data. If 'state' is not available, it looks for 'province'.
- **Country**: The script also includes the 'country' field as the final field.

# License
MIT License -- Please see the LICENSE file.
