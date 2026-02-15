# NWS/NWM and GloFAS Data Audit Plan (Metadata-Only, Version Compatibility)

Date created: 2026-02-14  
Last updated: 2026-02-15  
Scope: version, release, coverage, format, and access documentation only.  
Working constraint: metadata-first audit (no bulk dataset downloads).

## 1) Purpose

Build one compact, shareable documentation artifact that tracks, for NWS/NWM and GloFAS:

1. Model versions (chronological).
2. Release dates for each version.
3. Retrospective/reanalysis products linked to each version (including release date and coverage window).
4. Forecast ensemble products linked to each version (including release/operational date and coverage window).
5. Reforecast/hindcast products linked to each version (if available), with release date and coverage window.
6. Where each dataset lives and how it is accessed (authoritative portals and metadata endpoints).

## 2) One-Page Outline for the Final Shareable Documentation

1. Scope and purpose.
2. NWM version timeline and product mapping.
3. GloFAS version timeline and product mapping.
4. Data-location and access registry.
5. Compatibility review notes (version pairing rationale and unresolved transitions).
6. Open issues, unknowns, and next verification targets.
7. Source list and last-verified dates.

## 3) Version Summaries (Verified So Far)

### 3.1 NWS/NWM Operational Version Timeline

| nwm_version | operational_effective_date | evidence_source_id | notes |
|---|---|---|---|
| Initial NWM implementation (pre-v1.1 label) | 2016-08-16 | `NWM-URL-16` | Initial operational implementation notice (TIN). |
| 1.1 | 2017-05-08 | `NWM-URL-11` | SCN updated date from May 4 to May 8. |
| 1.2 | 2018-03-06 | `NWM-URL-12` | SCN states operationally running v1.2. |
| 2.0 | 2019-06-19 | `NWM-URL-13` | SCN states operationally running v2.0. |
| 2.1 | 2021-04-20 | `NWM-URL-14` | SCN states operationally running v2.1. |
| 3.0 | 2023-09-20 | `NWM-URL-15` | SCN states operationally running v3.0. |
| 3.1 | Proposed in PNS (comment period through 2026-01-29) | `NWM-URL-18` | Proposal notice found; implementation date not yet confirmed in this audit. |

### 3.2 NWS/NWM Retrospective by Version (AWS Registry)

| nwm_version | retrospective_product | retrospective_release_date | retrospective_coverage_start | retrospective_coverage_end | format_notes | key_access_locations | notes |
|---|---|---|---|---|---|---|---|
| 3.0 | NWM retrospective v3.0 | not explicitly listed | 1979-02 | 2023-01 | NetCDF and Zarr | `NWM-URL-05` | Registry states no streamflow/data assimilation in retrospective simulations. |
| 2.1 | NWM retrospective v2.1 | not explicitly listed | 1979-02 | 2020-12 | NetCDF (+ Zarr resources listed) | `NWM-URL-05` | AORC forcing notes provided in registry text. |
| 2.0 | NWM retrospective v2.0 | not explicitly listed | 1993-01 | 2018-12 | NetCDF (plus separate zarr streamflow bucket listed) | `NWM-URL-05` | Forcing notes in registry mention NLDAS for v2.0/v1.2. |
| 1.2 | NWM retrospective v1.2 | not explicitly listed | 1993-01 | 2017-12 | NetCDF | `NWM-URL-05` | Legacy retrospective bucket listed as `nwm-archive`. |

### 3.3 NWS/NWM Forecast and Access Snapshot

| nwm_version | forecast_operational_start | forecast_operational_end | forecast_config_summary | key_evidence_sources | notes |
|---|---|---|---|---|---|
| 1.0 (initial implementation) | 2016-08-16 | 2017-05-07 | Short-range deterministic to 15h; medium-range deterministic to 10 days (once/day); long-range 30-day ensemble (4 members/cycle, 16/day). | `NWM-URL-16` | Baseline configuration from TIN16-30. |
| 1.1 | 2017-05-08 | 2018-03-05 | Four configurations retained; short-range extended to 18h; medium-range cycle frequency increased to 4/day. | `NWM-URL-11`, `NWM-URL-16` | SCN17-41 update states date changed from May 4 to May 8. |
| 1.2 | 2018-03-06 | 2019-06-18 | Same four configurations as v1.1 (analysis/assimilation, short, medium, long). | `NWM-URL-12` | SCN18-16 says v1.2 framework unchanged from v1.1. |
| 2.0 | 2019-06-19 | 2021-04-19 | Medium-range products in per-member directories `medium_range_memM` (M=1..7); Hawaii forecast products added. | `NWM-URL-13` | SCN19-42 describes member-specific medium-range files. |
| 2.1 | 2021-04-20 | 2023-09-19 | v2.1 upgrade with PR/USVI additions and post-processing updates; forecast products remain operationally versioned. | `NWM-URL-14` | SCN20-119 confirms operational start date. |
| 3.0 | 2023-09-20 | ongoing (as of 2026-02-15) | CONUS medium-range six-member ensemble; long-range daily 16-member 30-day ensemble; added TWL coastal guidance in v3.0 era. | `NWM-URL-15`, `NWM-URL-04` | NWM About page reflects current v3.0 operational cycling. |
| 3.1 | not yet operationally confirmed in reviewed sources | not applicable | Proposal notice found; implementation pending approval/SCN. | `NWM-URL-18` | PNS25-77 is proposal-only, not implementation notice. |

### 3.4 NWS/NWM Reforecast or Hindcast Availability Check

| check_item | status | evidence | note |
|---|---|---|---|
| Forecast-side reforecast product by NWM version | not found in reviewed authoritative NWS/NODD sources | `NWM-URL-04`, `NWM-URL-05`, `NWM-URL-11`, `NWM-URL-12`, `NWM-URL-13`, `NWM-URL-14`, `NWM-URL-15`, `NWM-URL-17`, `NWM-URL-19` | No explicit versioned forecast reforecast/hindcast catalog entry found in reviewed NWS/NODD URLs. |
| Retrospective runs (historical simulations) | found | `NWM-URL-05` | Retrospective datasets are available and versioned, but these are not labeled as forecast reforecast products in the reviewed sources. |

### 3.5 GloFAS Operational Version Timeline

| glofas_version | released_in_production | evidence_source_id | notes |
|---|---|---|---|
| 4.4 | 2025-09-10 | `GLOFAS-URL-10` | Listed as latest operational release in versioning system. |
| 4.3 | 2025-06-04 | `GLOFAS-URL-10` | Versioning table entry. |
| 4.2 | 2024-11-12 | `GLOFAS-URL-10` | Versioning table entry. |
| 4.1 | 2024-02-28 | `GLOFAS-URL-10` | Versioning table entry. |
| 4.0 | 2023-07-26 | `GLOFAS-URL-10` | Versioning table entry; v4.0 page also confirms operational date. |
| 3.5 | 2023-06-28 | `GLOFAS-URL-10` | Versioning table entry. |
| 3.4 | 2022-12-14 | `GLOFAS-URL-10` | Versioning table entry. |
| 3.3 | 2022-10-19 | `GLOFAS-URL-10` | Versioning table entry. |
| 3.2 | 2021-10-27 | `GLOFAS-URL-10` | Versioning table entry. |
| 3.1 | 2021-05-26 | `GLOFAS-URL-10` | Versioning table entry. |
| 2.2 | 2020-12-09 (12UTC) | `GLOFAS-URL-10` | Versioning table entry. |
| 2.1 | 2019-11-05 (12UTC) | `GLOFAS-URL-10` | Versioning table entry; note shows later decommissioning. |
| 2.0 | 2018-11-14 (12UTC) | `GLOFAS-URL-10` | Versioning table entry. |
| 1.0 | 2018-04-23 (12UTC) | `GLOFAS-URL-10` | Versioning table entry. |

### 3.6 GloFAS Historical, Forecast, and Reforecast Metadata

| product_type | current_system_version_note | product_release_or_publication_date | coverage_start | coverage_end | format | key_access_locations | notes |
|---|---|---|---|---|---|---|---|
| historical | operational version listed as v4.0 (released 2023-07-26) | publication date: 2019-11-05 | 1979-01-01 | near real time | GRIB2, NetCDF-4 | `GLOFAS-URL-01` | Daily data; global except Antarctica; legacy versions also available. |
| forecast | current version listed as v4.0 (released 2023-07-26) | publication date: 2020-05-19 | 2019-11-05 (river discharge) | near real time | GRIB2, NetCDF-4 | `GLOFAS-URL-03` | Soil wetness/snow variables indicate operational coverage from 2024-02-28 onward. |
| reforecast | current version listed as v4.0 (released 2023-07-26) | publication date: 2020-12-09 | first reference date: 2023-03-27 | near real time generation (historical years 2003-2022 per reference date) | GRIB2 | `GLOFAS-URL-05` | 11-member ECMWF-ENS reforecasts, Monday/Thursday reference dates, 46-day lead time, weekly update. |

### 3.7 GloFAS EWDS API Version Options by Product (Retrieve Metadata)

| product_id | system_version options in retrieve API | product_type options | data_format options | key timing/options notes | evidence_source_id |
|---|---|---|---|---|---|
| `cems-glofas-historical` | `version_2_1`, `version_3_1`, `version_4_0` | `consolidated`, `intermediate` | `grib2`, `netcdf` | No leadtime field (historical product). | `GLOFAS-URL-09` |
| `cems-glofas-forecast` | `operational`, `version_2_1`, `version_3_1` | `control_forecast`, `ensemble_perturbed_forecasts` | `grib2`, `netcdf` | Leadtime enum spans 24 to 720h (24h step). | `GLOFAS-URL-09` |
| `cems-glofas-reforecast` | `version_2_2`, `version_3_1`, `version_4_0` | `control_reforecast`, `ensemble_perturbed_reforecast` | `grib2`, `netcdf` | Leadtime enum spans 24 to 1104h (24h step). | `GLOFAS-URL-09` |

## 4) Source Checklist (Metadata Documentation)

Track source review progress here. Use URL IDs from Section 7.

| source_id | center | priority | fields_to_capture | status | last_checked_utc | notes |
|---|---|---|---|---|---|---|
| `NWM-URL-04` | NWM | high | operational forecast configuration details | `done` | `2026-02-15` | NWM configuration/cycle details extracted. |
| `NWM-URL-05` | NWM | high | retrospective versions, coverage, forcing notes | `done` | `2026-02-15` | Versioned retrospective windows and bucket map extracted. |
| `NWM-URL-15` | NWM | high | v3.0 operational effective date | `done` | `2026-02-15` | SCN23-76 confirms v3.0 effective date. |
| `NWM-URL-11/12/13/14/16` | NWM | high | historical operational version release dates | `done` | `2026-02-15` | TIN/SCNs used to reconstruct timeline 2016-2023. |
| `NWM-URL-17` | NWM | high | short-range archive scope and access endpoints | `done` | `2026-02-15` | Four-week rollover and bucket metadata extracted. |
| `NWM-URL-01` | NWM | medium | Planetary Computer metadata detail | `in_progress` | `2026-02-15` | Page is JS-heavy in this audit context; use supporting docs/notes where needed. |
| `GLOFAS-URL-01` | GloFAS | high | historical coverage, formats, release metadata | `done` | `2026-02-15` | Historical metadata extracted (coverage, format, DOI, dates). |
| `GLOFAS-URL-03` | GloFAS | high | forecast coverage, formats, release metadata | `done` | `2026-02-15` | Forecast metadata extracted (coverage, format, DOI, dates). |
| `GLOFAS-URL-05` | GloFAS | high | reforecast cadence, lead time, format, release metadata | `done` | `2026-02-15` | Reforecast metadata extracted (twice-weekly, 46-day, 11-member). |
| `GLOFAS-URL-10` | GloFAS | high | official version chronology and release dates | `done` | `2026-02-15` | Versioning system table extracted through v4.4. |
| `GLOFAS-URL-11` | GloFAS | high | latest operational release page content | `done` | `2026-02-15` | Cross-checks current operational release against versioning table. |
| `GLOFAS-URL-12` | GloFAS | medium | v4.0 release implementation details | `done` | `2026-02-15` | Used as supporting release-details reference for v4.0 era datasets. |
| `GLOFAS-URL-04` | GloFAS | medium | method chain notes (HTESSEL/LISFLOOD/IFS) | `done` | `2026-02-15` | Modelling-chain inputs and routing notes extracted. |
| `GLOFAS-URL-06/07/08/09` | GloFAS | medium | API auth and metadata endpoint behavior | `done` | `2026-02-15` | API endpoint and auth setup information captured. |

## 5) Metadata-Only TODO Checklist

Status legend: `[ ]` not started, `[~]` in progress, `[x]` done

### 5.1 Shared tasks

- [x] `A-01`: Lock final filename/location for the shareable data documentation artifact.
  Completion note: canonical path is locked to `repro/NWS_NWM_GLOFAS_DATA_AUDIT_PLAN.md` (see Section 8.1).
- [x] `A-02`: Define fixed date format and null-policy for unknown fields.
  Completion note: date and null policies are locked in Section 8.2.
- [x] `A-03`: Define source confidence labels (`authoritative`, `supporting`, `to_classify`).
  Completion note: label definitions are locked in Section 8.3.
- [x] `A-04`: Add a source-verification log (`source_url`, `claim`, `verified_on`, `status`, `notes`).
  Completion note: source-verification log template added in Section 8.4.
- [x] `A-05`: Keep this audit metadata-only (no bulk data transfer).
  Completion note: metadata-only policy is locked in document header and Section 8.5.

### 5.2 NWS/NWM tasks

- [x] `NWM-01`: Build complete NWM version chronology for the project period.
  Completion note: timeline completed from official TIN/SCN notices (`NWM-URL-16`, `NWM-URL-11`, `NWM-URL-12`, `NWM-URL-13`, `NWM-URL-14`, `NWM-URL-15`), with proposal-only status recorded for v3.1 (`NWM-URL-18`).
- [x] `NWM-02`: Link each version to retrospective/reanalysis products and release/coverage dates.
  Completion note: retrospective version-to-coverage mapping completed from `NWM-URL-05`; explicit gap recorded: authoritative per-version retrospective release dates are not explicitly listed in the reviewed registry/docs.
- [x] `NWM-03`: Link each version to forecast products and release/coverage dates.
  Completion note: version-to-forecast operational windows and configuration changes documented from SCNs/TIN (`NWM-URL-11` through `NWM-URL-16`) plus current NWM operations page (`NWM-URL-04`) and NODD short-range archive metadata (`NWM-URL-17`).
- [x] `NWM-04`: Confirm whether reforecast/hindcast products exist per version.
  Completion note: no authoritative NWS/NODD source in the reviewed URL set explicitly documents a versioned forecast reforecast/hindcast product for NWM; status recorded as `not found in reviewed sources` (see Section 3.4).
- [x] `NWM-05`: Record storage/access locations per product (portal, bucket/container, API/catalog endpoint).
  Completion note: completed using `NWM-URL-04`, `NWM-URL-05`, `NWM-URL-17`, `NWM-URL-09`, `NWM-URL-10`, `NWM-URL-03`, and supporting cloud-notes context from `NWM-URL-01`/`NWM-URL-02`.
- [x] `NWM-06`: Mark unresolved transitions or version-link uncertainties for follow-up.
  Completion note: unresolved items explicitly recorded: (1) v3.1 is proposal-only pending SCN implementation notice, (2) retrospective per-version release dates are not explicitly published in reviewed sources, (3) forecast-side reforecast/hindcast product remains undocumented in reviewed authoritative URLs.

### 5.3 GloFAS tasks

- [x] `GLOFAS-01`: Build complete GloFAS version chronology (including legacy versions).
  Completion note: chronology completed from official versioning system (`GLOFAS-URL-10`), including production release dates from v1.0 through v4.4.
- [x] `GLOFAS-02`: Link each version to historical/retrospective products and release/coverage dates.
  Completion note: historical dataset metadata captured (`GLOFAS-URL-01`) and API system-version options verified (`version_2_1`, `version_3_1`, `version_4_0`) via retrieve endpoint (`GLOFAS-URL-09`). Explicit gap: authoritative per-version coverage date ranges for all legacy historical versions are not published as a single table in reviewed sources.
- [x] `GLOFAS-03`: Link each version to forecast products and release/coverage dates.
  Completion note: forecast dataset metadata captured (`GLOFAS-URL-03`) and API system-version options verified (`operational`, `version_2_1`, `version_3_1`) via retrieve endpoint (`GLOFAS-URL-09`). Explicit gap: retrieve metadata does not explicitly map `operational` to a named numeric version in the endpoint itself.
- [x] `GLOFAS-04`: Link each version to reforecast products and release/coverage dates (if available).
  Completion note: reforecast dataset metadata captured (`GLOFAS-URL-05`) and API system-version options verified (`version_2_2`, `version_3_1`, `version_4_0`) via retrieve endpoint (`GLOFAS-URL-09`), including 46-day lead-time design and twice-weekly cadence.
- [x] `GLOFAS-05`: Record storage/access locations per product (EWDS catalogue/retrieve, IDs, endpoint notes).
  Completion note: recorded using dataset pages (`GLOFAS-URL-01`, `GLOFAS-URL-03`, `GLOFAS-URL-05`), catalogue collection endpoints (`GLOFAS-URL-07`, `GLOFAS-URL-08`), and retrieve process endpoints (`GLOFAS-URL-09`).
- [x] `GLOFAS-06`: Mark unresolved transitions or version-link uncertainties for follow-up.
  Completion note: unresolved items explicitly logged: (1) versioning page indicates operational v4.4 while EWDS dataset tables still label current version as v4.0 in reviewed pages, (2) no single authoritative table found that maps each operational version to exact historical/forecast/reforecast coverage windows for every legacy version, (3) forecast retrieve endpoint uses `operational` alias without explicit numeric expansion in endpoint metadata.

### 5.4 Finalization tasks

- [x] `F-01`: Complete both version summary tables with all required fields.
  Completion note: NWM and GloFAS version summary sections are fully populated with verified fields, and unresolved values are explicitly marked (`not found`/`unknown`).
- [x] `F-02`: Add a compact compatibility note per version pairing (`allowed`, `conditional`, `blocked`) with short rationale.
  Completion note: compact pairing decisions are defined in Section 9.
- [x] `F-03`: Add a one-page collaborator summary (safe pairings, conditional pairings, open questions).
  Completion note: collaborator summary added in Section 10.
- [x] `F-04`: Define update cadence and trigger events (new release, archive metadata update, revised methods pages).
  Completion note: cadence and trigger policy added in Section 11.

## 6) Flexible Compatibility Review Notes

Use this section for evidence-first notes while avoiding rigid assumptions until metadata is confirmed.

For each candidate retrospective -> forecast pairing, document:

1. Version relationship (same version, related version, unknown).
2. Release/operational timeline alignment.
3. Retrospective product linkage evidence.
4. Forecast/reforecast product linkage evidence.
5. Any transition-window ambiguity.
6. Current decision tag: `allowed`, `conditional`, or `blocked`.

## 7) Seed URLs

### 7.1 NWS/NWM

- `NWM-URL-01`: `https://planetarycomputer.microsoft.com/dataset/storage/noaa-nwm`
- `NWM-URL-02`: `https://github.com/TomAugspurger/noaa-nwm`
- `NWM-URL-03`: `https://www.weather.gov/media/wrn/calendar/NWS-NODD-Microsoft-NWM-Office-Hours-Notes.pdf`
- `NWM-URL-04`: `https://water.noaa.gov/about/nwm`
- `NWM-URL-05`: `https://registry.opendata.aws/nwm-archive/`
- `NWM-URL-06`: `https://github.com/NOAA-Big-Data-Program/nodd-data-docs/blob/main/nwm/README.md`
- `NWM-URL-07`: `https://aws.amazon.com/marketplace/pp/prodview-g6lcchc7brshw`
- `NWM-URL-08`: `https://www.weather.gov/media/owp/operations/nwps_user_guide.pdf`
- `NWM-URL-09`: `https://nomads.ncep.noaa.gov/pub/data/nccf/com/nwm/prod/`
- `NWM-URL-10`: `https://maps.water.noaa.gov/server/rest/services/nwm`
- `NWM-URL-11`: `https://www.weather.gov/media/notification/pdfs/scn17-41natl_water_model_aaa.pdf`
- `NWM-URL-12`: `https://www.weather.gov/media/notification/pdfs/scn18-16national_water_model.pdf`
- `NWM-URL-13`: `https://www.weather.gov/media/notification/pdf2/scn19-42natl_water_model.pdf`
- `NWM-URL-14`: `https://www.weather.gov/media/notification/pdf2/scn20-119nwm_v2.1_aad.pdf`
- `NWM-URL-15`: `https://www.weather.gov/media/notification/pdf_2023_24/scn23-76_national_water_model_v3.0_aab.pdf`
- `NWM-URL-16`: `https://www.weather.gov/media/notification/tins/tin16-30natl_water_model.pdf`
- `NWM-URL-17`: `https://registry.opendata.aws/noaa-nwm-pds/`
- `NWM-URL-18`: `https://preview.weather.gov/notification/`
- `NWM-URL-19`: `https://water.noaa.gov/about/output_file_contents`

### 7.2 GloFAS

- `GLOFAS-URL-01`: `https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical?tab=overview`
- `GLOFAS-URL-02`: `https://confluence.ecmwf.int/plugins/servlet/mobile?contentId=265028796#content/view/265028624`
- `GLOFAS-URL-03`: `https://ewds.climate.copernicus.eu/datasets/cems-glofas-forecast?tab=overview`
- `GLOFAS-URL-04`: `https://global-flood.emergency.copernicus.eu/general-information/glofas-methods/`
- `GLOFAS-URL-05`: `https://ewds.climate.copernicus.eu/datasets/cems-glofas-reforecast`
- `GLOFAS-URL-06`: `https://ewds.climate.copernicus.eu/how-to-api`
- `GLOFAS-URL-07`: `https://ewds.climate.copernicus.eu/api/catalogue/v1/`
- `GLOFAS-URL-08`: `https://ewds.climate.copernicus.eu/api/catalogue/v1/collections/cems-glofas-forecast`
- `GLOFAS-URL-09`: `https://ewds.climate.copernicus.eu/api/retrieve/v1/processes/cems-glofas-forecast`
- `GLOFAS-URL-10`: `https://confluence.ecmwf.int/display/CEMS/GloFAS%2Bversioning%2Bsystem`
- `GLOFAS-URL-11`: `https://confluence.ecmwf.int/display/CEMS/Latest%2Boperational%2BGloFAS%2Brelease`
- `GLOFAS-URL-12`: `https://confluence.ecmwf.int/pages/viewpage.action?pageId=388505179`

## 8) Shared Standards (Locked)

### 8.1 Canonical document location

- Canonical audit file: `repro/NWS_NWM_GLOFAS_DATA_AUDIT_PLAN.md`
- Document owner (current): project maintainer
- Scope boundary: metadata, versioning, coverage, and access documentation only

### 8.2 Date and null policy

| field type | policy |
|---|---|
| Date only | `YYYY-MM-DD` |
| Date-time | ISO 8601 UTC (e.g., `2026-02-15T00:00:00Z`) |
| Unknown scalar value | `unknown` |
| Not explicitly published in reviewed source | `not explicitly listed` |
| Not found after reviewed-source search | `not found in reviewed sources` |

### 8.3 Source confidence labels

| label | definition |
|---|---|
| `authoritative` | Official service owner documentation or official API/catalog metadata endpoint. |
| `supporting` | Reputable but non-authoritative explanatory source (e.g., community repos, office-hour notes). |
| `to_classify` | Source captured but confidence level not yet assigned. |

### 8.4 Source verification log template

| source_id | source_url | claim_checked | verdict | verified_on_utc | reviewer | notes |
|---|---|---|---|---|---|---|
| `<fill>` | `<fill>` | `<fill>` | `verified`/`partially_verified`/`not_found`/`conflict` | `<fill>` | `<fill>` | `<fill>` |

### 8.5 Metadata-only enforcement

1. No bulk download commands are part of this audit workflow.
2. Evidence must come from metadata pages, API/catalog descriptors, and official release notices.
3. Any unresolved field remains documented as unknown/not-found rather than inferred.

## 9) Compatibility Decisions (Compact, Current Evidence)

### 9.1 NWS/NWM pairing notes

| retrospective_version | forecast_version | decision | rationale | evidence |
|---|---|---|---|---|
| 3.0 retrospective | 3.0 forecast | `conditional` | Same version label, but retrospective publication date not explicitly listed and retrospective does not include streamflow DA. | `NWM-URL-05`, `NWM-URL-15` |
| 2.1 retrospective | 2.1 forecast | `conditional` | Same version label; retrospective and operational windows are documented but retrospective release-date metadata is incomplete. | `NWM-URL-05`, `NWM-URL-14` |
| 2.0 retrospective | 2.0 forecast | `conditional` | Same version label; similar metadata limitations on retrospective release-date publication. | `NWM-URL-05`, `NWM-URL-13` |
| 1.2 retrospective | 1.2 forecast | `conditional` | Same version label; legacy metadata is available but not complete for release-date fields. | `NWM-URL-05`, `NWM-URL-12` |
| Any cross-version retrospective->forecast pair | mixed | `blocked` | No reviewed authoritative mapping proving cross-version bias-transfer equivalence. | `NWM-URL-04`, `NWM-URL-05` |

### 9.2 GloFAS pairing notes

| historical_or_reforecast_version | forecast_version | decision | rationale | evidence |
|---|---|---|---|---|
| historical `version_3_1` | forecast `version_3_1` | `allowed` | Same explicit version identifier available in retrieve API metadata. | `GLOFAS-URL-09` |
| historical `version_2_1` | forecast `version_2_1` | `allowed` | Same explicit version identifier available in retrieve API metadata. | `GLOFAS-URL-09` |
| reforecast `version_3_1` | forecast `version_3_1` | `allowed` | Same explicit version identifier available in retrieve API metadata. | `GLOFAS-URL-09` |
| historical/reforecast `version_4_0` | forecast `operational` | `conditional` | Forecast endpoint uses `operational` alias; no explicit numeric expansion in endpoint metadata. | `GLOFAS-URL-09`, `GLOFAS-URL-10` |
| Any cross-version historical/reforecast->forecast pair | mixed | `blocked` | No reviewed authoritative source proves cross-version transfer compatibility as default. | `GLOFAS-URL-09`, `GLOFAS-URL-10` |

## 10) One-Page Collaborator Summary (Current)

### 10.1 What is ready now

1. NWM and GloFAS version timelines are populated from reviewed official sources.
2. Retrospective/historical, forecast, and reforecast metadata is mapped for both centers.
3. Key unresolved metadata gaps are explicitly documented instead of inferred.

### 10.2 Safe default pairing posture

1. Same-version pairs are preferred.
2. Cross-version pairs are blocked unless explicit authoritative equivalence is found.
3. Pairs involving unresolved version aliases or missing release metadata remain conditional.

### 10.3 Open questions

1. NWM forecast-side reforecast/hindcast product: not found in reviewed authoritative NWS/NODD URLs.
2. NWM retrospective per-version release dates: not explicitly listed in reviewed sources.
3. GloFAS `operational` alias mapping to numeric version in forecast retrieve metadata: not explicitly documented in endpoint metadata.

## 11) Update Cadence and Trigger Policy

| trigger | cadence | required action | output update |
|---|---|---|---|
| Routine maintenance | monthly | Re-check versioning pages, dataset overview pages, retrieve API inputs | Update Sections 3, 4, 5, 9, and `Last updated` date |
| New operational release notice | event-driven | Add new version row and assess pairing implications | Update Sections 3 and 9 |
| Archive/catalog metadata change | event-driven | Re-validate coverage windows, publication/update dates, format/options | Update Sections 3 and 4 |
| New evidence resolving an open question | event-driven | Move relevant item from open question to resolved status | Update Sections 5.2/5.3, 10.3, and 9 |

Policy:

1. Never overwrite a prior claim without updating evidence reference and verification date.
2. Keep unresolved items explicit (`unknown`, `not explicitly listed`, `not found in reviewed sources`).
