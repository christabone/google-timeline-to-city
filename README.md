# google-timeline-to-city
This script processes Google Timeline JSON history data to extract location information and converts latitude and longitude coordinates into readable city, province/state, and country names. The results are saved in a TSV format.

## Features
- Parses Google Timeline JSON data.
- Filters data based on configurable date ranges.
- Finds data points closest to specified times within these date ranges.
- Uses Nominatim to geocode coordinates into human-readable location names.
- Outputs the processed data in a TSV file.

## Requirements
- Python 3
- Libraries: json, yaml, argparse, datetime, geopy, tqdm
- A YAML configuration file specifying the date ranges and times for data extraction.

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
```  

start and end define the date range for extracting data.
closest_time specifies the time of day for which you want to find the closest data point.

# Output
The script outputs a TSV file named output.tsv containing the timestamp, latitude, longitude, and location name (city, province/state, country) for each data point in the specified date ranges.

# License
MIT License -- Please see the LICENSE file.
