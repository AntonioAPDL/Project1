import os
import pandas as pd
import matplotlib.pyplot as plt
import requests

# Define the directory containing the CSV files
input_dir = "/home/jaguir26/project1_ucsc_phd/climate_indices"

# List of indices that have data up until Dec 2022 or later
indices = [
    "Niño 3", "NAO", "Niño 1+2", "WHWP", "GMT",
    "ONI", "PNA", "NOI", "WP", "Niño 3.4", "Solar Flux",
    "AMO", "TSA", "PDO", "Niño 4", "TNA", "SOI"
]

# Function to download and process the updated PDO data
def download_pdo_data():
    url = "https://oceanview.pfeg.noaa.gov/erddap/tabledap/cciea_OC_PDO.htmlTable?time%2CPDO%2Cindex&time%3C=2024-05-25T00%3A00%3A00Z&time%3C=2024-06-01T00%3A00%3A00Z"
    pdo_df = pd.read_csv(url)
    pdo_df['Date'] = pd.to_datetime(pdo_df['time'])
    pdo_df.set_index('Date', inplace=True)
    pdo_df = pdo_df[['PDO']]
    pdo_df.rename(columns={'PDO': 'Value'}, inplace=True)
    pdo_df.to_csv(os.path.join(input_dir, "PDO.csv"))

# Function to download and process the updated NAO (Jones) data
def download_nao_jones_data():
    url = "https://crudata.uea.ac.uk/cru/data/nao/nao.dat"
    response = requests.get(url)
    data = response.text
    # Process the data into a DataFrame
    lines = data.splitlines()
    parsed_data = []
    for line in lines:
        parts = line.split()
        year = int(parts[0])
        monthly_values = [float(x) for x in parts[1:13]]
        parsed_data.append([year] + monthly_values)
    nao_jones_df = pd.DataFrame(parsed_data, columns=['Year'] + [f'Month_{i+1}' for i in range(12)])
    nao_jones_df.to_csv(os.path.join(input_dir, "NAO (Jones).csv"), index=False)

# Download the PDO and NAO (Jones) data
download_pdo_data()
download_nao_jones_data()

# Function to load and plot each index
def plot_index(file_path, index_name):
    df = pd.read_csv(file_path)
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')  # Convert Year column to numeric
    df = df.dropna(subset=['Year'])  # Drop rows where Year could not be converted to numeric
    
    # Filter the data to include only records from 1980 onwards
    df = df[df['Year'] >= 1980]
    
    # Melt the DataFrame to have a single time series
    df_melted = df.melt(id_vars='Year', var_name='Month', value_name='Value')
    month_mapping = {
        'Month_1': 1, 'Month_2': 2, 'Month_3': 3, 'Month_4': 4, 
        'Month_5': 5, 'Month_6': 6, 'Month_7': 7, 'Month_8': 8, 
        'Month_9': 9, 'Month_10': 10, 'Month_11': 11, 'Month_12': 12
    }
    df_melted['Month'] = df_melted['Month'].map(month_mapping)
    df_melted['Date'] = pd.to_datetime(df_melted[['Year', 'Month']].assign(DAY=1))
    df_melted.sort_values('Date', inplace=True)
    
    # Ensure 'Value' column is numeric and handle missing values
    df_melted['Value'] = pd.to_numeric(df_melted['Value'], errors='coerce')
    df_melted.replace([-99.99, -99.90, -99.9, -9.90, -999.0, 9999.00], pd.NA, inplace=True)
    df_melted.dropna(subset=['Value'], inplace=True)

    # Check for December 2022 value
    dec_2022_value = df_melted[(df_melted['Year'] == 2022) & (df_melted['Month'] == 12)]
    if dec_2022_value.empty or pd.isna(dec_2022_value['Value'].values[0]):
        print(f"December 2022 value for {index_name} is missing. Skipping plot.")
        return

    # Plotting
    plt.figure(figsize=(14, 6))
    plt.plot(df_melted['Date'], df_melted['Value'], label=index_name)
    
    plt.title(f"{index_name} Index Over Time (From 1980 to Dec 2022)")
    plt.xlabel("Date")
    plt.ylabel("Index Value")
    plt.legend(loc='upper right', bbox_to_anchor=(1.15, 1))
    plt.grid(True)
    plt.show()

# Loop through the indices and plot each one
for index_name in indices:
    file_name = f"{index_name}.csv"
    file_path = os.path.join(input_dir, file_name)
    if os.path.exists(file_path):
        plot_index(file_path, index_name)
    else:
        print(f"File not found: {file_path}")

# Plot the NAO (Jones) index
plot_index(os.path.join(input_dir, "NAO (Jones).csv"), "NAO (Jones)")
