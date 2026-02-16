Manual boundary probes for selected GloFAS forecast combos.
Purpose: supplement refine runs with explicit date-level checks under per-request timeout.
Method:
- dataset: cems-glofas-forecast
- variable: river_discharge_in_the_last_24_hours
- data_format: grib2
- download_format: zip
- area bbox: [37.2443931,-122.272464,36.8443931,-121.872464]
- timeout: 70 seconds per request
- cdsapi.Client(retry_max=1, sleep_max=5)

Notes:
- status=ok means retrieve+download completed and file written.
- status=invalid_request means explicit 400 invalid combination response.
- status=timeout means request did not complete before timeout (availability unresolved).
