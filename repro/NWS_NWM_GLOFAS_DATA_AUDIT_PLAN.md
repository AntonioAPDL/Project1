# NWS/NWM and GloFAS Data Audit Plan (Metadata-Only, Version Compatibility)

Date created: 2026-02-14  
Last updated: 2026-02-16  
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

## 1.1) Current Status Snapshot (2026-02-16)

1. NWS/NWM and GloFAS version timelines are populated from reviewed sources.
2. Version-linked historical/retrospective/forecast/reforecast metadata is populated where explicitly available.
3. Remaining unknowns are explicitly tracked (not inferred), especially:
   - NWM forecast-side reforecast/hindcast product metadata.
   - Per-version NWM retrospective publication dates.
   - Numeric expansion of GloFAS forecast `operational` alias in retrieve metadata.

## 2) One-Page Outline for the Final Shareable Documentation

1. Scope and purpose.
2. NWM version timeline and product mapping.
3. GloFAS version timeline and product mapping.
4. Data-location and access registry.
5. Compatibility review notes (version pairing rationale and unresolved transitions).
6. Open issues, unknowns, and next verification targets.
7. Source list and last-verified dates.

## 2.1) Evidence Hierarchy Used in This Document

When sources disagree, this document uses the following precedence:

1. Official versioning/release notices and official API/catalog metadata endpoints.
2. Official dataset overview pages and official release pages.
3. Supporting sources (marketplace summaries, community repos, local archives).

Applied coherence rules:

1. Chronology anchors use official release/versioning notices first.
2. Product-behavior details use per-product dataset/release pages.
3. Local/project evidence is clearly labeled as supplemental, not authoritative chronology.

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

### 3.2.1 NWM Retrospective Technical Notes (Registry + Marketplace Text)

| topic | verified note | evidence |
|---|---|---|
| Data assimilation in retrospective runs | No streamflow or other DA is performed in retrospective simulations. | `NWM-URL-05`, `NWM-URL-07` |
| Domain coverage by version | CONUS is provided by v1.2/v2.0/v2.1/v3.0; oCONUS retrospective coverage (Alaska, Hawaii, Puerto Rico/USVI) is only in v3.0. | `NWM-URL-07`, `NWM-URL-05` |
| CONUS forcing by version | v3.0 and v2.1 use AORC (v2.1 uses AORC v1.0 for 1979-2006 and v1.1 for 2007-2020; v3.0 uses AORC v1.1 for full period). v2.0 and v1.2 use NLDAS. | `NWM-URL-07`, `NWM-URL-05` |
| v3.0 forcing metadata caveat | Listing text warns some v3.0 forcing metadata tags may read “v2.1” even though files are v3.0 forcing files. | `NWM-URL-07` |
| Format availability by version | Retrospective data are available as NetCDF and/or Zarr with version-dependent field coverage. | `NWM-URL-05`, `NWM-URL-07` |

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

### 3.3.1 NWM Release-Notes Cross-Check (Ensemble-Member Structure)

Source:

- `NWM-URL-20`: `https://www.nco.ncep.noaa.gov/pmb/codes//nwprod/nwm.v3.0.17/doc/NationalWaterModelReleaseNotes.pdf`

Release-note findings relevant to member-structure and timeline interpretation:

| version | release-notes statement (condensed) | expected forecast-member implication | local archive check (`NWM-LOCAL-01`) |
|---|---|---|---|
| 2.0.0 | Added Medium Range ensemble forecast configuration: 7 members (4 cycles/day). | Transition from pre-2.0 single-member medium-range structure to 7-member structure. | Matches observed `1 -> 7` structural transition on `2019-06-19`. |
| 2.1.0 | Medium-range job remains `Medium Range 1-7`; cycle policy still treats medium-range as 7-member ensemble execution. | No structural member-count change expected at v2.1 boundary. | Matches observed no structural change at `2021-04-20`. |
| 3.0.0 | Explicit removal of NWM medium-range member 7; medium-range model listed as `1-6`. | Structural reduction from 7 to 6 members at v3.0 boundary. | Matches observed `7 -> 6` structural transition on `2023-09-20`. |

Interpretation:

1. The release-note evidence indicates that observed member-count transitions are consistent with documented version changes (especially 2.0 and 3.0).
2. The release notes provide change semantics (what changed), while SCN/TIN notices remain the primary source for operational effective dates used in Section 3.1.
3. This addresses prior uncertainty about v2.1 member-count behavior: no structural count change is expected at that boundary.

### 3.4 NWS/NWM Reforecast or Hindcast Availability Check

| check_item | status | evidence | note |
|---|---|---|---|
| Forecast-side reforecast product by NWM version | not found in reviewed authoritative NWS/NODD sources | `NWM-URL-04`, `NWM-URL-05`, `NWM-URL-11`, `NWM-URL-12`, `NWM-URL-13`, `NWM-URL-14`, `NWM-URL-15`, `NWM-URL-17`, `NWM-URL-19` | No explicit versioned forecast reforecast/hindcast catalog entry found in reviewed NWS/NODD URLs. |
| Retrospective runs (historical simulations) | found | `NWM-URL-05` | Retrospective datasets are available and versioned, but these are not labeled as forecast reforecast products in the reviewed sources. |

### 3.4.1 Project-Local Raw NWM Ensemble Archive Evidence (`results.pkl`)

Evidence role:

1. This subsection is supplemental local evidence (`NWM-LOCAL-01`) for member-structure behavior.
2. It is used to validate observed transitions against official release chronology, not to replace official release metadata.

Evidence file (project-local):

- `/data/muscat_data/jaguir26/project1_ucsc_phd/results.pkl` (`NWM-LOCAL-01`)
- Object type: Python dictionary (`1,832,084` entries)
- Key pattern parsed for this audit:
  - `issue_date`: `nwm.YYYYMMDD/...`
  - `ensemble_member`: `medium_range_memX` (default member `1` when `memX` token is absent)
  - `lead_time_h`: `.fNNN.`
  - `issue_hour`: `.t00z` or `.t12z`
- Value: single nonnegative point-location forecast value (float) in the audited file

Coverage summary from parsed keys:

| field | value |
|---|---|
| Issue-date range | `2018-09-17` to `2024-02-20` |
| Issue dates with any data | `1,980` |
| Missing issue dates in contiguous span | `2019-03-10`, `2020-03-12`, `2020-11-14` |
| Target-date range (`issue_date + lead_time_h`) | `2018-09-17` to `2024-03-01` |
| Missing target dates in contiguous span | none |
| Issue hours observed | `00`, `12` |

Observed member-set timeline by issue date:

| date window | observed member set | member count | classification |
|---|---|---|---|
| `2018-09-17` to `2019-06-18` | `{1}` | `1` | persistent |
| `2019-06-19` to `2023-09-19` | `{1,2,3,4,5,6,7}` | `7` | persistent (with one-day anomalies below) |
| `2023-09-20` to `2024-02-20` | `{1,2,3,4,5,6}` | `6` | persistent |

One-day member-set anomalies in the 7-member era:

| date | observed member set |
|---|---|
| `2020-03-16` | `{2,3,4,5,7}` |
| `2020-07-29` | `{1,2,3,4,5,7}` |
| `2022-07-14` | `{1,2,3,4,6,7}` |

Per-member first/last issue-date coverage:

| member | first issue date | last issue date | notes |
|---|---|---|---|
| 1 | `2018-09-17` | `2024-02-20` | missing on `2020-03-16` |
| 2 | `2019-06-19` | `2024-02-20` |  |
| 3 | `2019-06-19` | `2024-02-20` |  |
| 4 | `2019-06-19` | `2024-02-20` |  |
| 5 | `2019-06-19` | `2024-02-20` | missing on `2022-07-14` |
| 6 | `2019-06-19` | `2024-02-20` | missing on `2020-03-16`, `2020-07-29` |
| 7 | `2019-06-19` | `2023-09-19` | absent from `2023-09-20` onward |

Version alignment check (official timeline vs observed local member sets):

| NWM version window (official) | official operational start | first issue date present in local archive for that version window | observed medium-range member behavior in local archive | alignment note |
|---|---|---|---|---|
| 1.2 (`2018-03-06` to `2019-06-18`) | `2018-03-06` | `2018-09-17` | single-member (`{1}`) through `2019-06-18` | local archive starts late in v1.2 window (195-day lag from official start) |
| 2.0 (`2019-06-19` to `2021-04-19`) | `2019-06-19` | `2019-06-19` | 7-member (`{1..7}`) from start, aside from one-day outages | transition aligns exactly at official v2.0 start |
| 2.1 (`2021-04-20` to `2023-09-19`) | `2021-04-20` | `2021-04-20` | remains 7-member (`{1..7}`) | no member-count structural change at 2.1 boundary in local archive |
| 3.0 (`2023-09-20` onward) | `2023-09-20` | `2023-09-20` | persistent 6-member (`{1..6}`), member 7 ends on `2023-09-19` | transition aligns exactly at official v3.0 start |

Retrospective coverage-end vs forecast operational-start gap check:

| NWM version | retrospective coverage end (Section 3.2) | forecast operational start (Section 3.1) | gap indication |
|---|---|---|---|
| 1.2 | `2017-12` | `2018-03-06` | month-level gap (~3 months) |
| 2.0 | `2018-12` | `2019-06-19` | month-level gap (~6 months) |
| 2.1 | `2020-12` | `2021-04-20` | month-level gap (~4 months) |
| 3.0 | `2023-01` | `2023-09-20` | month-level gap (~8 months) |

Interpretation and limits:

1. This local archive evidence supports the hypothesis that operational forecast member structure changes are strongly version-linked for v2.0 and v3.0 transitions.
2. This local archive evidence also supports the hypothesis that retrospective coverage windows do not necessarily end exactly at operational forecast start dates for the same version label.
3. Exact retrospective **release** dates remain unresolved in authoritative public metadata (`not explicitly listed` in reviewed sources), so release-lag quantification is still a tracked open item.
4. One-day member-set drops are treated as outage/partial-ingestion anomalies unless corroborated by official version notices.

### 3.4.2 AWS Marketplace Metadata Check for Retrospective Release Timing

Source:

- `NWM-URL-07`: `https://aws.amazon.com/marketplace/pp/prodview-g6lcchc7brshw`

Extracted catalog metadata (from listing JSON payload):

| field | value | interpretation |
|---|---|---|
| Data Exchange fulfillment option name | `DataSet-nwm-archive` | Catalog object for retrospective data access in Marketplace. |
| `creationDate` | `2022-06-17T19:20:55.006Z` | Catalog/fulfillment-option creation timestamp, not a per-version retrospective publication date. |
| Artifact buckets listed | `noaa-nwm-retrospective-3-0-pds`, `noaa-nwm-retrospective-2-1-pds`, `noaa-nwm-retrospective-2-1-zarr-pds`, `noaa-nwm-retro-v2-0-pds`, `noaa-nwm-retro-v2-zarr-pds`, `nwm-archive` | Confirms multi-version artifact presence under one listing. |

Interpretation constraint:

1. The Marketplace listing provides one catalog-level creation timestamp and versioned artifact references.
2. It does not expose explicit per-version retrospective release timestamps for v1.2/v2.0/v2.1/v3.0 in the reviewed metadata payload.
3. Therefore, retrospective release-to-forecast-transition lag cannot be fully resolved from Marketplace metadata alone.

Retrospective version coverage windows (from listing text) vs forecast member transitions:

| version | retrospective coverage end (listing text) | forecast-member structural transition linked to operational version boundary | operational boundary date | coverage-end to boundary lag (approx) |
|---|---|---|---|---|
| 2.0 | `2018-12` | `1 -> 7` members | `2019-06-19` | ~6 months |
| 2.1 | `2020-12` | no structural member-count change observed | `2021-04-20` | ~4 months |
| 3.0 | `2023-01` | `7 -> 6` members | `2023-09-20` | ~8 months |

Interpretation:

1. Available evidence indicates that retrospective coverage windows and forecast-member structural transitions are not synchronized on the same dates.
2. Forecast-member transitions align with operational version boundaries (especially v2.0 and v3.0), while retrospective coverage windows end earlier.
3. Exact per-version retrospective publication/release timestamps remain an open evidence gap.

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

### 3.5.1 GloFAS Versioning-System Cross-Check (Internal Release, Test Window, Lifecycle Notes)

| glofas_version | glofas_internal_number | released_in_test | released_in_production | lifecycle_or_footnote_note | evidence_source_id |
|---|---|---|---|---|---|
| 4.4 | 005 | n/a | 2025-09-10 | Listed as latest operational release. | `GLOFAS-URL-10` |
| 4.3 | 005 | n/a | 2025-06-04 | Same internal number family as v4.0-v4.4. | `GLOFAS-URL-10`, `GLOFAS-URL-13` |
| 4.2 | 005 | n/a | 2024-11-12 | Same internal number family as v4.0-v4.4. | `GLOFAS-URL-10`, `GLOFAS-URL-14` |
| 4.1 | 005 | n/a | 2024-02-28 | Same internal number family as v4.0-v4.4. | `GLOFAS-URL-10`, `GLOFAS-URL-15` |
| 4.0 | 005 | 2023-07-05 | 2023-07-26 | Major v4 production cutover. | `GLOFAS-URL-10`, `GLOFAS-URL-12` |
| 3.5 | 004 | 2023-06-05 | 2023-06-28 | Late v3 production update before v4.0 cutover. | `GLOFAS-URL-10`, `GLOFAS-URL-16` |
| 3.4 | 004 | 2022-11-11 | 2022-12-14 | v3 generation release. | `GLOFAS-URL-10` |
| 3.3 | 004 | 2022-10-12 | 2022-10-19 | v3 generation release. | `GLOFAS-URL-10` |
| 3.2 | 004 | 2021-10-21 | 2021-10-27 | v3 generation release. | `GLOFAS-URL-10` |
| 3.1 | 004 | 2021-02-14 | 2021-05-26 | v3 generation release. | `GLOFAS-URL-10`, `GLOFAS-URL-17` |
| 2.2 | 003** | 2020-11-01 | 2020-12-09 (12UTC) | Footnote states no modelling change vs v2.1; internal number remains 003. | `GLOFAS-URL-10`, `GLOFAS-URL-18` |
| 2.1 | 003*** | 2019-10-08 | 2019-11-05 (12UTC) | Footnote states v2.1 decommissioned from mid-September 2022; previously generated data remain available in CDS. | `GLOFAS-URL-10`, `GLOFAS-URL-19` |
| 2.0 | 002 | 2018-10-14 | 2018-11-14 (12UTC) | v2.0 major release line. | `GLOFAS-URL-10`, `GLOFAS-URL-20` |
| 1.0 | 001 | 2018-03-23 | 2018-04-23 (12UTC) | First version listed in current official versioning table. | `GLOFAS-URL-10`, `GLOFAS-URL-21` |

Interpretation:

1. `GLOFAS-URL-10` is treated as the authoritative chronology for production timeline and internal-number transitions.
2. Version pages are used for product-impact context (historical/reanalysis/reforecast changes), not as primary chronology anchors when date fields differ.
3. The v2.1/v2.2 footnotes are operationally relevant for lifecycle interpretation (decommission and data-equivalence note).

### 3.6 GloFAS Historical, Forecast, and Reforecast Metadata

| product_type | current_system_version_note | product_release_or_publication_date | coverage_start | coverage_end | format | key_access_locations | notes |
|---|---|---|---|---|---|---|---|
| historical | operational version listed as v4.0 (released 2023-07-26) | publication date: 2019-11-05 | 1979-01-01 | near real time | GRIB2, NetCDF-4 | `GLOFAS-URL-01` | Daily data; global except Antarctica; legacy versions also available. |
| forecast | current version listed as v4.0 (released 2023-07-26) | publication date: 2020-05-19 | 2019-11-05 (river discharge) | near real time | GRIB2, NetCDF-4 | `GLOFAS-URL-03` | Soil wetness/snow variables indicate operational coverage from 2024-02-28 onward. |
| reforecast | current version listed as v4.0 (released 2023-07-26) | publication date: 2020-12-09 | first reference date: 2023-03-27 | near real time generation (historical years 2003-2022 per reference date) | GRIB2 (dataset page), GRIB2/NetCDF options in retrieve API metadata | `GLOFAS-URL-05`, `GLOFAS-URL-23` | 11-member ECMWF-ENS reforecasts, Monday/Thursday reference dates, 46-day lead time, weekly update. |

Coverage-note:

1. Table 3.6 uses product-page framing text (`near real time`, `first reference date`, etc.).
2. Exact collection-level start/end timestamps and current update state are tracked in Section 3.7.1.

### 3.6.1 GloFAS Version-Linked Product Notes (Reanalysis, Forecast, Reforecast)

| glofas_version | product dimension | extracted note | evidence_source_id |
|---|---|---|---|
| 4.0 | historical/reanalysis | Major version change is tied to an update of historical hydrological reanalysis, with large modelling-result impacts. | `GLOFAS-URL-12` |
| 4.2 | forecast-skill/reforecast linkage | Medium-range forecast skill layer was recalculated with expanded full reforecast coverage (not only initial months used in early v4.0 release period). | `GLOFAS-URL-14` |
| 3.5 | reforecast policy | No new 48r1-specific hydrological reforecast dataset in v3.5; reforecast handling is explicitly documented in release notes. | `GLOFAS-URL-16` |
| 2.1 | reanalysis and reforecast baseline | Upgrade includes ERA5-based hydrological reanalysis and new river-discharge reforecast sets (30-day and seasonal). | `GLOFAS-URL-19` |
| 1.0 | reforecast baseline design | Reforecasts documented as twice-weekly, 11-member, multi-year historical ensemble runs in v1.0-era release material. | `GLOFAS-URL-21` |

Operational consistency note:

1. EWDS dataset overview pages currently expose v4.0 labels for historical/forecast/reforecast metadata tables, while the versioning-system chronology reports newer operational releases up to v4.4.
2. This document keeps both views explicit: endpoint/product labels from EWDS pages and operational chronology from the official versioning table.

### 3.7 GloFAS EWDS API Version Options by Product (Retrieve Metadata)

| product_id | system_version options in retrieve API | product_type options | data_format options | key timing/options notes | evidence_source_id |
|---|---|---|---|---|---|
| `cems-glofas-historical` | `version_2_1`, `version_3_1`, `version_4_0` | `consolidated`, `intermediate` | `grib2`, `netcdf` | No leadtime field (historical product). | `GLOFAS-URL-22` |
| `cems-glofas-forecast` | `operational`, `version_2_1`, `version_3_1` | `control_forecast`, `ensemble_perturbed_forecasts` | `grib2`, `netcdf` | Leadtime enum spans 24 to 720h (24h step). | `GLOFAS-URL-09` |
| `cems-glofas-reforecast` | `version_2_2`, `version_3_1`, `version_4_0` | `control_reforecast`, `ensemble_perturbed_reforecast` | `grib2`, `netcdf` | Leadtime enum spans 24 to 1104h (24h step). | `GLOFAS-URL-23` |

Format-note:

1. For reforecast, the dataset overview page emphasizes GRIB2, while retrieve-process metadata currently lists both `grib2` and `netcdf` options.
2. This audit keeps both fields explicit and does not infer final per-request availability beyond endpoint metadata.

### 3.7.1 GloFAS Collection-Level Coverage and Active Notices (EWDS Catalogue API)

| collection_id | published | updated | temporal_extent_start | temporal_extent_end | active_messages_snapshot | evidence_source_id |
|---|---|---|---|---|---|---|
| `cems-glofas-historical` | `2019-11-05T00:00:00Z` | `2026-02-15T00:00:00Z` | `1979-01-01T00:00:00Z` | `2026-02-13T00:00:00Z` | time-critical advisory + known-issues note | `GLOFAS-URL-24`, `GLOFAS-URL-27` |
| `cems-glofas-forecast` | `2020-05-19T00:00:00Z` | `2026-02-15T00:00:00Z` | `2019-11-05T00:00:00Z` | `2026-02-15T00:00:00Z` | time-critical advisory + known-issues note | `GLOFAS-URL-25`, `GLOFAS-URL-28` |
| `cems-glofas-reforecast` | `2020-12-09T00:00:00Z` | `2025-04-02T00:00:00Z` | `1999-01-03T00:00:00Z` | `2023-11-25T00:00:00Z` | includes `2024-11-11` temporary freeze notice for medium-range reforecasts from EWDS (support ticket path provided) | `GLOFAS-URL-26`, `GLOFAS-URL-29` |

Coverage-interpretation constraint:

1. These are collection-level temporal extents and message feeds, not explicit per-`system_version` coverage windows.
2. Retrieve schemas publish version enums (`2.1`, `3.1`, `4.0` family options by product) but do not publish version-specific date windows in the same endpoint metadata.
3. Therefore, per-version historical/reforecast date coverage (for `version_2_1` vs `version_3_1` vs `version_4_0`) remains unresolved from metadata alone and must be treated as an explicit follow-up item.

### 3.7.2 GloFAS Selector Semantics (for `river_discharge_in_the_last_24_hours`)

| selector | where used | meaning in this audit | evidence |
|---|---|---|---|
| `system_version` | historical/forecast/reforecast retrieve APIs | Version label for the GloFAS system generation exposed by the endpoint (exact option sets differ by product). | `GLOFAS-URL-22`, `GLOFAS-URL-09`, `GLOFAS-URL-23` |
| `hydrological_model` (`htessel_lisflood`, `lisflood`) | historical/forecast/reforecast retrieve APIs | Model-chain selector. `lisflood` aligns with full LISFLOOD-era configuration; `htessel_lisflood` corresponds to the coupled HTESSEL+LISFLOOD lineage referenced in legacy-to-v3.1 transition notes. | `GLOFAS-URL-17`, `GLOFAS-URL-04`, `GLOFAS-URL-22`, `GLOFAS-URL-09`, `GLOFAS-URL-23` |
| `product_type` (historical: `consolidated` / `intermediate`) | historical dataset/API | `intermediate` uses ERA5T near-real-time forcing (daily updates); `consolidated` uses consolidated ERA5 forcing (monthly updates). | `GLOFAS-URL-01`, `GLOFAS-URL-22` |
| `product_type` (forecast: `control_forecast` / `ensemble_perturbed_forecasts`) | forecast dataset/API | Control member vs perturbed ensemble members for operational forecast runs. | `GLOFAS-URL-03`, `GLOFAS-URL-09` |
| `product_type` (reforecast: `control_reforecast` / `ensemble_perturbed_reforecast`) | reforecast dataset/API | Control member vs perturbed ensemble members for hindcast/reforecast runs. | `GLOFAS-URL-05`, `GLOFAS-URL-23` |
| `variable=river_discharge_in_the_last_24_hours` | historical/forecast/reforecast APIs | Daily river-discharge variable available across all three product families and used as the primary bias-transfer target in this project. | `GLOFAS-URL-22`, `GLOFAS-URL-09`, `GLOFAS-URL-23` |

Project-use interpretation:

1. `cems-glofas-historical` is the historical/reanalysis side used to learn retrospective bias structure.
2. `cems-glofas-forecast` is the real-time forecast side to be corrected.
3. `cems-glofas-reforecast` is the hindcast/reforecast side for skill calibration, post-processing, and compatibility checks when available.

### 3.7.3 Supporting Legacy Reanalysis Anchors (JRC Data Catalogue)

| source_product | version label in source | temporal coverage in source metadata | key notes | evidence_source_id |
|---|---|---|---|---|
| GloFAS streamflow reanalysis | `v3.0` | `1980-01-01` to `2018-12-31` | Legacy LISFLOOD/ERA5 reanalysis archive in JRC catalogue; large bulk archive link available. | `GLOFAS-URL-30` |
| GloFAS hydrological reanalysis | `v4.0` | `1980-01-01` to `2022-07-31` | JRC dataset description explicitly frames v4.0 as an update compared to v3.1; access points are bulk archive style. | `GLOFAS-URL-31` |

Interpretation constraints:

1. These JRC entries are used as legacy coverage anchors and are treated as supporting sources in this audit.
2. EWDS retrieve/catalogue endpoints remain the primary authoritative source for current operational access and version selectors.
3. Label mapping is not yet fully resolved between JRC archive labels (`v3.0`, `v4.0`) and EWDS historical retrieve options (`version_2_1`, `version_3_1`, `version_4_0`).

### 3.7.4 GloFAS Coverage-Window Investigation Placeholders (Metadata-Only)

The following items remain intentionally open and should be resolved without bulk downloads:

- [ ] Derive `historical` per-`system_version` date coverage windows (`2.1`, `3.1`, `4.0`) using metadata-only API validation/probing.
- [ ] Derive `reforecast` per-`system_version` date coverage windows (`2.2`, `3.1`, `4.0`) using metadata-only API validation/probing.
- [ ] Confirm whether a dedicated public landing page exists for a standalone `v3.1` reanalysis archive and record it if found.
- [ ] Reconcile JRC legacy archive labels with EWDS `system_version` lineage in one explicit mapping table.
- [ ] Re-check reforecast freeze status before each production cycle and record message-feed timestamp.

## 4) Source Checklist (Metadata Documentation)

Track source review progress here. Use URL IDs from Section 7.

Status values:

1. `done`: metadata field extraction finished for current scope.
2. `in_progress`: source reviewed partially; at least one targeted field still unresolved.

| source_id | center | priority | fields_to_capture | status | last_checked_utc | notes |
|---|---|---|---|---|---|---|
| `NWM-URL-04` | NWM | high | operational forecast configuration details | `done` | `2026-02-15` | NWM configuration/cycle details extracted. |
| `NWM-URL-05` | NWM | high | retrospective versions, coverage, forcing notes | `done` | `2026-02-15` | Versioned retrospective windows and bucket map extracted. |
| `NWM-URL-15` | NWM | high | v3.0 operational effective date | `done` | `2026-02-15` | SCN23-76 confirms v3.0 effective date. |
| `NWM-URL-11/12/13/14/16` | NWM | high | historical operational version release dates | `done` | `2026-02-15` | TIN/SCNs used to reconstruct timeline 2016-2023. |
| `NWM-URL-17` | NWM | high | short-range archive scope and access endpoints | `done` | `2026-02-15` | Four-week rollover and bucket metadata extracted. |
| `NWM-URL-07` | NWM | high | Marketplace retrospective listing metadata (coverage text + catalog timing fields + artifact map) | `done` | `2026-02-15` | Verified listing text by version, oCONUS/forcing/format notes, and catalog `creationDate`; per-version release dates still not explicitly exposed. |
| `NWM-URL-20` | NWM | high | NWM release-notes change log signals for medium-range member structure by version | `done` | `2026-02-15` | Used to cross-check 2.0 (7-member introduction), 2.1 (1-7 continuity), and 3.0 (member-7 removal). |
| `NWM-URL-01` | NWM | medium | Planetary Computer metadata detail | `in_progress` | `2026-02-15` | Page is JS-heavy in this audit context; use supporting docs/notes where needed. |
| `NWM-LOCAL-01` | NWM | high | project-local point-extracted ensemble timeline (`results.pkl`) for member-set transition evidence | `done` | `2026-02-15` | Used for issue-date/member-set transition evidence and version-alignment cross-check in Section 3.4.1. |
| `GLOFAS-URL-01` | GloFAS | high | historical coverage, formats, release metadata | `done` | `2026-02-15` | Historical metadata extracted (coverage, format, DOI, dates). |
| `GLOFAS-URL-03` | GloFAS | high | forecast coverage, formats, release metadata | `done` | `2026-02-15` | Forecast metadata extracted (coverage, format, DOI, dates). |
| `GLOFAS-URL-05` | GloFAS | high | reforecast cadence, lead time, format, release metadata | `done` | `2026-02-15` | Reforecast metadata extracted (twice-weekly, 46-day, 11-member). |
| `GLOFAS-URL-10` | GloFAS | high | official version chronology and release dates | `done` | `2026-02-15` | Versioning system table extracted through v4.4. |
| `GLOFAS-URL-11` | GloFAS | high | latest operational release page content | `done` | `2026-02-15` | Cross-checks current operational release against versioning table. |
| `GLOFAS-URL-12` | GloFAS | medium | v4.0 release implementation details | `done` | `2026-02-15` | Used as supporting release-details reference for v4.0 era datasets. |
| `GLOFAS-URL-13/14/15/16/17/18/19/20/21` | GloFAS | high | per-version release details for reanalysis/forecast/reforecast behavior and lifecycle notes | `done` | `2026-02-15` | Used to extract product-impact notes across v1.0, v2.x, v3.x, and v4.x pages while chronology remains anchored to `GLOFAS-URL-10`. |
| `GLOFAS-URL-04` | GloFAS | medium | method chain notes (HTESSEL/LISFLOOD/IFS) | `done` | `2026-02-15` | Modelling-chain inputs and routing notes extracted. |
| `GLOFAS-URL-06/07/08/09/22/23` | GloFAS | medium | API auth and metadata endpoint behavior | `done` | `2026-02-15` | API endpoint and auth setup information captured, including per-product retrieve-process option metadata. |
| `GLOFAS-URL-24/25/26` | GloFAS | high | collection-level `published`/`updated` fields and temporal extent intervals | `done` | `2026-02-15` | Catalogue collection metadata used for explicit dataset-level start/end coverage timestamps. |
| `GLOFAS-URL-27/28/29` | GloFAS | high | dataset message feeds (warnings, advisories, freeze notices) | `done` | `2026-02-15` | Includes reforecast temporary-freeze message dated `2024-11-11` and shared known-issues/time-critical advisory notices. |
| `GLOFAS-URL-30/31` | GloFAS | medium | supporting legacy reanalysis coverage anchors from JRC catalogue | `done` | `2026-02-16` | Added to document `v3.0` and `v4.0` historical-reanalysis temporal coverage anchors without bulk download. |
| `GLOFAS-URL-32` | GloFAS | low | CDS -> EWDS migration context (supporting forum note) | `done` | `2026-02-16` | Supporting migration context only; not used as authoritative version-coverage evidence. |

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
  Completion note: retrospective version-to-coverage mapping completed from `NWM-URL-05` and `NWM-URL-07`; explicit gap remains: reviewed metadata exposes coverage windows and catalog-level creation timing, but not explicit per-version retrospective release dates.
- [x] `NWM-03`: Link each version to forecast products and release/coverage dates.
  Completion note: version-to-forecast operational windows and configuration changes documented from SCNs/TIN (`NWM-URL-11` through `NWM-URL-16`) plus current NWM operations page (`NWM-URL-04`) and NODD short-range archive metadata (`NWM-URL-17`).
- [x] `NWM-04`: Confirm whether reforecast/hindcast products exist per version.
  Completion note: no authoritative NWS/NODD source in the reviewed URL set explicitly documents a versioned forecast reforecast/hindcast product for NWM; status recorded as `not found in reviewed sources` (see Section 3.4).
- [x] `NWM-05`: Record storage/access locations per product (portal, bucket/container, API/catalog endpoint).
  Completion note: completed using `NWM-URL-04`, `NWM-URL-05`, `NWM-URL-17`, `NWM-URL-09`, `NWM-URL-10`, `NWM-URL-03`, and supporting cloud-notes context from `NWM-URL-01`/`NWM-URL-02`.
- [x] `NWM-06`: Mark unresolved transitions or version-link uncertainties for follow-up.
  Completion note: unresolved items explicitly recorded: (1) v3.1 is proposal-only pending SCN implementation notice, (2) retrospective per-version release dates are not explicitly published in reviewed sources, (3) forecast-side reforecast/hindcast product remains undocumented in reviewed authoritative URLs. Prior v2.1 member-count uncertainty is now resolved by release-notes cross-check (`NWM-URL-20`).

### 5.3 GloFAS tasks

- [x] `GLOFAS-01`: Build complete GloFAS version chronology (including legacy versions).
  Completion note: chronology completed from official versioning system (`GLOFAS-URL-10`), including production release dates from v1.0 through v4.4 plus internal release-number/test-window/lifecycle-footnote cross-check.
- [x] `GLOFAS-02`: Link each version to historical/retrospective products and release/coverage dates.
  Completion note: historical dataset metadata captured (`GLOFAS-URL-01`) and API system-version options verified (`version_2_1`, `version_3_1`, `version_4_0`) via historical retrieve endpoint (`GLOFAS-URL-22`). Explicit gap: authoritative per-version coverage date ranges for all legacy historical versions are not published as a single table in reviewed sources.
- [x] `GLOFAS-03`: Link each version to forecast products and release/coverage dates.
  Completion note: forecast dataset metadata captured (`GLOFAS-URL-03`) and API system-version options verified (`operational`, `version_2_1`, `version_3_1`) via retrieve endpoint (`GLOFAS-URL-09`). Explicit gap: retrieve metadata does not explicitly map `operational` to a named numeric version in the endpoint itself.
- [x] `GLOFAS-04`: Link each version to reforecast products and release/coverage dates (if available).
  Completion note: reforecast dataset metadata captured (`GLOFAS-URL-05`) and API system-version options verified (`version_2_2`, `version_3_1`, `version_4_0`) via reforecast retrieve endpoint (`GLOFAS-URL-23`), including 46-day lead-time design and twice-weekly cadence.
- [x] `GLOFAS-05`: Record storage/access locations per product (EWDS catalogue/retrieve, IDs, endpoint notes).
  Completion note: recorded using dataset pages (`GLOFAS-URL-01`, `GLOFAS-URL-03`, `GLOFAS-URL-05`), catalogue collection endpoints (`GLOFAS-URL-07`, `GLOFAS-URL-08`, `GLOFAS-URL-24`, `GLOFAS-URL-25`, `GLOFAS-URL-26`), retrieve process endpoints (`GLOFAS-URL-09`, `GLOFAS-URL-22`, `GLOFAS-URL-23`), and collection message feeds (`GLOFAS-URL-27`, `GLOFAS-URL-28`, `GLOFAS-URL-29`).
- [x] `GLOFAS-06`: Mark unresolved transitions or version-link uncertainties for follow-up.
  Completion note: unresolved items explicitly logged: (1) versioning page indicates operational v4.4 while EWDS dataset tables still label current version as v4.0 in reviewed pages, (2) no single authoritative table found that maps each operational version to exact historical/forecast/reforecast coverage windows for every legacy version, (3) forecast retrieve endpoint uses `operational` alias without explicit numeric expansion in endpoint metadata, (4) some per-version page date fields differ from versioning-table chronology and are treated as secondary chronology signals.

Placeholder follow-up tasks (open):

- [ ] `GLOFAS-F01`: Extract per-`system_version` historical coverage windows (`2.1`, `3.1`, `4.0`) via metadata-only endpoint probing (no bulk payload transfer).
- [ ] `GLOFAS-F02`: Extract per-`system_version` reforecast coverage windows (`2.2`, `3.1`, `4.0`) via metadata-only endpoint probing (no bulk payload transfer).
- [ ] `GLOFAS-F03`: Build explicit lineage mapping table between JRC reanalysis labels (`v3.0`, `v4.0`) and EWDS historical selector labels (`version_2_1`, `version_3_1`, `version_4_0`).
- [ ] `GLOFAS-F04`: Confirm whether public standalone `v3.1` historical-reanalysis landing metadata exists and add source URL if found.
- [ ] `GLOFAS-F05`: Re-validate medium-range reforecast freeze status from EWDS message feed before each new cutoff-date experiment.

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
- `NWM-URL-20`: `https://www.nco.ncep.noaa.gov/pmb/codes/nwprod/nwm.v3.0.17/doc/NationalWaterModelReleaseNotes.pdf`

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
- `GLOFAS-URL-13`: `https://confluence.ecmwf.int/display/CEMS/GloFAS+v4.3`
- `GLOFAS-URL-14`: `https://confluence.ecmwf.int/display/CEMS/GloFAS+v4.2`
- `GLOFAS-URL-15`: `https://confluence.ecmwf.int/display/CEMS/GloFAS+v4.1`
- `GLOFAS-URL-16`: `https://confluence.ecmwf.int/display/CEMS/GloFAS+v3.5`
- `GLOFAS-URL-17`: `https://confluence.ecmwf.int/display/CEMS/GloFAS+v3.1`
- `GLOFAS-URL-18`: `https://confluence.ecmwf.int/display/CEMS/GloFAS+v2.2`
- `GLOFAS-URL-19`: `https://confluence.ecmwf.int/display/CEMS/GloFAS+v2.1`
- `GLOFAS-URL-20`: `https://confluence.ecmwf.int/display/CEMS/GloFAS+v2.0`
- `GLOFAS-URL-21`: `https://confluence.ecmwf.int/display/CEMS/GloFAS+v1.0`
- `GLOFAS-URL-22`: `https://ewds.climate.copernicus.eu/api/retrieve/v1/processes/cems-glofas-historical`
- `GLOFAS-URL-23`: `https://ewds.climate.copernicus.eu/api/retrieve/v1/processes/cems-glofas-reforecast`
- `GLOFAS-URL-24`: `https://ewds.climate.copernicus.eu/api/catalogue/v1/collections/cems-glofas-historical`
- `GLOFAS-URL-25`: `https://ewds.climate.copernicus.eu/api/catalogue/v1/collections/cems-glofas-forecast`
- `GLOFAS-URL-26`: `https://ewds.climate.copernicus.eu/api/catalogue/v1/collections/cems-glofas-reforecast`
- `GLOFAS-URL-27`: `https://ewds.climate.copernicus.eu/api/catalogue/v1/collections/cems-glofas-historical/messages`
- `GLOFAS-URL-28`: `https://ewds.climate.copernicus.eu/api/catalogue/v1/collections/cems-glofas-forecast/messages`
- `GLOFAS-URL-29`: `https://ewds.climate.copernicus.eu/api/catalogue/v1/collections/cems-glofas-reforecast/messages`
- `GLOFAS-URL-30`: `https://data.jrc.ec.europa.eu/dataset/73305ca5-c002-4124-b1d5-6451cc93af3f`
- `GLOFAS-URL-31`: `https://data.jrc.ec.europa.eu/dataset/f96b7a19-0133-4105-a879-0536991ca9c5`
- `GLOFAS-URL-32`: `https://forum.ecmwf.int/t/glofas-version-3-1-no-longer-seems-available-in-the-climate-data-store/6811`

### 7.3 Project-Local Evidence Inputs

- `NWM-LOCAL-01`: `/data/muscat_data/jaguir26/project1_ucsc_phd/results.pkl`

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

### 8.6 Terminology and Coverage Window Standard

| canonical term in this project | NWS/NWM equivalent | GloFAS equivalent | meaning |
|---|---|---|---|
| `retrospective_or_reanalysis` | retrospective | historical | Model run used to learn historical bias structure against observations. |
| `forecast_operational` | operational forecast products | operational forecast products | Real-time forecast ensemble products to be bias-corrected. |
| `reforecast_or_hindcast` | not found in reviewed authoritative NWS sources | reforecast | Forecast-like reruns on past dates for skill estimation/post-processing. |
| `operational_version_window` | SCN/TIN-based NWM version window | versioning-table GloFAS production window | Date window where a forecast version is operational. |
| `retro_coverage_window` | retrospective dataset coverage by version | historical/reforecast coverage by version | Data-date coverage of the retrospective/reanalysis side used for bias learning. |
| `collection_temporal_extent` | rarely exposed as STAC-like collection in reviewed NWM sources | EWDS catalogue extent intervals | Dataset-level start/end timestamps, not necessarily version-specific. |

Standard usage rule:

1. For cross-center comparability, always report both `operational_version_window` and `retro_coverage_window` in the same pairing note.
2. Treat `collection_temporal_extent` as dataset-level context, not proof of version-specific coverage.

## 9) Compatibility Decisions (Compact, Current Evidence)

Decision scope:

1. These decisions are metadata-based, evidence-constrained pairability tags.
2. They are not final model-performance judgments and can change with new authoritative metadata.

### 9.1 NWS/NWM pairing notes

| retrospective_version | forecast_version | decision | rationale | evidence |
|---|---|---|---|---|
| 3.0 retrospective | 3.0 forecast | `conditional` | Same version label, but retrospective publication date not explicitly listed and retrospective does not include streamflow DA. | `NWM-URL-05`, `NWM-URL-15` |
| 2.1 retrospective | 2.1 forecast | `conditional` | Same version label; retrospective and operational windows are documented but retrospective release-date metadata is incomplete. | `NWM-URL-05`, `NWM-URL-14` |
| 2.0 retrospective | 2.0 forecast | `conditional` | Same version label; similar metadata limitations on retrospective release-date publication. | `NWM-URL-05`, `NWM-URL-13` |
| 1.2 retrospective | 1.2 forecast | `conditional` | Same version label; legacy metadata is available but not complete for release-date fields. | `NWM-URL-05`, `NWM-URL-12` |
| Any cross-version retrospective->forecast pair | mixed | `blocked` | No reviewed authoritative mapping proving cross-version bias-transfer equivalence. | `NWM-URL-04`, `NWM-URL-05` |

#### 9.1.1 NWS/NWM cutoff-date operating rule (for bias fitting)

Use this direct mapping when choosing retrospective data from a forecast issue cutoff date:

| cutoff_date range (forecast issue date) | forecast version | retrospective version to use | retrospective coverage window | interpretation |
|---|---|---|---|---|
| `2021-04-20` to `2023-09-19` | `2.1` | `2.1` | `1979-02` to `2020-12` | Same-version pairing, but retrospective coverage ends before many cutoffs in this window. |
| `2023-09-20` onward | `3.0` | `3.0` | `1979-02` to `2023-01` | Same-version pairing, but retrospective coverage ends before many recent cutoffs. |

Implementation rule:

1. Choose retrospective by forecast version label first (`2.1->2.1`, `3.0->3.0`).
2. Then explicitly report the retrospective coverage-end gap to cutoff date in your run metadata.

### 9.2 GloFAS pairing notes

| historical_or_reforecast_version | forecast_version | decision | rationale | evidence |
|---|---|---|---|---|
| historical `version_3_1` | forecast `version_3_1` | `allowed` | Same explicit version identifier available in retrieve API metadata. | `GLOFAS-URL-22`, `GLOFAS-URL-09` |
| historical `version_2_1` | forecast `version_2_1` | `allowed` | Same explicit version identifier available in retrieve API metadata. | `GLOFAS-URL-22`, `GLOFAS-URL-09` |
| reforecast `version_3_1` | forecast `version_3_1` | `allowed` | Same explicit version identifier available in retrieve API metadata. | `GLOFAS-URL-23`, `GLOFAS-URL-09` |
| historical/reforecast `version_4_0` | forecast `operational` | `conditional` | Forecast endpoint uses `operational` alias; no explicit numeric expansion in endpoint metadata. | `GLOFAS-URL-22`, `GLOFAS-URL-23`, `GLOFAS-URL-09`, `GLOFAS-URL-10` |
| Any cross-version historical/reforecast->forecast pair | mixed | `blocked` | No reviewed authoritative source proves cross-version transfer compatibility as default. | `GLOFAS-URL-09`, `GLOFAS-URL-10` |

#### 9.2.1 GloFAS cutoff-date operating rule (for bias fitting)

| forecast issue cutoff window | forecast version from chronology | exact historical version available in retrieve options | exact reforecast version available in retrieve options | decision |
|---|---|---|---|---|
| `2019-11-05` to `2020-12-08` | `2.1` | yes (`version_2_1`) | no (reforecast options start at `2.2`) | `conditional` |
| `2020-12-09` to `2021-05-25` | `2.2` | no | yes (`version_2_2`) | `conditional` |
| `2021-05-26` to `2021-10-26` | `3.1` | yes (`version_3_1`) | yes (`version_3_1`) | `allowed` |
| `2021-10-27` to `2023-07-25` | `3.2` / `3.3` / `3.4` / `3.5` | no exact version option | no exact version option | `ambiguous` |
| `2023-07-26` to `2024-02-27` | `4.0` | yes (`version_4_0`) | yes (`version_4_0`) | `allowed` |
| `2024-02-28` onward | `4.1+` | no exact version option exposed | no exact version option exposed | `ambiguous` |

Example (`cutoff_date=2022-12-25`):

1. Forecast chronology maps this cutoff to `v3.4`.
2. Retrieve options for historical/reforecast do not expose `version_3_4`; only `2.1/3.1/4.0` (historical) and `2.2/3.1/4.0` (reforecast) are exposed.
3. So this cutoff remains `ambiguous` until an authoritative compatibility mapping (or additional endpoint metadata) is found.

Cautionary note:

1. Reforecast collection messages include a `2024-11-11` temporary-freeze notice (no EWDS medium-range reforecast updates from the GloFAS v4.2 release date in reviewed metadata).
2. This freeze affects data availability posture and should be checked before assuming reforecast continuity for recent periods.

## 10) One-Page Collaborator Summary (Current)

### 10.1 Current Status

1. NWM and GloFAS version timelines are populated from reviewed official sources.
2. Retrospective/historical, forecast, and reforecast metadata is mapped for both centers.
3. Key unresolved metadata gaps are explicitly documented instead of inferred.

### 10.2 Default Pairing Policy

1. Same-version pairs are preferred.
2. Cross-version pairs are blocked unless explicit authoritative equivalence is found.
3. Pairs involving unresolved version aliases or missing release metadata remain conditional.

### 10.3 Open questions

1. NWM forecast-side reforecast/hindcast product: not found in reviewed authoritative NWS/NODD URLs.
2. NWM retrospective per-version release dates: not explicitly listed in reviewed sources (Marketplace provides catalog-level `creationDate`, not per-version publication dates).
3. GloFAS `operational` alias mapping to numeric version in forecast retrieve metadata: not explicitly documented in endpoint metadata.
4. GloFAS retrieve/catalogue metadata is clear on collection-level extents, but per-`system_version` date windows are not explicitly published in the reviewed endpoint schemas.
5. Mapping between JRC legacy reanalysis labels (`v3.0`, `v4.0`) and EWDS historical selector labels (`version_2_1`, `version_3_1`, `version_4_0`) is not yet fully resolved.
6. GloFAS per-version release pages sometimes report date fields that differ from the versioning-table chronology; current policy is to anchor chronology to `GLOFAS-URL-10` and use per-version pages for product-impact details.

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
