import os
import requests
import pandas as pd
import io

# Define the list of indices and their corresponding URLs
indices = [ 
    {"name": "PNA", "url": "https://psl.noaa.gov/data/correlation/pna.data"},
    {"name": "EP/NP", "url": "https://psl.noaa.gov/data/correlation/epo.data"},
    {"name": "WP", "url": "https://psl.noaa.gov/data/correlation/wp.data"},
    {"name": "EA/WR", "url": "https://psl.noaa.gov/data/correlation/ea.data"},
    {"name": "NAO", "url": "https://psl.noaa.gov/data/correlation/nao.data"},
    {"name": "NAO (Jones)", "url": "https://psl.noaa.gov/data/correlation/jonesnao.data"},
    {"name": "SOI", "url": "https://psl.noaa.gov/data/correlation/soi.data"},
    {"name": "Niño 3", "url": "https://psl.noaa.gov/data/correlation/nina3.anom.data"},
    {"name": "BEST", "url": "https://psl.noaa.gov/data/correlation/censo.long.data"},
    {"name": "TNA", "url": "https://psl.noaa.gov/data/correlation/tna.data"},
    {"name": "TSA", "url": "https://psl.noaa.gov/data/correlation/tsa.data"},
    {"name": "WHWP", "url": "https://psl.noaa.gov/data/correlation/whwp.data"},
    {"name": "ONI", "url": "https://psl.noaa.gov/data/correlation/oni.data"},
    {"name": "MEI V2", "url": "https://psl.noaa.gov/data/correlation/mei.data"},
    {"name": "Niño 1+2", "url": "https://psl.noaa.gov/data/correlation/nina1.anom.data"},
    {"name": "Niño 4", "url": "https://psl.noaa.gov/data/correlation/nina4.anom.data"},
    {"name": "Niño 3.4", "url": "https://psl.noaa.gov/data/correlation/nina34.anom.data"},
    {"name": "PDO", "url": "https://psl.noaa.gov/data/correlation/pdo.data"},
    {"name": "TPI/IPO", "url": "https://psl.noaa.gov/data/timeseries/IPOTPI/ipotpi.hadisst2.data"},
    {"name": "NOI", "url": "https://psl.noaa.gov/data/correlation/noi.data"},
    {"name": "NP", "url": "https://psl.noaa.gov/data/correlation/np.data"},
    {"name": "Atlantic Tripole", "url": "https://psl.noaa.gov/data/correlation/atltri.data"},
    {"name": "AMO", "url": "https://psl.noaa.gov/data/correlation/amon.us.data"},
    {"name": "GIAM", "url": "https://psl.noaa.gov/data/correlation/glaam.data.scaled"},
    {"name": "ESPI", "url": "https://psl.noaa.gov/data/correlation/espi.data"},
    {"name": "CIP", "url": "https://psl.noaa.gov/data/correlation/indiamon.data"},
    {"name": "Sahel Rainfall", "url": "https://psl.noaa.gov/data/correlation/sahelrain.data"},
    {"name": "SW Monsoon", "url": "https://psl.noaa.gov/data/correlation/swmonsoon.data"},
    {"name": "NEB", "url": "https://psl.noaa.gov/data/correlation/brazilrain.data"},
    {"name": "Solar Flux", "url": "https://psl.noaa.gov/data/correlation/solar.data"},
    {"name": "GMT", "url": "https://psl.noaa.gov/data/correlation/gmsst.data"}
]

def download_data(url, index_name):
    response = requests.get(url)
    response.raise_for_status()  # Check if the request was successful
    return response.text

def is_data_line(line):
    """Check if a line starts with a year and contains the expected number of columns."""
    parts = line.strip().split()
    if len(parts) != 13:
        return False
    try:
        int(parts[0])  # Check if the first part is an integer (year)
        return True
    except ValueError:
        return False

def process_data(data, index_name):
    lines = data.splitlines()
    # Find the start of the data
    start_line = 0
    for i, line in enumerate(lines):
        if is_data_line(line):
            start_line = i
            break
    
    cleaned_lines = []
    for line in lines[start_line:]:
        parts = line.strip().split()
        if len(parts) == 13 and parts[0].isdigit():
            cleaned_lines.append(line)
        elif len(parts) > 13:
            cleaned_lines.append(' '.join(parts[:13]))  # Only take the first 13 parts
    
    df = pd.read_csv(io.StringIO('\n'.join(cleaned_lines)), sep='\s+', header=None)
    df.columns = ['Year'] + [f'Month_{i+1}' for i in range(12)]
    
    # Replace specific values with NaN
    na_values = [-99.99, -99.90, -99.9, -9.90, -999.0, 9999.00]
    df.replace(na_values, pd.NA, inplace=True)
    
    return df

def save_data(df, index_name, output_dir):
    output_file = os.path.join(output_dir, f"{index_name}.csv")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)  # Ensure directory exists
    df.to_csv(output_file, index=False)

def main(output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for index in indices:
        index_name = index["name"]
        url = index["url"]
        print(f"Downloading data for {index_name}...")
        try:
            data = download_data(url, index_name)
            df = process_data(data, index_name)
            save_data(df, index_name, output_dir)
        except requests.exceptions.HTTPError as http_err:
            print(f"Error processing data for {index_name}: {http_err}")
        except pd.errors.ParserError as parse_err:
            print(f"ParserError: Skipping {index_name} due to format issues. {parse_err}")
        except Exception as err:
            print(f"Error processing data for {index_name}: {err}")

    print(f"All indices have been downloaded and saved to {output_dir}")

if __name__ == "__main__":
    output_dir = "/home/jaguir26/project1_ucsc_phd/climate_indices"
    main(output_dir)
