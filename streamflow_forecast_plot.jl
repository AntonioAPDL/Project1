using CSV, DataFrames, Dates, PyPlot

# Load forecast data
df_forecast = CSV.read("/data/muscat_data/jaguir26/project1_ucsc_phd/streamflow_forecasts.csv", DataFrame)

# Load observed data
df_observed = CSV.read("/data/muscat_data/jaguir26/project1_ucsc_phd/usgs_daily_avg.csv", DataFrame)

# Parse the 'Date' columns as Date type (ensure dates are strings first)
df_forecast.ds = Date.(string.(df_forecast.ds), "yyyy-mm-dd")
df_observed.Date = Date.(string.(df_observed.Date), "yyyy-mm-dd")

# Split the observed data into training (before 2022-12-25) and test (after 2022-12-25)
df_training = filter(row -> row.Date <= Date(2022, 12, 25), df_observed)
df_test = filter(row -> row.Date > Date(2022, 12, 25), df_observed)

# Plotting the observed training data in black
fig, ax = plt.subplots(figsize=(10, 5))
ax.scatter(df_training.Date, df_training.Daily_Avg_Log_Streamflow, color="k", label="Observed (Training)")

# Plotting the observed test data in red
ax.scatter(df_test.Date, df_test.Daily_Avg_Log_Streamflow, color="r", label="Observed (Test)", marker="x")

# Plotting the forecasted values with uncertainty bands in blue
for i = 1:maximum(df_forecast.particle)
    subdf = df_forecast[df_forecast.particle .== i, :]
    ax.plot(subdf.ds, subdf.y_mean, color="b", linewidth=0.5)
    ax.fill_between(subdf.ds, subdf.y_0.025, subdf.y_0.975, color="tab:blue", alpha=0.2, label=nothing)
end

# Customize the plot
ax.set_xlabel("Date")
ax.set_ylabel("Daily Avg Log Streamflow")
ax.legend()
plt.title("Streamflow Forecasts vs Observed Data")

# Save the plot as a high-quality PNG image
plt.savefig("/data/muscat_data/jaguir26/project1_ucsc_phd/streamflow_forecast_vs_observed.png", dpi=300)
println("Plot saved as 'streamflow_forecast_vs_observed.png'.")

# Display the plot
plt.show()

