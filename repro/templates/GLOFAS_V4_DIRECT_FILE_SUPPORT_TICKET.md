Subject: Access to GloFAS v4.0 legacy global reanalysis NetCDF direct file

Hello ECMWF/CEMS support,

We are preparing a reproducible audit and parity check between EWDS historical selectors and legacy JRC reanalysis archives.

Context:
- We can access the legacy v3.0 direct file:
  `https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS-RA/streamflow_analysis/LATEST/dis_1980_2018.nc`
- For v4.0 (`1980-01-01` to `2022-07-31`), the JRC catalog entry appears as `WEB_SERVICE` and points to EWDS dataset access.

Request:
1. Is there an official direct-file NetCDF URL for the complete v4.0 global legacy hydrological reanalysis archive (similar to v3.0)?
2. If yes, please provide the canonical URL and expected checksum/file size metadata.
3. If no, please confirm the recommended API-based workflow to reproduce an equivalent full archive and whether this is considered equivalent for parity checks.

Dataset references:
- v4.0 JRC entry: `https://data.jrc.ec.europa.eu/dataset/f96b7a19-0133-4105-a879-0536991ca9c5`
- EWDS historical dataset: `https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical?tab=overview`

Thanks.
