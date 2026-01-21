import os
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

# Function to create necessary directories
def create_directories(base_path):
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    print(f"Data will be stored in: {base_path}")

# Define paths
base_path = '/data/muscat_data/jaguir26/project1_ucsc_phd/soil_moisture_data/'
netcdf_file_path_template = os.path.join(base_path, 'soil_moisture_big_trees_{}.nc')
csv_file_path = os.path.join(base_path, 'soil_moisture_big_trees.csv')
# Create necessary directories
create_directories(base_path)

# Define the range of years
years = range(2022, 2024)

# Load and merge the data from all files
all_data = []
for year in years:
    netcdf_file_path = netcdf_file_path_template.format(year)
    if os.path.exists(netcdf_file_path):
        print(f"Processing data for year {year}...")
        try:
            ds = xr.open_dataset(netcdf_file_path)
            # Select the soil moisture variable and average over latitude and longitude
            soil_moisture = ds['swvl1'].mean(dim=['latitude', 'longitude'])
            soil_moisture_df = soil_moisture.to_dataframe().reset_index()
            soil_moisture_df['Date'] = pd.to_datetime(soil_moisture_df['time'])
            soil_moisture_df = soil_moisture_df[['Date', 'swvl1']].rename(columns={'swvl1': 'Soil_Moisture'})
            soil_moisture_df = soil_moisture_df.drop_duplicates(subset=['Date'])
            all_data.append(soil_moisture_df)
        except Exception as e:
            print(f"Error occurred while processing data for year {year}: {e}")
            continue
    else:
        print(f"Data for year {year} does not exist. Skipping...")

# Concatenate all dataframes
if all_data:
    final_df = pd.concat(all_data)
    final_df = final_df.sort_values(by='Date').reset_index(drop=True)
    final_df.to_csv(csv_file_path, index=False)
    print(f"Data saved to {csv_file_path}")

    # Plot the data
    plt.figure(figsize=(14, 7))
    plt.plot(final_df['Date'], final_df['Soil_Moisture'], label='Soil Moisture')
    plt.xlabel('Date')
    plt.ylabel('Soil Moisture (m³/m³)')
    plt.title('Daily Soil Moisture Time Series for Big Trees near Santa Cruz')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(base_path, 'soil_moisture_plot.png'))
    print(f"Plot saved to {os.path.join(base_path, 'soil_moisture_plot.png')}")
    plt.show()
else:
    print("No data was retrieved.")
