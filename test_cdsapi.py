import os
import pygrib
import numpy as np
import pandas as pd
from haversine import haversine, Unit

# Directories
base_directory = '/home/jaguir26/projects/Project/Input/GLOFAS/Medium_Range'
output_file = '/home/jaguir26/projects/Project/Input/GLOFAS/consolidated_glofas_data.csv'

# Initialize an empty list to store the consolidated data
data_list = []

def process_glofas_data(grbs, closest_indices):
    if grbs is None or closest_indices is None:
        print("GRIB file or closest indices not provided.")
        return []

    closest_i, closest_j = closest_indices
    glofas_data = []

    for grb in grbs:
        lead_time = grb['forecastTime']
        ensemble_member = grb['perturbationNumber']
        data_value = grb.values[closest_i, closest_j]
        glofas_data.append((lead_time, ensemble_member, data_value))

    grbs.close()
    return glofas_data

def convert_longitude_to_neg_180_180(lon):
    if lon > 180:
        return lon - 360
    return lon

def convert_longitude_to_0_360(lon):
    if lon < 0:
        return lon + 360
    return lon

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
    
    return closest_coordinates_glofas, closest_i, closest_j, min_distance

# Main processing loop
target_location = (34.05, -118.25)  # Example coordinates, replace with actual coordinates

for date_folder in sorted(os.listdir(base_directory)):
    date_folder_path = os.path.join(base_directory, date_folder)
    if not os.path.isdir(date_folder_path):
        continue

    for file_name in os.listdir(date_folder_path):
        if file_name.endswith('.grib'):
            file_path = os.path.join(date_folder_path, file_name)
            grbs = pygrib.open(file_path)
            closest_coordinates_glofas, closest_i, closest_j, min_distance = find_closest_coordinates(grbs, target_location)
            if closest_coordinates_glofas:
                print(f"Processing file {file_name} for date {date_folder}")
                glofas_data = process_glofas_data(grbs, (closest_i, closest_j))

                # Append data to the list
                for lead_time, ensemble_member, discharge in glofas_data:
                    data_list.append({
                        'start_forecast': date_folder,
                        'lead_time': lead_time,
                        'ensemble_member': ensemble_member,
                        'discharge': discharge
                    })

# Convert the list to a DataFrame
consolidated_df = pd.DataFrame(data_list)

# Save the consolidated DataFrame to a CSV file
consolidated_df.to_csv(output_file, index=False)
print(f"Consolidated data saved to {output_file}")
