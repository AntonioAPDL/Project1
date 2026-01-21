import cdsapi
import os

c = cdsapi.Client()
# (37.0443931, -122.072464)
output_dir = "/data/muscat_data/jaguir26/project1_ucsc_phd/soil_moisture_data"
os.makedirs(output_dir, exist_ok=True)

years = list(range(1987, 2024))
months = [f"{m:02d}" for m in range(1, 13)]
days = [f"{d:02d}" for d in range(1, 32)]
hours = [f"{h:02d}:00" for h in range(24)]

for year in years:
    for month in months:
        target_file = os.path.join(output_dir, f"soil_moisture_big_trees_{year}_{month}.nc")

        # Skip if file already exists
        if os.path.exists(target_file):
            print(f"✅ Already downloaded: {target_file}")
            continue

        print(f"📦 Requesting ERA5 soil moisture for {year}-{month}...")

        try:
            c.retrieve(
                'reanalysis-era5-land',
                {
                    'product_type': 'reanalysis',
                    'variable': 'volumetric_soil_water_layer_1',
                    'year': str(year),
                    'month': month,
                    'day': days,
                    'time': hours,
                    'area': [37.05, -122.08, 37.03, -122.06],
                    'format': 'netcdf',
                },
                target_file
            )
            print(f"✅ Saved: {target_file}")

        except Exception as e:
            print(f"❌ Failed for {year}-{month}: {e}")
            continue
