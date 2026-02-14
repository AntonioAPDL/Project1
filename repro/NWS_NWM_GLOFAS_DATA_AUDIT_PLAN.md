# NWS/NWM and GloFAS Data Audit Plan (Version Compatibility)

Date created: 2026-02-14  
Scope: planning checklist for a shareable data documentation artifact  
Purpose: track where data lives, model versions, temporal coverage, and retrospective-to-forecast compatibility rules.

## 1) Document Intent

This document is the planning scaffold for a collaborator-facing data documentation file focused on:

1. NWS/NOAA National Water Model (NWM)
2. ECMWF/Copernicus GloFAS

In scope:

1. Model-version chronology.
2. Retrospective/reanalysis and ensemble/reforecast availability by version.
3. Data locations and authoritative access points.
4. Explicit compatibility gates for retrospective-to-forecast pairing.

Out of scope:

1. Credentials or step-by-step download instructions.
2. Pipeline implementation details unrelated to version/data provenance.

## 2) One-Page Outline for the Final Shareable Documentation

1. Purpose and bias-transfer risk statement.
2. Centers and product families in scope (NWM, GloFAS).
3. Version timeline per center (chronological table).
4. Product matrix per version:
   - retrospective/reanalysis (coverage dates)
   - forecast ensemble (coverage dates)
   - reforecast/hindcast (coverage dates)
5. Operational/release timeline:
   - release date
   - operational start/end
   - transition/overlap windows
6. Data-access registry:
   - authoritative portals
   - programmatic entry points
   - storage location and formats
7. Compatibility matrix:
   - allowed version pairs
   - blocked/conditional pairs and rationale
8. Validation rules and pre-run gates.
9. Change log and verification history.
10. Quick links appendix (authoritative URLs).

## 3) TODO Checklist to Build the Documentation

Status legend: `[ ]` not started, `[~]` in progress, `[x]` done

### 3.1 Shared foundation

- [ ] `A-01`: Lock canonical filename/location and owner for ongoing maintenance.
- [ ] `A-02`: Define standard version keys (`center`, `system`, `major.minor`, `release_tag`) and UTC date format (`YYYY-MM-DD`).
- [ ] `A-03`: Lock source ranking policy: official operations docs > official dataset pages > archive metadata > third-party summaries.
- [ ] `A-04`: Create source-verification log fields: `verified_on`, `verified_by`, `evidence_url`, `notes`.
- [ ] `A-05`: Lock red-flag labels: `version_unknown`, `date_gap`, `transition_overlap`, `reforecast_unconfirmed`, `non_authoritative_only`.

### 3.2 NWS/NOAA NWM tasks

- [ ] `NWM-01`: Build complete NWM version chronology for the project analysis period.
- [ ] `NWM-02`: Record retrospective/reanalysis products and date coverage per version.
- [ ] `NWM-03`: Record ensemble forecast products and date coverage per version.
- [ ] `NWM-04`: Confirm whether reforecast/hindcast streams exist per version; if yes, record coverage and archive location.
- [ ] `NWM-05`: Record operational transition windows between versions.
- [ ] `NWM-06`: Classify anchor URLs as `authoritative`, `supporting`, or `to_classify`:
  - `https://planetarycomputer.microsoft.com/dataset/storage/noaa-nwm`
  - `https://github.com/TomAugspurger/noaa-nwm`
  - `https://www.weather.gov/media/wrn/calendar/NWS-NODD-Microsoft-NWM-Office-Hours-Notes.pdf`
  - `https://water.noaa.gov/about/nwm`
  - `https://registry.opendata.aws/nwm-archive/`
  - `https://github.com/NOAA-Big-Data-Program/nodd-data-docs/blob/main/nwm/README.md`
  - `https://aws.amazon.com/marketplace/pp/prodview-g6lcchc7brshw`
  - `https://www.weather.gov/media/owp/operations/nwps_user_guide.pdf` (mark relevance explicitly)
- [ ] `NWM-07`: Build storage/access map for each NWM stream (portal, bucket, format, partitioning, cadence).
- [ ] `NWM-08`: Mark uncertainty intervals where retrospective and forecast version identity is ambiguous.

### 3.3 ECMWF/Copernicus GloFAS tasks

- [ ] `GLOFAS-01`: Build complete GloFAS version chronology (including legacy versions on official pages).
- [ ] `GLOFAS-02`: Record historical/retrospective coverage by version.
- [ ] `GLOFAS-03`: Record operational forecast-ensemble coverage by version.
- [ ] `GLOFAS-04`: Confirm reforecast/hindcast availability, frequency, lead-time structure, and coverage.
- [ ] `GLOFAS-05`: Record release and operational transition windows, including documented ingredient changes.
- [ ] `GLOFAS-06`: Classify anchor URLs as `authoritative`, `supporting`, or `to_classify`:
  - `https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical?tab=overview`
  - `https://confluence.ecmwf.int/plugins/servlet/mobile?contentId=265028796#content/view/265028624`
  - `https://ewds.climate.copernicus.eu/datasets/cems-glofas-forecast?tab=overview`
  - `https://global-flood.emergency.copernicus.eu/general-information/glofas-methods/`
- [ ] `GLOFAS-07`: Build storage/access map for each GloFAS stream (portal/API, dataset IDs, variable/member metadata).
- [ ] `GLOFAS-08`: Mark uncertainty intervals where historical and forecast version identity is ambiguous.

### 3.4 Finalization tasks

- [ ] `F-01`: Build compatibility matrix by center (`allow`, `block`, `needs_review`) for retrospective->forecast pairings.
- [ ] `F-02`: Add explicit do-not-train/do-not-correct windows around unverified transitions.
- [ ] `F-03`: Add one-page collaborator summary: safe now vs blocked pending verification.
- [ ] `F-04`: Define monthly verification cadence plus trigger-based updates (new release, metadata revision, archive correction).

## 4) Data-Access Registry Template

```yaml
record_id: "<center>-<system>-<product_type>-<version>-<tag>"
center: "NWS_NOAA | ECMWF_COPERNICUS"
system: "NWM | GloFAS"
product_type: "retrospective | reanalysis | forecast_ensemble | reforecast_hindcast"
model_version:
  label: "<e.g., v3.0>"
  family: "<major branch if needed>"
  compatibility_group: "<same-model or approved pair-group id>"
temporal_coverage:
  data_start_utc: "YYYY-MM-DD"
  data_end_utc: "YYYY-MM-DD or ongoing"
  operational_start_utc: "YYYY-MM-DD or null"
  operational_end_utc: "YYYY-MM-DD or null"
release_metadata:
  release_date_utc: "YYYY-MM-DD or null"
  status: "operational | retrospective_only | deprecated | legacy"
ensemble_metadata:
  has_ensembles: true
  member_count: "<int or range or null>"
  lead_time_design: "<text>"
  has_reforecasts: "yes | no | unknown"
  reforecast_coverage: "<date range or null>"
storage_and_access:
  authoritative_portal: "<url>"
  programmatic_entrypoint: "<api/stac/cds/s3 url>"
  storage_location: "<bucket/container/path or dataset id>"
  file_format: "<grib/netcdf/zarr/csv/...>"
  partitioning: "<time/member/path pattern>"
  update_cadence: "<operational schedule or archive update notes>"
quality_and_lineage:
  source_rank: "authoritative | supporting | to_classify"
  verified_on_utc: "YYYY-MM-DD"
  verified_by: "<name>"
  evidence_urls:
    - "<url1>"
    - "<url2>"
  notes: "<free text>"
risk_flags:
  - "version_unknown | date_gap | transition_overlap | reforecast_unconfirmed | metadata_conflict"
compatibility_decision:
  can_pair_with:
    - "<target version id(s)>"
  decision: "allow | block | conditional"
  rationale: "<short reason>"
```

## 5) Compatibility Decision Rules (Pre-Pairing Gates)

1. Version identity gate:
   - Require exact model-version match, or an explicitly approved compatibility pair with documented rationale.
   - If version is unknown on either side, set decision to `block`.
2. Operational alignment gate:
   - Forecast valid time must fall inside the operational window of the forecast version.
   - Training retrospective period must correspond to the same version (or an approved pair).
3. Transition-window gate:
   - Any pair crossing cutover/overlap windows is flagged `transition_overlap`.
   - Default action is `block` until a documented transition policy exists.
4. Reforecast preference gate:
   - If version-matched reforecasts/hindcasts exist, prefer them for calibration and validation.
   - If absent, record downgrade rationale and require stronger out-of-sample diagnostics.
5. Storage provenance gate:
   - Only use records with at least one authoritative source and recent verification date.
   - Records with only supporting/third-party sources are `conditional` pending maintainer sign-off.
6. Coverage sufficiency gate:
   - Enforce minimum training duration and event-coverage thresholds (site/basin-specific).
   - If thresholds are not met, set decision to `block` or `conditional` with caveat.
7. Metadata consistency gate:
   - Validate variable semantics, units, member conventions, lead-time definitions, and calendars.
   - Any unresolved mismatch blocks pairing.
8. Decision logging gate:
   - Every approved pair must include reviewer, decision date, evidence URLs, and next review date.

## 6) Anchor Sources to Start Classification

### 6.1 NWS/NWM anchor links

- `https://planetarycomputer.microsoft.com/dataset/storage/noaa-nwm`
- `https://github.com/TomAugspurger/noaa-nwm`
- `https://www.weather.gov/media/wrn/calendar/NWS-NODD-Microsoft-NWM-Office-Hours-Notes.pdf`
- `https://water.noaa.gov/about/nwm`
- `https://registry.opendata.aws/nwm-archive/`
- `https://github.com/NOAA-Big-Data-Program/nodd-data-docs/blob/main/nwm/README.md`
- `https://aws.amazon.com/marketplace/pp/prodview-g6lcchc7brshw`
- `https://www.weather.gov/media/owp/operations/nwps_user_guide.pdf`

### 6.2 GloFAS anchor links

- `https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical?tab=overview`
- `https://confluence.ecmwf.int/plugins/servlet/mobile?contentId=265028796#content/view/265028624`
- `https://ewds.climate.copernicus.eu/datasets/cems-glofas-forecast?tab=overview`
- `https://global-flood.emergency.copernicus.eu/general-information/glofas-methods/`
