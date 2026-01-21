import os
import cdsapi
from datetime import datetime, timedelta
import numpy as np
from haversine import haversine, Unit
import subprocess
import pygrib
import pandas as pd  # Import pandas

os.chdir('/home/jaguir26/projects/')

def create_directory_NAME(base_path, folder_name):
    directory_path = os.path.join(base_path, folder_name)
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    return directory_path

base_path = os.getcwd()
directory_path_project = create_directory_NAME(base_path, 'Project')

base_path = directory_path_project
directory_path_input = create_directory_NAME(base_path, 'Input')
directory_path_output = create_directory_NAME(base_path, 'Output')

base_path = directory_path_input
directory_path_retro = create_directory_NAME(base_path, 'Retrospective_Analysis')
directory_path_retro_glofas = create_directory_NAME(base_path, 'GLOFAS')

# Define the base directory for GloFAS medium-range forecasts
base_directory_glofas_frsc_med = create_directory_NAME(directory_path_retro_glofas, 'Medium_Range')

# Define the directory where you want to save the CSV file
dir = directory_path_input  # Replace with the actual directory path
os.makedirs(dir, exist_ok=True)

# Function to convert date format
def convert_date_format(date_str):
    return date_str.replace("-", "")

def choose_hydrological_model(start_forecast):
    lisflood_start_date = datetime.strptime('2021-05-26', '%Y-%m-%d')
    forecast_date = datetime.strptime(start_forecast, '%Y-%m-%d')
    if forecast_date < lisflood_start_date:
        return 'htessel_lisflood'
    else:
        return 'lisflood'

def convert_longitude_to_neg_180_180(lon):
    if lon > 180:
        return lon - 360
    return lon

def convert_longitude_to_0_360(lon):
    if lon < 0:
        return lon + 360
    return lon

def retrieve_glofas_data_medium(
    start_forecast,
    target_location,
    buffer=1,
    system_version='operational',
    product_type=['control_forecast', 'ensemble_perturbed_forecasts'],
    variable='river_discharge_in_the_last_24_hours',
    leadtime_hour=[str(i) for i in range(24, 721, 24)],
    base_directory_glofas_frsc_med=base_directory_glofas_frsc_med
):
    if datetime.strptime(start_forecast, '%Y-%m-%d') < datetime(2019, 11, 11):
        print("No data available before Nov 11, 2019 for medium-range forecasts.")
        return None
    
    hydrological_model = choose_hydrological_model(start_forecast)
    dt = datetime.strptime(start_forecast, '%Y-%m-%d')
    year, month, day = dt.year, dt.month, dt.day
    latitude, longitude = target_location
    area = [latitude + 2*buffer, longitude - buffer, latitude - 2*buffer, longitude + buffer]
    short_product_type = '_'.join(''.join(word[0] for word in item.split('_')) for item in product_type)
    short_variable = ''.join(word[0] for word in variable.split('_'))
    file_name_elements = [
        system_version[:3], 
        hydrological_model[:3], 
        short_product_type,
        short_variable,
        str(year), str(month).zfill(2), str(day).zfill(2),
        f"lt_{leadtime_hour[0]}_to_{leadtime_hour[-1]}", 
        f"area_{round(area[0], 2)}_{round(area[1], 2)}_{round(area[2], 2)}_{round(area[3], 2)}"
    ]
    file_name = '_'.join(file_name_elements) + '.grib'
    
    # Create a directory for this specific start forecast date
    date_directory = create_directory_NAME(base_directory_glofas_frsc_med, start_forecast)
    output_file = os.path.join(date_directory, file_name)
    
    if os.path.exists(output_file):
        print(f"File already exists: {output_file}")
        return output_file
    
    c = cdsapi.Client()
    retrieval_params = {
        'system_version': system_version,
        'hydrological_model': hydrological_model,
        'product_type': product_type,
        'variable': variable,
        'year': str(year),
        'month': str(month).zfill(2),
        'day': str(day).zfill(2),
        'leadtime_hour': leadtime_hour,
        'format': 'grib',
        'area': area
    }
    c.retrieve('cems-glofas-forecast', retrieval_params, output_file)
    print(f"Retrieval completed. Output file saved to: {output_file}")
    return output_file

def process_grib_file(file_path):
    if file_path is None or not os.path.exists(file_path):
        print(f"File does not exist or path is None: {file_path}")
        return None, None, None

    grbs = pygrib.open(file_path)
    unique_lead_times = set()
    unique_ensemble_members = set()

    for grb in grbs:
        unique_lead_times.add(grb['forecastTime'])
        unique_ensemble_members.add(grb['perturbationNumber'])

    grbs.seek(0)
    return grbs, unique_lead_times, unique_ensemble_members

def find_closest_coordinates(grbs, target_location):
    if grbs is None:
        return None, None, None, None

    min_distance = float('inf')
    closest_coordinates = None
    closest_i = None
    closest_j = None

    for grb in grbs:
        if grb['perturbationNumber'] == 0:
            latitudes, longitudes = grb.latlons()
            for i in range(len(latitudes)):
                for j in range(len(longitudes[0])):
                    coord = (latitudes[i][j], convert_longitude_to_neg_180_180(longitudes[i][j]))
                    # coord = (latitudes[i][j], longitudes[i][j])
                    distance = haversine(target_location, coord, unit=Unit.METERS)
                    if distance < min_distance:
                        min_distance = distance
                        closest_coordinates = coord
                        closest_i = i
                        closest_j = j
            break

    closest_coordinates_glofas = None
    if closest_coordinates:
        closest_coordinates_glofas = (closest_coordinates[0], convert_longitude_to_0_360(closest_coordinates[1]))
        # closest_coordinates_glofas = (closest_coordinates[0], closest_coordinates[1])
    
    
    return closest_coordinates_glofas, closest_i, closest_j, min_distance

def process_glofas_data(grbs, closest_indices):
    if grbs is None or closest_indices is None:
        print("GRIB file or closest indices not provided.")
        return {}, np.array([])

    closest_i, closest_j = closest_indices
    glofas_data = {}

    for grb in grbs:
        lead_time = grb['forecastTime']
        ensemble_member = grb['perturbationNumber']
        data_value = grb.values[closest_i, closest_j]
        glofas_data[(ensemble_member, lead_time)] = data_value

    grbs.close()

    sorted_ensemble_members = sorted(set(val[0] for val in glofas_data.keys()))
    sorted_lead_times = sorted(set(val[1] for val in glofas_data.keys()))
    ensemble_member_to_idx = {em: idx for idx, em in enumerate(sorted_ensemble_members)}
    lead_time_to_idx = {lt: idx for idx, lt in enumerate(sorted_lead_times)}

    glofas_array = np.zeros((len(sorted_ensemble_members), len(sorted_lead_times)))
    for (ensemble_member, lead_time), value in glofas_data.items():
        i = ensemble_member_to_idx[ensemble_member]
        j = lead_time_to_idx[lead_time]
        glofas_array[i, j] = value

    return glofas_data, glofas_array

# Loop over the date range and download data
date_range = pd.date_range(start='2022-11-01', end='2023-01-01', freq='D')
# target_location = (37.0443931, -122.072464)  # Example coordinates, replace with actual coordinates
# target_location = (37.449999999999996, -122.05000000000004)
target_location = (37.0443931, -122.072464)

for single_date in date_range:
    start_forecast = single_date.strftime('%Y-%m-%d')
    grib_file_path = retrieve_glofas_data_medium(start_forecast=start_forecast, target_location=target_location)
    grbs, unique_lead_times, unique_ensemble_members = process_grib_file(grib_file_path)
    closest_coordinates_glofas, closest_i, closest_j, min_distance = find_closest_coordinates(grbs, target_location)
    if closest_coordinates_glofas:
        print(f"Closest Coordinates in GloFAS format for {start_forecast}: {closest_coordinates_glofas}")
    glofas_data, glofas_array = process_glofas_data(grbs, (closest_i, closest_j))
