
# Standard library imports
import os
import json
import shutil
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta
from math import sqrt
from pathlib import Path
import pickle
import re
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Third-party imports
import boto3
import botocore
import cdsapi
import dataretrieval.nwis as nwis
import fsspec
import geopandas as gpd
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyproj
import requests
import s3fs
import xarray as xr
from google.cloud import storage
from haversine import haversine, Unit
from pyproj import Transformer
from shapely.geometry import Point


# Setup basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration and setup
os.chdir('/home/jaguir26/projects')

def create_directory_NAME(base_path, folder_name):
    """Ensure directory exists and create if not."""
    directory_path = Path(base_path) / folder_name
    directory_path.mkdir(parents=True, exist_ok=True)
    return directory_path

# Directory structure setup
base_path = Path.cwd()
directory_path_project = create_directory_NAME(base_path, 'Project')
directory_path_input = create_directory_NAME(directory_path_project, 'Input')
directory_path_output = create_directory_NAME(directory_path_project, 'Output')
directory_path_input_id_river = create_directory_NAME(directory_path_input, 'ID_River')
directory_path_nws_coord = create_directory_NAME(directory_path_input, 'NWS-Coordinates')
directory_path_retro = create_directory_NAME(directory_path_input, 'Retrospective_Analysis')
directory_path_input_exAL = create_directory_NAME(directory_path_input, 'exAL')
directory_path_retro_nws = create_directory_NAME(directory_path_retro, 'NWS')
directory_path_retro_glofas = create_directory_NAME(directory_path_retro, 'GLOFAS')
directory_path_input_covariates = create_directory_NAME(directory_path_input_exAL, 'covariates')
directory_path_input_model = create_directory_NAME(directory_path_input_exAL, 'model_outputs')
directory_path_input_parameters = create_directory_NAME(directory_path_input_exAL, 'parameters')
directory_path_input_R_script = create_directory_NAME(directory_path_input_exAL, 'R_script')
directory_path_output_id_river = create_directory_NAME(directory_path_output, 'ID_River')

# Constants and initial configurations
CFSToCMS_CONVERSION_FACTOR = 0.0283168466
site_code = '11160500'
start_usgs = '1979-01-01'
end_usgs = datetime.today().strftime('%Y-%m-%d')

# Fetch and process data for the site
df = nwis.get_record(sites=site_code, service='dv', parameterCd='00060', statCd='00003',
                     start=start_usgs, end=end_usgs)
df['log_discharge'] = np.log(df['00060_Mean'].astype(float) + 1)
df = df[['log_discharge']]
df['discharge_cfs'] = np.exp(df['log_discharge']) - 1
df['discharge_cms'] = df['discharge_cfs'] * CFSToCMS_CONVERSION_FACTOR
df['log_discharge_cms'] = np.log(df['discharge_cms'] + 1)

# Site information and coordinates
site_info = nwis.get_record(sites=site_code, service='site')
latitude, longitude = float(site_info['dec_lat_va'][0]), float(site_info['dec_long_va'][0])
target_location = (latitude, longitude)
print(f"The coordinates for site {site_code} are {target_location}")

start_forecast = '2024-01-17'

def filter_dataframe(df, start_forecast, pre_days, post_days):
    """Filter DataFrame based on forecast date and days before/after."""
    start_forecast_dt = datetime.strptime(start_forecast, '%Y-%m-%d')
    start_filter_dt = start_forecast_dt - timedelta(days=pre_days)
    end_filter_dt = start_forecast_dt + timedelta(days=post_days)
    df_filtered = df.loc[start_filter_dt.strftime('%Y-%m-%d'):end_filter_dt.strftime('%Y-%m-%d')]
    return df_filtered

df_filtered = filter_dataframe(df, start_forecast, 10, 45)

def convert_date_format(date_str):
    """Convert date string from 'YYYY-MM-DD' to 'YYYYMMDD'."""
    return date_str.replace("-", "")

start_forecast_joint = convert_date_format(start_forecast)

# Directory paths for input and output based on the site code and forecast date
directory_path_input_ID = create_directory_NAME(directory_path_input_id_river, site_code)
directory_path_input_id_river_frsct_date = create_directory_NAME(directory_path_input_ID, 'Start_Forecast_Date')
directory_path_input_id_river_csv = create_directory_NAME(directory_path_input_ID, 'USGS_csv')
directory_input_id_frsc = create_directory_NAME(directory_path_input_id_river_frsct_date, start_forecast_joint)

directory_path_output_ID = create_directory_NAME(directory_path_output_id_river, site_code)
directory_path_output_id_river_frsct_date = create_directory_NAME(directory_path_output_ID, 'Start_Forecast_Date')
directory_output_id_frsc = create_directory_NAME(directory_path_output_id_river_frsct_date, start_forecast_joint)

# Setup for forecasts (inputs) and model outputs (outputs)
directory_glofas_frsc = create_directory_NAME(directory_input_id_frsc, 'GLOFAS_Forecasts')
directory_nws_frsc = create_directory_NAME(directory_input_id_frsc, 'NWS_Forecasts')
directory_path_model_output = create_directory_NAME(directory_output_id_frsc, 'exAL_output')
directory_path_figures = create_directory_NAME(directory_output_id_frsc, 'Figures')


# Save data to CSV
csv_file_path = directory_path_input_id_river_csv / f'{site_code}_{start_usgs}_{end_usgs}.csv'
if not csv_file_path.exists():
    df.to_csv(csv_file_path)
    print(f"Data saved as CSV at {csv_file_path}")
else:
    print(f"File already exists: {csv_file_path}")

# Example function to save and load data using pickle
def save_data(data, path):
    """Save data to a file using pickle."""
    with open(path, 'wb') as f:
        pickle.dump(data, f)

def load_data(path):
    """Load data from a pickle file."""
    with open(path, 'rb') as f:
        return pickle.load(f)

# Path to save/load data
saved_data_path = directory_path_nws_coord / 'saved_data.pkl'


# Check if the saved data exists
if os.path.exists(saved_data_path):
    print("Loading data from disk...")
    loaded_data = load_data(saved_data_path)
    gdf_projected = loaded_data['gdf_projected']
    closest_feature = loaded_data['closest_feature']
    closest_centroid_geometry = loaded_data['closest_centroid_geometry']
    closest_x = loaded_data['closest_x']
    closest_y = loaded_data['closest_y']
    closest_lon = loaded_data['closest_lon']
    closest_lat = loaded_data['closest_lat']
else:
    print("Performing original computations...")
    # Your original code starts here
    gdf_path = directory_path_nws_coord + '/NWM_v3_hydrofabric.gdb'
    gdf = gpd.read_file(gdf_path, driver='FileGDB', layer='nwm_reaches_conus')
    gdf_projected = gdf.to_crs(epsg=5070)
    gdf_projected.rename(columns={'ID': 'feature_id'}, inplace=True)
    gdf_projected['centroid'] = gdf_projected['geometry'].centroid
    transformer = Transformer.from_crs(4326, 5070, always_xy=True)
    target_x, target_y = transformer.transform(target_lon, target_lat)
    target_point = Point(target_x, target_y)
    gdf_projected['distance_to_target'] = gdf_projected['centroid'].apply(lambda point: point.distance(target_point))
    closest_feature = gdf_projected.loc[gdf_projected['distance_to_target'].idxmin()]['feature_id']
    closest_centroid_geometry = gdf_projected.loc[gdf_projected['feature_id'] == closest_feature]['centroid'].iloc[0]
    closest_x = closest_centroid_geometry.x
    closest_y = closest_centroid_geometry.y
    reverse_transformer = Transformer.from_crs(5070, 4326, always_xy=True)
    closest_lon, closest_lat = reverse_transformer.transform(closest_x, closest_y)
    
    # Saving data for future use
    print("Saving data to disk...")
    data_to_save = {
        'gdf_projected': gdf_projected,
        'closest_feature': closest_feature,
        'closest_centroid_geometry': closest_centroid_geometry,
        'closest_x': closest_x,
        'closest_y': closest_y,
        'closest_lon': closest_lon,
        'closest_lat': closest_lat
    }
    save_data(data_to_save, saved_data_path)

print("Data ready.")

def construct_blob_names(start_date, end_date):
    blob_names = []
    exclude_date = datetime(2019, 3, 10)  # Date to exclude
    
    for single_date in (start_date + timedelta(n) for n in range((end_date - start_date).days + 1)):
        # Skip the excluded date
        if single_date == exclude_date:
            continue

        date_str = single_date.strftime('%Y%m%d')
        
        # Adjust the lead times based on date
        if single_date >= datetime(2021, 4, 21):
            lead_times = range(1, 241)  # Hourly intervals
        else:
            lead_times = range(3, 241, 3)  # 3-hour intervals
        
        if single_date < datetime(2019, 6, 19):
            # Single member forecasts before 2019-06-19, using t00z initialization time
            for lead_time in lead_times:
                blob_name = f"nwm.{date_str}/medium_range/nwm.t00z.medium_range.channel_rt.f{lead_time:03}.conus.nc"
                blob_names.append(blob_name)
        else:
            # Multiple members forecasts from 2019-06-19 onwards, using t12z initialization time
            for ensemble_num in range(1, 8):  # Adjust based on actual ensemble numbers available
                ensemble_dir = f"medium_range_mem{ensemble_num}"
                for lead_time in lead_times:
                    max_lead_time = 240 if ensemble_num == 1 else 204  # Adjust as necessary
                    if lead_time <= max_lead_time:
                        # Note the adjustment to t12z for the initialization time
                        blob_name = f"nwm.{date_str}/{ensemble_dir}/nwm.t12z.medium_range.channel_rt_{ensemble_num}.f{lead_time:03}.conus.nc"
                        blob_names.append(blob_name)
    
    return blob_names

def extract_value_from_blob(blob_name, closest_feature):
    client = storage.Client.create_anonymous_client()
    bucket = client.bucket('national-water-model')
    blob = bucket.blob(blob_name)
    
    try:
        #logging.info(f"Starting download: {blob_name}")
        with tempfile.NamedTemporaryFile() as temp_file:
            blob.download_to_filename(temp_file.name)
            ds = xr.open_dataset(temp_file.name)
            value = ds.sel(feature_id=int(closest_feature))['streamflow'].values.item()
            ds.close()
            #logging.info(f"Successfully processed {blob_name}: {value}")
            return (blob_name, value)
    except Exception as e:
        logging.error(f"Error processing {blob_name}: {e}")
        return (blob_name, None)


def process_blobs(blob_names, closest_feature, results_filepath):
    # Load previously saved results or initialize a new dictionary
    results = load_existing_results(results_filepath)
    
    # Calculate the total number of blobs and the number of already processed blobs
    total_blobs = len(blob_names)
    processed_count = len(results)  # Count how many blobs have been processed already

    # Initialize ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_blob = {}
        
        for blob_name in blob_names:
            # Skip processing blobs that are already in the results
            if blob_name not in results:
                future_to_blob[executor.submit(extract_value_from_blob, blob_name, closest_feature)] = blob_name

        # Iterate over the futures as they complete
        for future in as_completed(future_to_blob):
            blob_name = future_to_blob[future]
            try:
                # Extract result for the completed future
                blob_name, value = future.result()
                if value is not None:
                    # Update the results dictionary
                    results[blob_name] = value
                    processed_count += 1  # Increment the processed count
                    completion_percentage = (processed_count / total_blobs) * 100
                    
                    # Periodically save results to disk
                    if processed_count % 100 == 0 or processed_count == total_blobs:
                        save_results(results, results_filepath)
                        logging.info(f"Progress: {processed_count}/{total_blobs} blobs processed. Completion: {completion_percentage:.2f}%")
            except Exception as e:
                logging.error(f"Error with blob {blob_name}: {e}")

    # Save the final results to disk
    save_results(results, results_filepath)
    #logging.info("Completed processing. Results saved.")


def load_existing_results(filepath):
    backup_path = filepath.with_suffix('.bak')

    def attempt_load(path):
        try:
            with open(path, 'rb') as f:
                return pickle.load(f), True
        except (EOFError, FileNotFoundError) as e:
            logging.error(f"Failed to load data from {path}: {e}")
            return {}, False

    results, success = attempt_load(filepath)
    if not success:
        logging.info(f"Attempting to recover from backup {backup_path}.")
        results, backup_success = attempt_load(backup_path)
        if backup_success:
            logging.info(f"Successfully recovered data from {backup_path}.")
        else:
            logging.error("Failed to recover data from both primary and backup files.")
    
    return results

def save_results(data, filepath):
    temp_fd, temp_name = tempfile.mkstemp(dir=filepath.parent)
    backup_path = filepath.with_suffix('.bak')
    
    try:
        with os.fdopen(temp_fd, 'wb') as tmp:
            pickle.dump(data, tmp)
        os.replace(temp_name, filepath)
        shutil.copyfile(filepath, backup_path)
        #logging.info(f"Successfully saved results to {filepath} and backup to {backup_path}.")
    except Exception as e:
        logging.error(f"Failed to save data: {e}")
        try:
            os.remove(temp_name)
        except OSError as os_err:
            logging.error(f"Error cleaning up temporary file: {os_err}")

# Example usage remains unchanged
start_date = datetime(2018, 9, 17)
end_date = datetime(2024, 2, 20)  # Adjusted for demonstration
blob_names = construct_blob_names(start_date, end_date)
results_filepath = Path('results.pkl')  # Converts the string to a Path object

process_blobs(blob_names, closest_feature, results_filepath)