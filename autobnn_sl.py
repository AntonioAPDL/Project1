#!/usr/bin/env python3

# San Lorenzo River @ Big Trees - AutoBNN: Weekly Streamflow Forecast (Expressive)

import os, pickle, jax, jax.numpy as jnp, numpy as np, matplotlib.pyplot as plt, pandas as pd
from datetime import datetime
import dataretrieval.nwis as nwis
from autobnn import estimators

CFSToCMS_CONVERSION_FACTOR = 0.0283168466
SITE_CODE = '11160500'
START_USGS = '1979-01-01'
END_USGS = datetime.today().strftime('%Y-%m-%d')
TRAIN_END = '2022-12-31'
FORECAST_WEEKS = 52  # 1 year (52 weeks)
RANDOM_SEED = 0

print("Downloading daily discharge data from USGS...")
df = nwis.get_record(
    sites=SITE_CODE,
    service='dv',
    parameterCd='00060',
    statCd='00003',
    start=START_USGS,
    end=END_USGS
)
df.index = pd.to_datetime(df.index)
df = df.sort_index()
df['discharge_cms'] = df['00060_Mean'].astype(float) * CFSToCMS_CONVERSION_FACTOR

df_clean = df[
    (df['discharge_cms'].notna()) &
    (df['discharge_cms'] >= 0) &
    (df['00060_Mean'] != -999999.0)
].copy()
df_clean['log_discharge_cms'] = np.log(df_clean['discharge_cms'] + 1)
dropped = len(df) - len(df_clean)
if dropped > 0:
    print(f"Filtered out {dropped} rows with missing/invalid data.")

# --- AGGREGATE TO WEEKLY MEANS ---
weekly_df = df_clean['log_discharge_cms'].resample('W').mean().dropna()
# .resample('W') -> weekly frequency; can use 'W-SUN' or 'W-MON' to specify ending day if needed

# --- TRAIN/TEST SPLIT: up to Dec 2022, then next 52 weeks ---
train_df = weekly_df[:TRAIN_END]
test_df = weekly_df[TRAIN_END:].iloc[:FORECAST_WEEKS]

y_train = train_df.values
y_test = test_df.values
dates_train = train_df.index
dates_test = test_df.index

# --- NORMALIZE TIME INDICES ---
x_all = np.arange(len(weekly_df))
x_train = x_all[:len(train_df)]
x_test = x_all[len(train_df):len(train_df) + FORECAST_WEEKS]
x_scale = x_train.max()
x_train = x_train / x_scale
x_test = x_test / x_scale

# --- PERIODS FOR SEASONALITY (in weeks, normalized) ---
# One year = 52 weeks, half-year = 26, quarter = 13, etc.
one_year = jnp.array(52. / x_scale, dtype=jnp.float32)
periods = (
    one_year,              # 1 year (seasonal)
    one_year/2,            # 6 months
    one_year/4,            # 3 months (quarterly)
    one_year*2,            # 2 years
    one_year*5.5,          # ENSO-like cycle (~5-6 years)
    one_year*6.75,         # ~81 weeks (approx. 1.5 years)
    one_year*10,           # Decadal
    jnp.array(1.0 / x_scale, dtype=jnp.float32),     # 1 week (high-frequency, if desired)
    jnp.array(2.0 / x_scale, dtype=jnp.float32),     # 2 weeks (biweekly)
    jnp.array(4.0 / x_scale, dtype=jnp.float32)      # 1 month (4 weeks)
)

print("Setting up and fitting AutoBNN model... (very expressive config, weekly data)")
seed = jax.random.PRNGKey(RANDOM_SEED)
fit_seed, pred_seed, _ = jax.random.split(seed, 3)

est = estimators.AutoBnnMapEstimator(
    model_or_name='sum_of_stumps_and_products',  # very expressive
    likelihood_model='bounded_normal_likelihood_logistic_noise',
    seed=fit_seed,
    periods=periods,
    num_particles=32,     # you can increase for even more expressiveness
    width=100,            # or set higher for more flexibility
    num_iters=2000,       # may want more for convergence on longer weekly series
    learning_rate=0.001
)
est = est.fit(x_train[..., None], y_train[..., None])

# --- FORECAST ---
x_pred = np.concatenate([x_train, x_test])
preds = est.predict(x_pred[..., None])
lo, mid, p90, hi = est.predict_quantiles(x_pred[..., None], q=[2.5, 50., 90., 97.5])
dates_all = dates_train.append(dates_test)


# Output directory (optional: change as needed)
OUTPUT_DIR = "autobnn_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PLOT_PATH = os.path.join(OUTPUT_DIR, "san_lorenzo_autobnn_forecast_weekly.png")
MODEL_PATH = os.path.join(OUTPUT_DIR, "san_lorenzo_autobnn_estimator_weekly.pkl")

print(f"Saving forecast plot to {PLOT_PATH} ...")
plt.figure(figsize=(16, 5), dpi=200)  # dpi set higher for sharpness

plt.plot(dates_train, y_train, label='Train Data', color='#1f77b4', linewidth=2)
plt.plot(dates_test, y_test, label='Test Data', color='#2ca02c', linewidth=2)
plt.plot(dates_all, mid, color='#d62728', label='Prediction Median', linewidth=2)
plt.fill_between(dates_all, lo, hi, color='#d62728', alpha=0.18, label='95% CI', linewidth=0)
plt.axvline(dates_train[-1], color='black', linestyle='--', linewidth=1.4, label='Train/Test Split')

plt.title('San Lorenzo River @ Big Trees\nWeekly log Streamflow Forecast (Complex AutoBNN)', fontsize=18, weight='bold')
plt.xlabel('Year', fontsize=14)
plt.ylabel('log(discharge cms + 1)', fontsize=14)
plt.legend(fontsize=12, frameon=False, loc='upper left')
plt.grid(axis='y', linestyle=':', alpha=0.35)
plt.tight_layout()
plt.savefig(PLOT_PATH, dpi=400, bbox_inches='tight', pad_inches=0.12)
plt.close()
print(f"Plot saved to: {PLOT_PATH}")

print(f"Saving fitted estimator object to {MODEL_PATH} ...")
with open(MODEL_PATH, "wb") as f:
    pickle.dump(est, f)
print(f"Model saved to: {MODEL_PATH}")

print("All done. Complex weekly forecast and model saved to output directory.")
