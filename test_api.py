import cdsapi
import requests

# Modify the session to enable debugging at the HTTP level
requests.Session().hooks['response'].append(lambda r, *args, **kwargs: print(r.request.headers))

c = cdsapi.Client()

try:
    c.retrieve(
        'cems-glofas-forecast',
        {
            'variable': 'river_discharge_in_the_last_24_hours',
            'format': 'grib',
            'system_version': 'operational',
            'hydrological_model': 'lisflood',
            'year': '2022',
            'month': '12',
            'day': '01',
            'leadtime_hour': [
                '24', '48', '72',
                '96', '120', '144'
            ],
            'area': [
                50, 10, 40, 20  # Adjusted for a specific smaller region
            ],
            'product_type': [
                'control_forecast'
            ],
        },
        'download.grib'
    )
except Exception as e:
    print("Failed to retrieve data:", e)

