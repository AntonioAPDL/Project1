#!/usr/bin/env python3
"""Operational NWS/NWM latest-cycle updater (point-only, latest-only retention).

This updater performs the full production loop for the San Lorenzo point:

1. Detect latest available NWM medium-range cycle.
2. Download each required NetCDF file to a temporary file only.
3. Extract a single streamflow value at the configured feature_id.
4. Delete temporary raw files immediately after extraction.
5. Build daily ensemble forecast CSV via existing forecats post-processor.
6. Generate a lightweight operational plot (obs + NWS ensembles).
7. Stage -> validate -> atomically promote as current.
8. Keep only latest successful run artifacts and latest cache alias.

No raw gridded forecast archive is retained.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import datetime as dt
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import xarray as xr


try:
    import yaml
except Exception as exc:  # pragma: no cover
    yaml = None
    YAML_IMPORT_ERROR = exc
else:
    YAML_IMPORT_ERROR = None


CFS_TO_CMS = 0.0283168466
ISSUE_DATE_RE = re.compile(r"^(?:nwm|nwm2|nwmv3|nwmv2)\.(\d{8})/")
ISSUE_HOUR_RE = re.compile(r"\.t(\d{2})z\.")
MEM_RE = re.compile(r"medium_range_mem(\d+)")
LEAD_RE = re.compile(r"\.f(\d{3})\.")


@dataclasses.dataclass(frozen=True)
class IssueCycle:
    issue_date: dt.date
    cycle_hour: int

    @property
    def cycle_tag(self) -> str:
        return f"{self.issue_date.isoformat()}_t{self.cycle_hour:02d}z"


@dataclasses.dataclass(frozen=True)
class ExtractionTask:
    key: str
    url: str
    member: int
    lead_hour: int


DEFAULT_CONFIG: Dict[str, Any] = {
    "site": {
        "usgs_site": "11160500",
        "feature_id": 17684066,
        "lat": 37.0443931,
        "lon": -122.072464,
    },
    "ingest": {
        "base_url": "https://storage.googleapis.com/national-water-model",
        "lookback_days": 4,
        "cycle_hours_desc": [18, 12, 6, 0],
        "member_max_leads": {"1": 240, "2": 204, "3": 204, "4": 204, "5": 204, "6": 204},
        "timeout_connect_sec": 20,
        "timeout_read_sec": 180,
        "retries": 3,
        "backoff_sec": 0.40,
        "workers": 4,
        "max_tasks": None,
    },
    "processing": {
        "post_days": 28,
        "weighting_scheme": "latest",
        "alpha": 1.0,
        "aggregation_scale": "log_log1p_cms",
        "parse_issue_hour": True,
        "issue_lookback_days": 2,
        "exponents": {},
    },
    "observed": {
        "pre_days": 20,
        "nwis_parameter_cd": "00060",
        "nwis_stat_cd": "00003",
    },
    "output": {
        "root_dir": "data/nws_operational_latest/site=11160500",
        "cache_alias_root": "data/forecats_cache/site=11160500/run_id=operational_nws_latest/forecast_cache/nws",
        "status_file_rel": "status/latest_run.json",
        "plot_file_rel": "plots/nws_operational_latest.png",
    },
    "runtime": {
        "skip_if_current": True,
    },
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: Path) -> Dict[str, Any]:
    if yaml is None:  # pragma: no cover
        raise RuntimeError(f"PyYAML import failed: {YAML_IMPORT_ERROR}")
    cfg_raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cfg = deep_merge(DEFAULT_CONFIG, cfg_raw)

    # Normalize member lead mapping to int->int.
    member_max = cfg["ingest"]["member_max_leads"]
    cfg["ingest"]["member_max_leads"] = {int(k): int(v) for k, v in member_max.items()}
    cfg["ingest"]["cycle_hours_desc"] = [int(x) for x in cfg["ingest"]["cycle_hours_desc"]]
    return cfg


def nwm_url(base_url: str, issue: IssueCycle, member: int, lead_hour: int) -> str:
    ymd = issue.issue_date.strftime("%Y%m%d")
    return (
        f"{base_url}/nwm.{ymd}/medium_range_mem{member}/"
        f"nwm.t{issue.cycle_hour:02d}z.medium_range.channel_rt_{member}.f{lead_hour:03d}.conus.nc"
    )


def nwm_key(issue: IssueCycle, member: int, lead_hour: int) -> str:
    ymd = issue.issue_date.strftime("%Y%m%d")
    return (
        f"nwm.{ymd}/medium_range_mem{member}/"
        f"nwm.t{issue.cycle_hour:02d}z.medium_range.channel_rt_{member}.f{lead_hour:03d}.conus.nc"
    )


def head_ok(url: str, timeout_connect: float, timeout_read: float) -> bool:
    try:
        r = requests.head(url, timeout=(timeout_connect, timeout_read), allow_redirects=True)
        return r.status_code == 200
    except Exception:
        return False


def find_latest_cycle(cfg: Dict[str, Any], now_utc: Optional[dt.datetime] = None) -> IssueCycle:
    ingest = cfg["ingest"]
    base_url = ingest["base_url"]
    lookback = int(ingest["lookback_days"])
    cycles = [int(x) for x in ingest["cycle_hours_desc"]]
    timeout_connect = float(ingest["timeout_connect_sec"])
    timeout_read = float(ingest["timeout_read_sec"])

    now = now_utc or dt.datetime.now(dt.timezone.utc)
    for dback in range(0, lookback + 1):
        issue_date = (now - dt.timedelta(days=dback)).date()
        for cyc in cycles:
            issue = IssueCycle(issue_date=issue_date, cycle_hour=cyc)
            probe_url = nwm_url(base_url, issue, member=1, lead_hour=1)
            if head_ok(probe_url, timeout_connect, timeout_read):
                return issue
    raise RuntimeError("No available NWM medium-range cycle found in lookback window.")


def parse_nwm_key(key: str) -> Optional[Dict[str, Any]]:
    m_issue = ISSUE_DATE_RE.search(key)
    m_hour = ISSUE_HOUR_RE.search(key)
    m_mem = MEM_RE.search(key)
    m_lead = LEAD_RE.search(key)
    if not (m_issue and m_hour and m_mem and m_lead):
        return None
    issue_date = dt.datetime.strptime(m_issue.group(1), "%Y%m%d").date()
    return {
        "issue_date": issue_date.isoformat(),
        "issue_hour": int(m_hour.group(1)),
        "member": int(m_mem.group(1)),
        "lead_hour": int(m_lead.group(1)),
    }


def build_tasks(cfg: Dict[str, Any], issue: IssueCycle) -> List[ExtractionTask]:
    ingest = cfg["ingest"]
    base_url = ingest["base_url"]
    member_max = dict(ingest["member_max_leads"])
    timeout_connect = float(ingest["timeout_connect_sec"])
    timeout_read = float(ingest["timeout_read_sec"])

    tasks: List[ExtractionTask] = []
    for member in sorted(member_max):
        probe = nwm_url(base_url, issue, member=member, lead_hour=1)
        if not head_ok(probe, timeout_connect, timeout_read):
            continue
        max_lead = int(member_max[member])
        for lead in range(1, max_lead + 1):
            tasks.append(
                ExtractionTask(
                    key=nwm_key(issue, member, lead),
                    url=nwm_url(base_url, issue, member, lead),
                    member=member,
                    lead_hour=lead,
                )
            )

    max_tasks = ingest.get("max_tasks")
    if max_tasks is not None:
        tasks = tasks[: int(max_tasks)]

    if not tasks:
        raise RuntimeError("No extraction tasks available for latest cycle.")
    return tasks


def _download_to_temp(url: str, timeout_connect: float, timeout_read: float) -> Tuple[str, int]:
    fd, temp_path = tempfile.mkstemp(suffix=".nc")
    os.close(fd)
    nbytes = 0
    try:
        with requests.get(url, stream=True, timeout=(timeout_connect, timeout_read)) as r:
            r.raise_for_status()
            with open(temp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=(1 << 20)):
                    if chunk:
                        f.write(chunk)
                        nbytes += len(chunk)
        return temp_path, nbytes
    except Exception:
        with contextlib.suppress(Exception):
            os.remove(temp_path)
        raise


def resolve_feature_index(cfg: Dict[str, Any], issue: IssueCycle) -> Tuple[int, float]:
    ingest = cfg["ingest"]
    feature_id = int(cfg["site"]["feature_id"])
    sample_url = nwm_url(ingest["base_url"], issue, member=1, lead_hour=1)

    p, _ = _download_to_temp(
        url=sample_url,
        timeout_connect=float(ingest["timeout_connect_sec"]),
        timeout_read=float(ingest["timeout_read_sec"]),
    )
    try:
        ds = xr.open_dataset(p)
        feature_values = np.asarray(ds["feature_id"].values)
        idx = np.where(feature_values == feature_id)[0]
        if idx.size != 1:
            raise RuntimeError(f"Configured feature_id={feature_id} not uniquely found in sample file (count={idx.size}).")
        feature_index = int(idx[0])
        smoke_value = float(np.asarray(ds["streamflow"].isel(feature_id=feature_index).values).item())
        ds.close()
        return feature_index, smoke_value
    finally:
        with contextlib.suppress(Exception):
            os.remove(p)


def _worker_extract(payload: Dict[str, Any]) -> Dict[str, Any]:
    task = payload["task"]
    feature_index = int(payload["feature_index"])
    retries = int(payload["retries"])
    backoff = float(payload["backoff_sec"])
    timeout_connect = float(payload["timeout_connect_sec"])
    timeout_read = float(payload["timeout_read_sec"])

    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        tmp_path = None
        try:
            tmp_path, nbytes = _download_to_temp(task["url"], timeout_connect, timeout_read)
            ds = xr.open_dataset(tmp_path)
            value = float(np.asarray(ds["streamflow"].isel(feature_id=feature_index).values).item())
            ds.close()
            os.remove(tmp_path)
            return {
                "key": task["key"],
                "value": value,
                "bytes": int(nbytes),
                "attempt": int(attempt),
            }
        except Exception as exc:
            last_exc = exc
            if tmp_path:
                with contextlib.suppress(Exception):
                    os.remove(tmp_path)
            time.sleep(backoff * attempt)

    raise RuntimeError(f"Extraction failed after retries for {task['url']}: {last_exc}")


def extract_cycle_values(cfg: Dict[str, Any], tasks: List[ExtractionTask], feature_index: int) -> Dict[str, Any]:
    ingest = cfg["ingest"]
    workers = max(1, int(ingest["workers"]))
    retries = int(ingest["retries"])
    timeout_connect = float(ingest["timeout_connect_sec"])
    timeout_read = float(ingest["timeout_read_sec"])
    backoff_sec = float(ingest["backoff_sec"])

    task_payloads = [
        {
            "task": dataclasses.asdict(t),
            "feature_index": feature_index,
            "retries": retries,
            "timeout_connect_sec": timeout_connect,
            "timeout_read_sec": timeout_read,
            "backoff_sec": backoff_sec,
        }
        for t in tasks
    ]

    results: Dict[str, float] = {}
    total_bytes = 0
    total_attempts = 0
    started = time.perf_counter()

    if workers == 1:
        for i, payload in enumerate(task_payloads, 1):
            rec = _worker_extract(payload)
            results[rec["key"]] = float(rec["value"])
            total_bytes += int(rec["bytes"])
            total_attempts += int(rec["attempt"])
            if i % 60 == 0 or i == len(task_payloads):
                elapsed = time.perf_counter() - started
                fps = i / elapsed if elapsed > 0 else 0.0
                print(f"[extract] {i}/{len(task_payloads)} files | elapsed={elapsed:.1f}s | fps={fps:.3f}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_worker_extract, payload) for payload in task_payloads]
            done = 0
            for fut in as_completed(futs):
                rec = fut.result()
                results[rec["key"]] = float(rec["value"])
                total_bytes += int(rec["bytes"])
                total_attempts += int(rec["attempt"])
                done += 1
                if done % 60 == 0 or done == len(task_payloads):
                    elapsed = time.perf_counter() - started
                    fps = done / elapsed if elapsed > 0 else 0.0
                    print(f"[extract] {done}/{len(task_payloads)} files | elapsed={elapsed:.1f}s | fps={fps:.3f}", flush=True)

    elapsed = time.perf_counter() - started
    return {
        "values": results,
        "download_extract_seconds": elapsed,
        "total_bytes": total_bytes,
        "avg_attempts_per_file": (total_attempts / len(task_payloads)) if task_payloads else 0.0,
    }


def write_pickle(path: Path, values: Dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        import pickle

        pickle.dump(values, f)


def build_exponent_spec(exponents: Dict[str, Any]) -> str:
    if not exponents:
        return ""
    parts = []
    for k in sorted(exponents, key=lambda x: int(x)):
        parts.append(f"{int(k)}={float(exponents[k])}")
    return ",".join(parts)


def run_postprocess(cfg: Dict[str, Any], repo_root: Path, issue: IssueCycle, pkl_path: Path, out_csv: Path) -> Tuple[float, List[str]]:
    processing = cfg["processing"]
    post_days = int(processing["post_days"])
    forecast_start = issue.issue_date + dt.timedelta(days=1)
    forecast_end = issue.issue_date + dt.timedelta(days=post_days)

    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "forecats_build_nws_weighted.py"),
        "--pkl",
        str(pkl_path),
        "--cutoff-date",
        issue.issue_date.isoformat(),
        "--forecast-start-date",
        forecast_start.isoformat(),
        "--forecast-end-date",
        forecast_end.isoformat(),
        "--weighting-scheme",
        str(processing["weighting_scheme"]),
        "--alpha",
        str(float(processing["alpha"])),
        "--aggregation-scale",
        str(processing["aggregation_scale"]),
        "--issue-lookback-days",
        str(int(processing["issue_lookback_days"])),
        "--out-csv",
        str(out_csv),
        "--overwrite",
    ]
    if bool(processing.get("parse_issue_hour", True)):
        cmd.append("--parse-issue-hour")

    if str(processing["weighting_scheme"]) == "notebook":
        exp_spec = build_exponent_spec(dict(processing.get("exponents", {})))
        if not exp_spec:
            raise RuntimeError("notebook weighting requires non-empty processing.exponents")
        cmd.extend(["--exponents", exp_spec])

    t0 = time.perf_counter()
    cp = subprocess.run(cmd, check=True, capture_output=True, text=True)
    elapsed = time.perf_counter() - t0
    tail = cp.stdout.strip().splitlines()[-5:]
    return elapsed, tail


def create_legacy_alias(nws_members_csv: Path, out_path: Path) -> None:
    df = pd.read_csv(nws_members_csv)
    if "target_date" in df.columns:
        df = df.rename(columns={"target_date": "Date"})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)


def fetch_usgs_recent(site_id: str, pre_days: int, parameter_cd: str, stat_cd: str) -> pd.DataFrame:
    period_days = max(1, int(pre_days) + 5)
    url = (
        "https://waterservices.usgs.gov/nwis/dv/?format=json"
        f"&sites={site_id}&parameterCd={parameter_cd}&statCd={stat_cd}&period=P{period_days}D"
    )
    r = requests.get(url, timeout=(20, 60))
    r.raise_for_status()
    payload = r.json()

    series = ((payload.get("value") or {}).get("timeSeries") or [])
    if not series:
        raise RuntimeError("USGS NWIS returned no timeSeries data.")

    rows: List[Tuple[dt.date, float]] = []
    values = (((series[0].get("values") or [{}])[0]).get("value") or [])
    for item in values:
        date_txt = str(item.get("dateTime", ""))
        val_txt = str(item.get("value", ""))
        try:
            d = dt.datetime.fromisoformat(date_txt.replace("Z", "+00:00")).date()
            v_cfs = float(val_txt)
        except Exception:
            continue
        rows.append((d, v_cfs * CFS_TO_CMS))

    if not rows:
        raise RuntimeError("USGS NWIS parsing produced no valid rows.")

    df = pd.DataFrame(rows, columns=["date", "discharge_cms"]).drop_duplicates(subset=["date"]).sort_values("date")
    return df


def build_plot(obs_df: pd.DataFrame, nws_members_csv: Path, issue: IssueCycle, pre_days: int, post_days: int, out_png: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"matplotlib is required for plotting: {exc}")

    fc = pd.read_csv(nws_members_csv)
    if "target_date" not in fc.columns:
        raise RuntimeError("Expected target_date column in nws_members.csv")
    fc["target_date"] = pd.to_datetime(fc["target_date"]).dt.date
    member_cols = [c for c in fc.columns if c.startswith("member_")]
    if not member_cols:
        raise RuntimeError("No member_* columns found in nws_members.csv")

    obs = obs_df.copy()
    obs["date"] = pd.to_datetime(obs["date"]).dt.date

    # Window alignment: last pre_days before issue + post_days forecast horizon.
    x_min = issue.issue_date - dt.timedelta(days=int(pre_days))
    x_max = issue.issue_date + dt.timedelta(days=int(post_days))

    obs = obs[(obs["date"] >= x_min) & (obs["date"] <= issue.issue_date)]
    fc = fc[(fc["target_date"] >= issue.issue_date + dt.timedelta(days=1)) & (fc["target_date"] <= x_max)]

    p10 = fc[member_cols].quantile(0.10, axis=1, numeric_only=True)
    p50 = fc[member_cols].quantile(0.50, axis=1, numeric_only=True)
    p90 = fc[member_cols].quantile(0.90, axis=1, numeric_only=True)
    mean = fc[member_cols].mean(axis=1, numeric_only=True)

    fig, ax = plt.subplots(figsize=(12, 5), constrained_layout=True)

    if not obs.empty:
        ax.plot(obs["date"], obs["discharge_cms"], color="#2a7f46", linewidth=1.8, label="USGS observed")

    if not fc.empty:
        for col in member_cols:
            ax.plot(fc["target_date"], fc[col], color="#6c63b8", alpha=0.20, linewidth=0.8)
        ax.fill_between(fc["target_date"], p10, p90, color="#6c63b8", alpha=0.18, label="NWS p10-p90")
        ax.plot(fc["target_date"], p50, color="#483d99", linewidth=1.8, label="NWS p50")
        ax.plot(fc["target_date"], mean, color="#2f2a67", linewidth=1.4, linestyle="--", label="NWS mean")

    ax.axvline(issue.issue_date, color="#444", linestyle="--", linewidth=1.0)
    ax.set_title("San Lorenzo River Discharge: Observed + NWS/NWM Ensemble")
    ax.set_xlabel(f"Issue date: {issue.issue_date.isoformat()} (cycle t{issue.cycle_hour:02d}z)")
    ax.set_ylabel("Discharge (m^3/s)")
    ax.set_xlim([x_min, x_max])
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left", frameon=True)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def validate_stage_outputs(stage_dir: Path, post_days: int) -> Dict[str, Any]:
    members_csv = stage_dir / "forecasts" / "nws_members.csv"
    weighted_csv = stage_dir / "forecasts" / "nws_weighted_daily.csv"
    plot_png = stage_dir / "plots" / "nws_operational_latest.png"
    pickle_path = stage_dir / "point" / "results.pkl"

    for p in (members_csv, weighted_csv, plot_png, pickle_path):
        if not p.exists():
            raise RuntimeError(f"Validation failed: missing artifact: {p}")
        if p.is_file() and p.stat().st_size <= 0:
            raise RuntimeError(f"Validation failed: empty artifact: {p}")

    df = pd.read_csv(members_csv)
    if len(df) != int(post_days):
        raise RuntimeError(f"Validation failed: expected {post_days} rows in nws_members.csv, found {len(df)}")

    member_cols = [c for c in df.columns if c.startswith("member_")]
    if len(member_cols) < 2:
        raise RuntimeError("Validation failed: expected at least 2 member columns")

    vals = df[member_cols].to_numpy(dtype=float)
    finite = np.isfinite(vals)
    if finite.sum() == 0:
        raise RuntimeError("Validation failed: no finite forecast values")

    return {
        "rows": int(len(df)),
        "member_columns": len(member_cols),
        "finite_values": int(finite.sum()),
    }


def _atomic_symlink_update(link_path: Path, target_path: Path, root_dir: Path) -> None:
    rel_target = os.path.relpath(str(target_path), start=str(root_dir))
    tmp_link = root_dir / (link_path.name + ".tmp")
    if tmp_link.exists() or tmp_link.is_symlink():
        tmp_link.unlink()
    os.symlink(rel_target, tmp_link)
    os.replace(tmp_link, link_path)


def current_run_dir(root_dir: Path) -> Optional[Path]:
    cur = root_dir / "current"
    if cur.is_symlink():
        target = os.readlink(cur)
        p = (root_dir / target).resolve()
        return p
    return None


def cleanup_staging(root_dir: Path, keep_name: Optional[str] = None) -> None:
    staging = root_dir / "staging"
    if not staging.exists():
        return
    for candidate in staging.iterdir():
        if not candidate.is_dir():
            continue
        if keep_name and candidate.name == keep_name:
            continue
        shutil.rmtree(candidate, ignore_errors=True)


def promote_successful_run(root_dir: Path, stage_dir: Path) -> Tuple[Path, Optional[Path]]:
    runs_dir = root_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    run_dir = runs_dir / stage_dir.name
    if run_dir.exists():
        shutil.rmtree(run_dir, ignore_errors=True)
    os.replace(stage_dir, run_dir)

    old_current = current_run_dir(root_dir)
    _atomic_symlink_update(root_dir / "current", run_dir, root_dir)

    # Latest-only retention: keep only active current run.
    cur_now = current_run_dir(root_dir)
    for candidate in runs_dir.iterdir():
        if not candidate.is_dir():
            continue
        if cur_now is not None and candidate.resolve() == cur_now.resolve():
            continue
        shutil.rmtree(candidate, ignore_errors=True)

    return run_dir, old_current


def publish_cache_alias(current_run: Path, cache_alias_root: Path, issue: IssueCycle) -> Path:
    cache_alias_root.mkdir(parents=True, exist_ok=True)
    for d in cache_alias_root.glob("cutoff_date=*"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)

    alias_dir = cache_alias_root / f"cutoff_date={issue.issue_date.isoformat()}"
    alias_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(current_run / "forecasts" / "nws_members.csv", alias_dir / "nws_members.csv")
    return alias_dir


def should_skip_update(status_file: Path, issue: IssueCycle, skip_if_current: bool) -> bool:
    if not skip_if_current:
        return False
    if not status_file.exists():
        return False
    try:
        info = json.loads(status_file.read_text(encoding="utf-8"))
    except Exception:
        return False

    is_same_cycle = (
        str(info.get("issue_date")) == issue.issue_date.isoformat()
        and int(info.get("cycle_hour", -1)) == issue.cycle_hour
        and str(info.get("status")) == "success"
    )
    if not is_same_cycle:
        return False

    # Status file alone is not enough; ensure promoted "current" artifacts exist.
    root_dir = status_file.parents[1]
    current_dir = current_run_dir(root_dir)
    if current_dir is None:
        return False
    expected = current_dir / "forecasts" / "nws_members.csv"
    return expected.exists() and expected.stat().st_size > 0


@contextlib.contextmanager
def exclusive_lock(lock_file: Path):
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with lock_file.open("w", encoding="utf-8") as fh:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"Another updater instance is running (lock: {lock_file}).") from exc
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def run_once(cfg: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    root_dir = (repo_root / cfg["output"]["root_dir"]).resolve()
    cache_alias_root = (repo_root / cfg["output"]["cache_alias_root"]).resolve()
    status_file = root_dir / str(cfg["output"]["status_file_rel"])
    root_dir.mkdir(parents=True, exist_ok=True)

    timings: Dict[str, float] = {}
    t_all = time.perf_counter()

    issue = find_latest_cycle(cfg)
    print(f"[cycle] latest={issue.issue_date.isoformat()} t{issue.cycle_hour:02d}z", flush=True)

    skip_if_current = bool(cfg.get("runtime", {}).get("skip_if_current", True))
    if should_skip_update(status_file, issue, skip_if_current=skip_if_current):
        return {
            "status": "skipped_current",
            "issue_date": issue.issue_date.isoformat(),
            "cycle_hour": issue.cycle_hour,
            "message": "Latest cycle already current; no-op.",
            "total_seconds": round(time.perf_counter() - t_all, 3),
        }

    t0 = time.perf_counter()
    tasks = build_tasks(cfg, issue)
    timings["task_build_seconds"] = time.perf_counter() - t0
    print(f"[tasks] count={len(tasks)}", flush=True)

    t1 = time.perf_counter()
    feature_index, smoke_value = resolve_feature_index(cfg, issue)
    timings["feature_resolve_seconds"] = time.perf_counter() - t1
    print(f"[feature] id={int(cfg['site']['feature_id'])} index={feature_index} smoke={smoke_value:.6f}", flush=True)

    run_id = f"{issue.issue_date.strftime('%Y%m%d')}t{issue.cycle_hour:02d}z_{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    stage_dir = root_dir / "staging" / run_id
    cleanup_staging(root_dir=root_dir, keep_name=run_id)
    if stage_dir.exists():
        shutil.rmtree(stage_dir, ignore_errors=True)
    (stage_dir / "point").mkdir(parents=True, exist_ok=True)
    (stage_dir / "forecasts").mkdir(parents=True, exist_ok=True)
    (stage_dir / "plots").mkdir(parents=True, exist_ok=True)
    (stage_dir / "meta").mkdir(parents=True, exist_ok=True)

    try:
        t2 = time.perf_counter()
        extract_info = extract_cycle_values(cfg, tasks, feature_index)
        timings["download_extract_seconds"] = float(extract_info["download_extract_seconds"])

        pkl_path = stage_dir / "point" / "results.pkl"
        write_pickle(pkl_path, extract_info["values"])

        extract_meta = {
            "issue_date": issue.issue_date.isoformat(),
            "cycle_hour": issue.cycle_hour,
            "task_count": len(tasks),
            "feature_id": int(cfg["site"]["feature_id"]),
            "feature_index": feature_index,
            "download_extract_seconds": round(timings["download_extract_seconds"], 3),
            "download_mb": round(float(extract_info["total_bytes"]) / (1024 * 1024), 3),
            "avg_attempts_per_file": round(float(extract_info["avg_attempts_per_file"]), 3),
        }
        (stage_dir / "meta" / "extract_meta.json").write_text(json.dumps(extract_meta, indent=2), encoding="utf-8")

        members_csv = stage_dir / "forecasts" / "nws_members.csv"
        weighted_csv = stage_dir / "forecasts" / "nws_weighted_daily.csv"

        t3 = time.perf_counter()
        post_elapsed, post_tail = run_postprocess(cfg, repo_root, issue, pkl_path, weighted_csv)
        timings["postprocess_seconds"] = post_elapsed
        shutil.copy2(weighted_csv, members_csv)
        create_legacy_alias(members_csv, stage_dir / "forecasts" / "nws_forecast.csv")

        t4 = time.perf_counter()
        obs = fetch_usgs_recent(
            site_id=str(cfg["site"]["usgs_site"]),
            pre_days=int(cfg["observed"]["pre_days"]),
            parameter_cd=str(cfg["observed"]["nwis_parameter_cd"]),
            stat_cd=str(cfg["observed"]["nwis_stat_cd"]),
        )
        build_plot(
            obs_df=obs,
            nws_members_csv=members_csv,
            issue=issue,
            pre_days=int(cfg["observed"]["pre_days"]),
            post_days=int(cfg["processing"]["post_days"]),
            out_png=stage_dir / str(cfg["output"]["plot_file_rel"]),
        )
        timings["plot_seconds"] = time.perf_counter() - t4

        t5 = time.perf_counter()
        validation = validate_stage_outputs(stage_dir, int(cfg["processing"]["post_days"]))
        timings["validation_seconds"] = time.perf_counter() - t5

        run_dir, old_current = promote_successful_run(root_dir, stage_dir)
        alias_dir = publish_cache_alias(run_dir, cache_alias_root, issue)
    except Exception:
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise

    total_elapsed = time.perf_counter() - t_all
    timings["total_seconds"] = total_elapsed

    summary = {
        "status": "success",
        "issue_date": issue.issue_date.isoformat(),
        "cycle_hour": issue.cycle_hour,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "cache_alias_dir": str(alias_dir),
        "feature_id": int(cfg["site"]["feature_id"]),
        "feature_index": int(feature_index),
        "task_count": int(len(tasks)),
        "validation": validation,
        "timings": {k: round(float(v), 3) for k, v in timings.items()},
        "download_mb": round(float(extract_info["total_bytes"]) / (1024 * 1024), 3),
        "avg_attempts_per_file": round(float(extract_info["avg_attempts_per_file"]), 3),
        "post_stdout_tail": post_tail,
        "old_current": str(old_current) if old_current is not None else None,
        "updated_at_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Operational NWS/NWM latest-cycle updater (point-only, latest-only)")
    p.add_argument(
        "--config",
        type=Path,
        default=Path("config/nws_operational_latest.yaml"),
        help="YAML configuration path",
    )
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root")
    p.add_argument("--print-summary-only", action="store_true", help="Only print latest status file and exit")
    return p


def print_latest_summary(cfg: Dict[str, Any], repo_root: Path) -> int:
    status_file = (repo_root / cfg["output"]["root_dir"] / cfg["output"]["status_file_rel"]).resolve()
    if not status_file.exists():
        print(json.dumps({"status": "missing", "status_file": str(status_file)}, indent=2))
        return 1
    print(status_file.read_text(encoding="utf-8"))
    return 0


def main() -> int:
    args = build_parser().parse_args()
    repo_root = args.repo_root.resolve()
    cfg = load_config((repo_root / args.config).resolve())

    if args.print_summary_only:
        return print_latest_summary(cfg, repo_root)

    root_dir = (repo_root / cfg["output"]["root_dir"]).resolve()
    lock_file = root_dir / ".lock"

    root_dir = (repo_root / cfg["output"]["root_dir"]).resolve()
    lock_file = root_dir / ".lock"

    try:
        with exclusive_lock(lock_file):
            summary = run_once(cfg, repo_root)
    except Exception as exc:
        err = {
            "status": "error",
            "error": str(exc),
            "updated_at_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        try:
            status_dir = root_dir / "status"
            status_dir.mkdir(parents=True, exist_ok=True)
            (status_dir / "latest_error.json").write_text(json.dumps(err, indent=2), encoding="utf-8")
        except Exception:
            pass
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 2

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
