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
- A YAML configuration file specifying the date ranges and times for data extraction.
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
```  

start and end define the date range for extracting data.
closest_time specifies the time of day for which you want to find the closest data point.

# Output
The script outputs a TSV file named output.tsv containing the timestamp, latitude, longitude, and location name (city, province/state, country) for each data point in the specified date ranges.

# License
MIT License -- Please see the LICENSE file.
