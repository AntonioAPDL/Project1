.libPaths(c("~/R/libs", .libPaths()))
print(.libPaths())
# ----------------------------------------
# Install required packages if missing
# ----------------------------------------
required_packages <- c("prism", "dplyr", "lubridate", "raster")
installed <- rownames(installed.packages())

for (pkg in required_packages) {
  if (!pkg %in% installed) install.packages(pkg, repos = "https://cloud.r-project.org/")
}

# ----------------------------------------
# Load packages
# ----------------------------------------
library(prism)
library(dplyr)
library(lubridate)
library(raster)

# ----------------------------------------
# Set up directories
# ----------------------------------------
setwd('/data/muscat_data/jaguir26/project1_ucsc_phd')
prism_set_dl_dir('/data/muscat_data/jaguir26/project1_ucsc_phd/prism_data')

# ----------------------------------------
# Download PRISM Daily Precipitation Data
# ----------------------------------------
start_date <- as.Date("1987-01-01")
end_date <- as.Date("2023-12-31")

get_prism_dailys(
  type = "ppt",
  minDate = format(start_date),
  maxDate = format(end_date),
  keepZip = FALSE
)
# ----------------------------------------
# List and read PRISM raster files
# ----------------------------------------
folders <- prism_archive_ls()
bil_files <- file.path(prism_get_dl_dir(), folders, paste0(folders, ".bil"))

# Santa Cruz coordinates
santa_cruz_coords <- c(-122.072464, 37.0443931)

# Function to extract value from raster with robust date extraction
read_prism_file <- function(file) {
  r <- raster(file)
  value <- extract(r, matrix(santa_cruz_coords, ncol = 2))

  # Extract YYYYMMDD using regex
  file_name <- basename(file)
  date_str <- regmatches(file_name, regexpr("[0-9]{8}", file_name))
  date <- as.Date(date_str, format = "%Y%m%d")

  data.frame(Date = date, PRCP_mm = value)
}

# Apply and bind all results
prism_data_list <- lapply(bil_files, read_prism_file)
prism_data <- bind_rows(prism_data_list) %>%
  arrange(Date) %>%
  filter(!is.na(Date) & !is.na(PRCP_mm))  # Ensure both columns are valid

# ----------------------------------------
# Save to CSV
# ----------------------------------------
output_csv <- "prism_precipitation_santa_cruz_1987_2023.csv"
write.csv(prism_data, output_csv, row.names = FALSE)

cat("✅ Fixed and saved PRISM data with valid dates to:", output_csv, "\n")
