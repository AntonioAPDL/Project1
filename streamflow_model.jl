using CSV, DataFrames, AutoGP, Dates, PyPlot, Logging, JLD2

# Load dataset
df = CSV.read("/data/muscat_data/jaguir26/project1_ucsc_phd/usgs_daily_avg.csv", DataFrame)

# No need to convert 'Date', already of Date type

# Filter data up to 2022-12-25
df_filtered = filter(row -> row.Date <= Date(2022, 12, 25), df)

# Create AutoGP model
n_train = size(df_filtered, 1)
println("Model created with $n_train observations")

# Adjusting number of particles based on the number of threads available
n_particles = min(Threads.nthreads(), 6)  # Use available threads if less than 6
println("Using $n_particles particles out of available threads: ", Threads.nthreads())

model = AutoGP.GPModel(df_filtered.Date, df_filtered.Daily_Avg_Log_Streamflow; n_particles=n_particles)

# Debug: Print model summary
println("Model created. Starting to fit the model...")

# Fit the model using SMC with debugging info
AutoGP.fit_smc!(model; schedule=AutoGP.Schedule.linear_schedule(n_train, 0.10), n_mcmc=75, n_hmc=10, verbose=true)

println("Model fitting completed")

# Save the model object to disk using JLD2
@save "/data/muscat_data/jaguir26/project1_ucsc_phd/streamflow_model.jld2" model

# Make predictions for 365 days after 2022-12-25
ds_future = range(Date(2022, 12, 26), step=Day(1), length=365)
forecasts = AutoGP.predict(model, vcat(df_filtered.Date, ds_future); quantiles=[0.025, 0.975])

# Save the forecast data to CSV
CSV.write("/data/muscat_data/jaguir26/project1_ucsc_phd/streamflow_forecasts.csv", forecasts)

# Debugging: Check the forecasts output
println("Forecasting completed. First 5 rows of forecast data:")
println(first(forecasts, 5))

# Plot results
fig, ax = plt.subplots(figsize=(10,5))
ax.scatter(df_filtered.Date, df_filtered.Daily_Avg_Log_Streamflow, marker=".", color="k", label="Observed Data")
for i = 1:AutoGP.num_particles(model)
    subdf = forecasts[forecasts.particle .== i, :]
    ax.plot(subdf.Date, subdf.y_mean, color="k", linewidth=0.5)
    ax.fill_between(subdf.Date, subdf.y_0_025, subdf.y_0_975, color="tab:blue", alpha=0.05)
end
ax.set_xlabel("Date")
ax.set_ylabel("Daily Avg Log Streamflow")
plt.legend()
plt.title("Streamflow Forecasts")

# Save the plot as an image file
plt.savefig("/data/muscat_data/jaguir26/project1_ucsc_phd/streamflow_forecast_plot.png")
println("Plot saved as 'streamflow_forecast_plot.png'.")

# Display plot
plt.show()

# Save forecasts and additional data in JLD2 format for future use
@save "/data/muscat_data/jaguir26/project1_ucsc_phd/streamflow_model_data.jld2" model forecasts
println("Model and forecast data saved to 'streamflow_model_data.jld2'.")

